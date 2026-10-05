"""Tests for the thin Claude Agent SDK adapter. No network; SDK import optional."""

from __future__ import annotations

import asyncio
import dataclasses
import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ADAPTER = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ADAPTER / f"{name}.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


agent = _load("l9_agent")
validator = _load("validate_agent_sdk_env")
REPO = Path(agent.REPO)

# The whole option surface. Anything added here must be SDK runtime mechanics,
# never policy the project settings already own.
RUNTIME_KEYS = {
    "cwd",
    "setting_sources",
    "system_prompt",
    "permission_mode",
    "output_format",
    "max_turns",
    "max_budget_usd",
    "enable_file_checkpointing",
}


def test_project_settings_are_the_governance_source():
    kwargs = agent.option_kwargs()
    assert kwargs["setting_sources"] == ["project"]
    assert kwargs["cwd"] == REPO
    assert kwargs["system_prompt"] == {"type": "preset", "preset": "claude_code"}


def test_option_surface_is_runtime_only():
    assert set(agent.option_kwargs()) == RUNTIME_KEYS


@pytest.mark.parametrize("key", validator.SHADOW_POLICY_KEYS)
def test_no_shadow_policy_key_is_passed(key):
    assert key not in agent.option_kwargs()


@pytest.mark.parametrize(
    "needle",
    [
        "l9_hook_exec",
        "claude-code/hooks",
        "--class",
        "governor",
        "bootstrap_capability_preflight",
        "telemetry/",
        "AgentDefinition",
        "HookMatcher",
    ],
)
def test_removed_machinery_does_not_reappear(needle):
    for path in (ADAPTER / "l9_agent.py", ADAPTER / "validate_agent_sdk_env.py"):
        assert needle not in path.read_text(encoding="utf-8"), f"{needle!r} in {path.name}"
    assert not (ADAPTER / "config.yaml").exists()


def test_budget_and_turn_bounds_are_wired():
    kwargs = agent.option_kwargs(mode="plan", budget=5.0, turns=7)
    assert (kwargs["max_budget_usd"], kwargs["max_turns"]) == (5.0, 7)
    assert kwargs["permission_mode"] == "plan"


@pytest.mark.parametrize(
    "bad", [{"mode": "bypassPermissions"}, {"budget": 0.0}, {"turns": 0}, {"budget": -1.0}]
)
def test_invalid_bounds_are_rejected(bad):
    with pytest.raises(ValueError):
        agent.option_kwargs(**bad)


def test_structured_report_contract():
    assert set(agent.REPORT_SCHEMA["required"]) == {"summary", "findings", "files_changed"}
    fmt = agent.option_kwargs()["output_format"]
    assert fmt == {"type": "json_schema", "schema": agent.REPORT_SCHEMA}
    result = SimpleNamespace(
        subtype="success",
        is_error=False,
        num_turns=3,
        total_cost_usd=0.01,
        session_id="s1",
        permission_denials=[],
        structured_output={"summary": "ok", "findings": [], "files_changed": []},
    )
    doc = agent.report_document(result, [{"name": "m", "status": "connected"}])
    assert doc["structured_output"]["summary"] == "ok"
    assert doc["mcp_servers"] == [{"name": "m", "status": "connected"}]


def test_mcp_summary_drops_server_config():
    status = {
        "mcpServers": [
            {"name": "a", "status": "connected", "scope": "project", "config": {"env": {"K": "v"}}},
            {"name": "b", "status": "failed", "error": "boom"},
        ]
    }
    assert agent.summarize_mcp(status) == [
        {"name": "a", "status": "connected", "scope": "project"},
        {"name": "b", "status": "failed", "error": "boom"},
    ]


class _FakeClient:
    """Yields each status once, then repeats the last one."""

    def __init__(self, statuses):
        self._statuses = list(statuses)

    async def get_mcp_status(self):
        row = self._statuses.pop(0) if len(self._statuses) > 1 else self._statuses[0]
        return {"mcpServers": [row]}


def test_mcp_status_waits_for_pending_to_settle(monkeypatch):
    async def no_sleep(_s):
        return None

    monkeypatch.setattr(agent.asyncio, "sleep", no_sleep)
    client = _FakeClient([{"name": "m", "status": "pending"}, {"name": "m", "status": "connected"}])
    rows = asyncio.run(agent.settled_mcp_status(client, timeout=60))
    assert rows == [{"name": "m", "status": "connected"}]


def test_mcp_status_reports_pending_truthfully_on_timeout():
    client = _FakeClient([{"name": "m", "status": "pending"}])
    rows = asyncio.run(agent.settled_mcp_status(client, timeout=0))
    assert rows == [{"name": "m", "status": "pending"}]


def test_default_report_path_is_gitignored():
    assert validator.check_report_ignored(REPO, agent.DEFAULT_REPORT) == ([], [])


def test_sdk_dependency_is_bound_in_the_lock():
    assert validator.check_dependency(REPO) == []


def test_repository_obligations_hold():
    errors, unknowns = validator.validate(agent)
    assert errors == []
    assert all(u.startswith("SDK_IMPORT") for u in unknowns)


@pytest.mark.parametrize(
    ("override", "code"),
    [
        ({"setting_sources": ["user"]}, "SETTING_SOURCES"),
        ({"allowed_tools": ["Read"]}, "SHADOW_POLICY"),
        ({"disallowed_tools": ["WebFetch"]}, "SHADOW_POLICY"),
        ({"hooks": {}}, "SHADOW_POLICY"),
        (
            {"system_prompt": {"type": "preset", "preset": "claude_code", "append": "x"}},
            "SHADOW_POLICY",
        ),
    ],
)
def test_validator_fails_on_broken_option_obligation(override, code):
    errors = validator.check_options({**agent.option_kwargs(), **override})
    assert any(e.startswith(code) for e in errors)


def test_validator_fails_without_sdk_pin(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
    (tmp_path / "uv.lock").write_text("version = 1\n")
    assert validator.check_dependency(tmp_path)[0].startswith("DEPENDENCY_BOUND")


def test_validator_fails_when_lock_lacks_pinned_version(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project.optional-dependencies]\nagent-sdk = ["claude-agent-sdk==9.9.9"]\n'
    )
    (tmp_path / "uv.lock").write_text(
        'version = 1\n[[package]]\nname = "claude-agent-sdk"\nversion = "0.0.1"\n'
    )
    assert "uv.lock does not carry" in validator.check_dependency(tmp_path)[0]


def test_validator_fails_on_missing_governance_inputs(tmp_path):
    assert agent.missing_governance(tmp_path) == list(agent.PROJECT_GOVERNANCE)


def test_validator_fails_when_report_path_is_tracked_tree(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    errors, unknowns = validator.check_report_ignored(tmp_path, agent.DEFAULT_REPORT)
    assert unknowns == [] and errors[0].startswith("REPORT_IGNORED")


# The agent-sdk extra is optional (each wheel bundles a ~100 MB CLI) and is not
# synced by the default `--extra dev` CI environment. This is the one seam that
# needs the real SDK; it runs wherever `uv sync --locked --extra agent-sdk` ran.
_SDK = importlib.util.find_spec("claude_agent_sdk") is not None


@pytest.mark.skipif(not _SDK, reason="agent-sdk extra not synced in this environment")
def test_real_sdk_accepts_options_and_exposes_report_fields():
    import claude_agent_sdk as sdk

    opts = agent.build_options(agent.option_kwargs())
    assert isinstance(opts, sdk.ClaudeAgentOptions)
    assert opts.setting_sources == ["project"]
    assert opts.allowed_tools == [] and opts.disallowed_tools == []
    assert not opts.hooks and not opts.agents and not opts.mcp_servers
    assert set(agent.RESULT_FIELDS) <= {f.name for f in dataclasses.fields(sdk.ResultMessage)}

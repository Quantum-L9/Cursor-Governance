"""Tests for ops/scripts/reconcile_claude_settings.py"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[3] / "ops" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from reconcile_claude_settings import (  # noqa: E402
    merge_user_settings,
    merge_workspace_settings,
    run,
)


def test_merge_preserves_plugins() -> None:
    template = {
        "hooks": {"SessionStart": []},
        "permissions": {"allow": ["Read"], "deny": []},
        "env": {"L9_AUTONOMY_ENABLED": "true"},
        "skillOverrides": {"l9-forge": "user-invocable-only"},
    }
    existing = {
        "enabledPlugins": {"hookify@claude-plugins-official": True},
        "theme": "light",
        "customUserKey": 1,
    }
    merged = merge_user_settings(template, existing)
    assert merged["enabledPlugins"] == existing["enabledPlugins"]
    assert merged["theme"] == "light"
    assert merged["customUserKey"] == 1
    assert merged["env"]["L9_AUTONOMY_ENABLED"] == "true"
    assert "hooks" in merged


def test_reconcile_workspace_and_check(tmp_path: Path) -> None:
    root = tmp_path / "gov"
    hooks = root / "environment" / "agents" / "adapters" / "claude-code" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "session_start_claude_governance.sh").write_text("#!/bin/bash\n", encoding="utf-8")
    (hooks / "merge_gate_wrap.py").write_text("# wrap\n", encoding="utf-8")
    tmpl = {
        "$schema": "https://example.com/schema.json",
        "hooks": {"SessionStart": [{"hooks": []}]},
        "permissions": {"allow": ["Read"], "deny": []},
        "env": {"L9_GOVERNANCE_SURFACE": "claude-code", "L9_AUTONOMY_ENABLED": "true"},
        "skillOverrides": {},
    }
    tmpl_path = (
        root / "environment" / "agents" / "adapters" / "claude-code" / "settings.template.json"
    )
    tmpl_path.write_text(json.dumps(tmpl, indent=2) + "\n", encoding="utf-8")

    ws = tmp_path / "consumer"
    ws.mkdir()
    result = run(root, workspace=ws, user=False, gov=True, check=False)
    assert (root / ".claude" / "settings.json").is_file()
    assert (ws / ".claude" / "settings.json").is_file()
    assert (ws / ".claude" / "hooks" / "session_start_claude_governance.sh").is_file()
    check = run(root, workspace=ws, user=False, gov=True, check=True)
    assert check["ok"] is True
    assert result["wrote"]


# -- issue #281: a git-tracked workspace settings file owns its hooks --------


def test_merge_composes_hooks_for_tracked_file() -> None:
    template = {
        "hooks": {
            "SessionStart": [{"hooks": [{"type": "command", "command": "gov-session-start"}]}],
            "PreToolUse": [
                {"matcher": "Edit|Write", "hooks": [{"type": "command", "command": "gov-edit"}]}
            ],
        },
        "permissions": {"allow": ["Read"], "deny": []},
        "env": {},
        "skillOverrides": {},
    }
    existing = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [
                        {"type": "command", "command": "python3 tools/contract_scanner.py --quick"}
                    ],
                }
            ],
            "Stop": [{"hooks": [{"type": "command", "command": "consumer-stop"}]}],
        },
        "enabledPlugins": {"plugin@official": True},
    }
    merged = merge_workspace_settings(template, existing, compose_hooks=True)
    pretool = merged["hooks"]["PreToolUse"]
    # Consumer guard first and kept, governance group appended.
    assert pretool[0]["hooks"][0]["command"] == "python3 tools/contract_scanner.py --quick"
    assert pretool[1]["hooks"][0]["command"] == "gov-edit"
    # Consumer-only event survives; governance-only event lands.
    assert merged["hooks"]["Stop"][0]["hooks"][0]["command"] == "consumer-stop"
    assert merged["hooks"]["SessionStart"][0]["hooks"][0]["command"] == "gov-session-start"
    assert merged["enabledPlugins"] == {"plugin@official": True}


def test_merge_wholesale_replaces_hooks_when_untracked() -> None:
    template = {
        "hooks": {
            "SessionStart": [{"hooks": [{"type": "command", "command": "gov-session-start"}]}]
        }
    }
    existing = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "consumer-stop"}]}]}}
    merged = merge_workspace_settings(template, existing)  # default: untracked file
    assert "Stop" not in merged["hooks"]
    assert merged["hooks"]["SessionStart"][0]["hooks"][0]["command"] == "gov-session-start"


def test_compose_churn_free_when_hooks_already_match_template() -> None:
    template = {
        "hooks": {
            "SessionStart": [{"hooks": [{"type": "command", "command": "gov-session-start"}]}],
            "PreToolUse": [
                {"matcher": "Edit", "hooks": [{"type": "command", "command": "gov-edit"}]}
            ],
        }
    }
    existing = {"hooks": template["hooks"], "theme": "dark"}
    merged = merge_workspace_settings(template, existing, compose_hooks=True)
    assert merged["hooks"] == template["hooks"]
    assert merged["theme"] == "dark"


def test_compose_replaces_malformed_event_value_with_template() -> None:
    template = {
        "hooks": {
            "SessionStart": [{"hooks": [{"type": "command", "command": "gov-session-start"}]}]
        }
    }
    existing = {
        "hooks": {
            "SessionStart": {"not": "a list"},
            "Stop": [{"hooks": [{"type": "command", "command": "consumer-stop"}]}],
        }
    }
    merged = merge_workspace_settings(template, existing, compose_hooks=True)
    # A malformed event value is not a hook list: governance groups replace it.
    assert merged["hooks"]["SessionStart"][0]["hooks"][0]["command"] == "gov-session-start"
    # Consumer-owned events stay verbatim.
    assert merged["hooks"]["Stop"][0]["hooks"][0]["command"] == "consumer-stop"


def test_compose_drops_stale_l9_managed_hooks_before_appending_template() -> None:
    stale = (
        "bash -c 'x=\"$HOME/.cursor-governance/environment/agents/adapters/"
        'claude-code/hooks/l9_hook_exec.sh"; [ -f "$x" ] || exit 0; '
        'exec bash "$x" --class observer retired_gate.sh\''
    )
    fresh = (
        "bash -c 'x=\"$HOME/.cursor-governance/environment/agents/adapters/"
        'claude-code/hooks/l9_hook_exec.sh"; [ -f "$x" ] || exit 0; '
        'exec bash "$x" --class observer session_start_claude_governance.sh\''
    )
    template = {
        "hooks": {
            "SessionStart": [{"hooks": [{"type": "command", "command": fresh}]}],
        }
    }
    existing = {
        "hooks": {
            "SessionStart": [
                {"hooks": [{"type": "command", "command": stale}]},
                {"hooks": [{"type": "command", "command": "python3 tools/contract_scanner.py"}]},
            ],
        }
    }
    merged = merge_workspace_settings(template, existing, compose_hooks=True)
    commands = [g["hooks"][0]["command"] for g in merged["hooks"]["SessionStart"]]
    assert stale not in commands
    assert "python3 tools/contract_scanner.py" in commands
    assert fresh in commands
    assert commands.count(fresh) == 1


def test_reconcile_workspace_composes_tracked_settings(tmp_path: Path) -> None:
    root = tmp_path / "gov"
    hooks = root / "environment" / "agents" / "adapters" / "claude-code" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "session_start_claude_governance.sh").write_text("#!/bin/bash\n", encoding="utf-8")
    (hooks / "merge_gate_wrap.py").write_text("# wrap\n", encoding="utf-8")
    tmpl = {
        "$schema": "https://example.com/schema.json",
        "hooks": {
            "SessionStart": [{"hooks": [{"type": "command", "command": "gov-session-start"}]}]
        },
        "permissions": {"allow": ["Read"], "deny": []},
        "env": {"L9_GOVERNANCE_SURFACE": "claude-code", "L9_AUTONOMY_ENABLED": "true"},
        "skillOverrides": {},
    }
    tmpl_path = (
        root / "environment" / "agents" / "adapters" / "claude-code" / "settings.template.json"
    )
    tmpl_path.write_text(json.dumps(tmpl, indent=2) + "\n", encoding="utf-8")

    ws = tmp_path / "consumer"
    ws.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=ws, check=True)
    settings = ws / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text(
        json.dumps(
            {
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "Bash",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "python3 tools/contract_scanner.py --quick",
                                }
                            ],
                        }
                    ]
                }
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", ".claude/settings.json"], cwd=ws, check=True)

    result = run(root, workspace=ws, user=False, gov=True, check=False)
    assert result["wrote"]

    reconciled = json.loads(settings.read_text(encoding="utf-8"))
    pretool_commands = [g["hooks"][0]["command"] for g in reconciled["hooks"]["PreToolUse"]]
    assert "python3 tools/contract_scanner.py --quick" in pretool_commands, (
        "a tracked consumer guard must survive reconciliation"
    )
    assert reconciled["hooks"]["SessionStart"], "governance hooks must still land"

    # Idempotent: the composed file must not churn on the next reconcile.
    second = run(root, workspace=ws, user=False, gov=True, check=False)
    assert second["wrote"] == []
    check = run(root, workspace=ws, user=False, gov=True, check=True)
    assert check["ok"] is True


# --- Hook budgets are derived from registrations, never authored twice -------
# A hook cannot ask the harness how long it has, so the allowance is told to it.
# It used to be told twice -- as the registration's `timeout` and as a literal
# in `env` -- and two independently editable numbers that must agree is a defect
# waiting for its first edit. The dangerous direction is silent: LOWER a timeout
# without lowering the env literal and the hook believes it has time it does not,
# overruns, and is killed mid-flight. That is the exact failure the budget
# machinery exists to remove.

REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = REPO_ROOT / "environment/agents/adapters/claude-code/settings.template.json"


def _template() -> dict:
    return json.loads(TEMPLATE.read_text(encoding="utf-8"))


def test_template_authors_no_budget_literal() -> None:
    """Budgets are derived. A literal in the template is the bug, not config."""
    env = _template().get("env") or {}
    authored = [k for k in env if k.endswith("_BUDGET")]
    assert authored == [], (
        f"{authored} authored in settings.template.json env; budgets are derived "
        "from each hook's own `timeout` by derive_budget_env()"
    )


def test_derive_publishes_a_budget_for_every_binding() -> None:
    from reconcile_claude_settings import BUDGET_BINDINGS, derive_budget_env

    env = derive_budget_env(_template())["env"]
    for _hook, (_event, var, _reserve) in BUDGET_BINDINGS.items():
        assert var in env, f"{var} not derived"
        assert int(env[var]) > 0


def test_derived_budget_never_exceeds_the_timeout_it_is_derived_from() -> None:
    """The whole point: the hook must not believe it has more time than it has."""
    from reconcile_claude_settings import BUDGET_BINDINGS, _hook_timeout, derive_budget_env

    template = _template()
    env = derive_budget_env(json.loads(TEMPLATE.read_text(encoding="utf-8")))["env"]
    for hook_file, (event, var, reserve) in BUDGET_BINDINGS.items():
        timeout = _hook_timeout(template, event, hook_file)
        assert timeout is not None, f"{hook_file} has no registration to derive from"
        assert int(env[var]) == max(1, timeout - reserve)
        assert int(env[var]) <= timeout


def test_lowering_a_timeout_lowers_the_budget() -> None:
    """The regression that matters: a timeout edit must carry the budget with it."""
    from reconcile_claude_settings import SESSION_START_NAME, derive_budget_env

    template = _template()
    for group in template["hooks"]["SessionStart"]:
        for hook in group["hooks"]:
            if SESSION_START_NAME in hook["command"]:
                hook["timeout"] = 12
    env = derive_budget_env(template)["env"]
    assert env["L9_SESSION_START_BUDGET"] == "12", (
        "a lowered timeout left a stale, higher budget — the silent direction "
        "of the drift this derivation removes"
    )


def test_a_stale_literal_is_overwritten_not_honoured() -> None:
    from reconcile_claude_settings import derive_budget_env

    template = _template()
    template.setdefault("env", {})["L9_SESSION_START_BUDGET"] = "999"
    env = derive_budget_env(template)["env"]
    assert env["L9_SESSION_START_BUDGET"] != "999"


def test_absent_registration_publishes_no_budget() -> None:
    """Never guess an allowance for a hook that is not registered."""
    from reconcile_claude_settings import derive_budget_env

    template = _template()
    template["hooks"]["Stop"] = []
    template.setdefault("env", {})["L9_MEMORY_WRITEBACK_BUDGET"] = "75"
    env = derive_budget_env(template)["env"]
    assert "L9_MEMORY_WRITEBACK_BUDGET" not in env


def test_deps_helper_default_budget_fits_its_registration() -> None:
    """The one budget still coupled by hand: deps waits, then detaches.

    Its allowance is a UX choice (how long to block session start) rather than a
    kill wall, so it is not derived — but it must still fit inside the timeout,
    or the synchronous report is lost to the reap.
    """
    import re

    template = _template()
    timeout = None
    for group in template["hooks"]["SessionStart"]:
        for hook in group["hooks"]:
            if "session_deps_cloud.sh" in hook["command"]:
                timeout = hook["timeout"]
    assert timeout is not None, "session_deps_cloud.sh must be registered"

    script = (
        REPO_ROOT / "environment/agents/adapters/claude-code/hooks/session_deps_cloud.sh"
    ).read_text(encoding="utf-8")
    match = re.search(r'BUDGET="\$\{L9_SESSION_DEPS_BUDGET:-(\d+)\}"', script)
    assert match, "session_deps_cloud.sh must declare a default budget"
    assert int(match.group(1)) < timeout, (
        f"deps budget {match.group(1)}s does not fit its {timeout}s registration"
    )

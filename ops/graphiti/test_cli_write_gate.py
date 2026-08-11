"""Regression tests for the cmd_write shared-workspace gate.

Direct writes to the shared workspace group (`igor-workspace`) must be
rejected by `graphiti_memory_client.py write`, whether targeted via
`--group-id` or `GRAPHITI_GROUP_ID`. The one sanctioned path into that
group — bootstrap's integration-edge mirror via `_write_episode` — must
stay open.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import graphiti_memory_client as gmc  # noqa: E402

_CLIENT = _HERE / "graphiti_memory_client.py"


def _run_cli(args: list[str], cwd: Path, extra_env: dict[str, str] | None = None):
    env = dict(os.environ)
    env.pop("GRAPHITI_GROUP_ID", None)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, str(_CLIENT), *args],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_cli_write_explicit_igor_workspace_rejected(tmp_path):
    # tmp cwd has no repo match, so the explicit override survives resolution
    # and must be stopped by the workspace gate itself.
    result = _run_cli(
        ["write", "test body", "--group-id", "igor-workspace", "--agent-id", "cursor", "--dry-run"],
        cwd=tmp_path,
    )
    assert result.returncode != 0
    assert "shared workspace group" in result.stderr


def test_cli_write_env_igor_workspace_rejected(tmp_path):
    result = _run_cli(
        ["write", "test body", "--dry-run"],
        cwd=tmp_path,
        extra_env={"GRAPHITI_GROUP_ID": "igor-workspace", "L9_MEMORY_AGENT_ID": "cursor"},
    )
    assert result.returncode != 0
    assert "shared workspace group" in result.stderr


def test_cmd_write_gate_fires_before_any_network(monkeypatch, tmp_path):
    import argparse

    monkeypatch.setattr(gmc, "load_env", lambda: None)
    monkeypatch.setattr(
        gmc,
        "resolve_group_id",
        lambda cwd, explicit=None: {
            "group_id": "igor-workspace",
            "method": "explicit_env",
            "readonly": False,
        },
    )

    def _no_network(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("call_tool must not be reached when the gate fires")

    monkeypatch.setattr(gmc, "call_tool", _no_network)
    args = argparse.Namespace(
        body="test body",
        kind="lesson",
        group_id="igor-workspace",
        dry_run=False,
        agent_id="cursor",
    )
    with pytest.raises(SystemExit) as excinfo:
        gmc.cmd_write(args)
    assert "shared workspace group" in str(excinfo.value)


def test_require_http_url_rejects_file_scheme(monkeypatch):
    with pytest.raises(ValueError, match="non-http"):
        gmc._require_http_url("file:///etc/passwd")
    monkeypatch.setenv("GRAPHITI_MCP_URL", "file:///tmp/evil")
    with pytest.raises(ValueError, match="non-http"):
        gmc.mcp_url()


def test_require_http_url_accepts_localhost():
    assert gmc._require_http_url("http://127.0.0.1:8100/mcp").startswith("http://")


def test_bootstrap_mirror_path_can_still_write_workspace_group(monkeypatch):
    # The sanctioned integration-edge mirror goes through _write_episode
    # directly and must NOT be blocked by cmd_write's gate.
    captured: dict = {}

    def _fake_call_tool(tool: str, payload: dict):
        captured["tool"] = tool
        captured["payload"] = payload
        return {"ok": True}

    monkeypatch.setattr(gmc, "call_tool", _fake_call_tool)
    result = gmc._write_episode(
        "integration_edge:cursor-governance:ib-odoo-19",
        '{"type": "integration_edge"}',
        "igor-workspace",
        "graphiti_memory_client bootstrap mirror",
    )
    assert result == {"ok": True}
    assert captured["tool"] == "add_memory"
    assert captured["payload"]["group_id"] == "igor-workspace"

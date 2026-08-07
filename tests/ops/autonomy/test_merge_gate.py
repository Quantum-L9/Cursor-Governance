"""Tests for ops/autonomy/merge_gate.py"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

GATE = Path(__file__).resolve().parents[3] / "ops" / "autonomy" / "merge_gate.py"


def _run(event: dict, env: dict | None = None) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(GATE)],
        input=json.dumps(event),
        text=True,
        capture_output=True,
        env={**os.environ, **(env or {})},
        check=False,
    )
    return proc.returncode, proc.stdout


def test_denies_gh_pr_merge() -> None:
    code, out = _run({"tool_name": "Bash", "tool_input": {"command": "gh pr merge 12"}})
    assert code == 0
    payload = json.loads(out)
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_denies_force_push() -> None:
    code, out = _run(
        {"tool_name": "Bash", "tool_input": {"command": "git push --force origin HEAD"}}
    )
    assert code == 0
    assert "deny" in out


def test_allows_normal_commit() -> None:
    code, out = _run(
        {"tool_name": "Bash", "tool_input": {"command": "git commit -m 'ok'"}}
    )
    assert code == 0
    assert out.strip() == ""


def test_breakglass_allows_merge() -> None:
    code, out = _run(
        {"tool_name": "Bash", "tool_input": {"command": "gh pr merge 1"}},
        env={"L9_MERGE_AUTHORIZED": "human approved merge of #1"},
    )
    assert code == 0
    assert out.strip() == ""


def test_denies_mcp_merge_tool() -> None:
    code, out = _run({"tool_name": "mcp__github__merge_pull_request", "tool_input": {}})
    assert code == 0
    assert "deny" in out

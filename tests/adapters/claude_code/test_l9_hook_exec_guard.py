"""l9_hook_exec.sh surface guard: Cursor skips gates; Claude enforces."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HOOK = ROOT / "environment" / "agents" / "adapters" / "claude-code" / "hooks" / "l9_hook_exec.sh"
GATE = "memory_gate.py"


def _run(hook_class: str, hook_name: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    cleaned = {
        k: v
        for k, v in os.environ.items()
        if k
        not in {
            "CURSOR_AGENT",
            "CLAUDECODE",
            "CLAUDE_CODE_ENTRYPOINT",
            "CLAUDE_CODE_SESSION_ID",
            "CLAUDE_CODE_REMOTE",
            "L9_GOVERNANCE_SURFACE",
            "L9_SURFACE_GUARD",
            "L9_GOVERNANCE_DIR",
        }
    }
    cleaned["L9_GOVERNANCE_DIR"] = str(ROOT)
    cleaned.update(env)
    return subprocess.run(
        ["bash", str(HOOK), "--class", hook_class, hook_name],
        cwd=str(ROOT),
        env=cleaned,
        capture_output=True,
        text=True,
        input=json.dumps(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": "ops/autonomy/surface_detect.py"},
            }
        ),
        check=False,
    )


def _denied(proc: subprocess.CompletedProcess[str]) -> bool:
    blob = proc.stdout + proc.stderr
    return "permissionDecision" in blob and "deny" in blob


def test_cursor_gate_skipped_without_invoking_memory_gate() -> None:
    proc = _run("gate", GATE, {"CURSOR_AGENT": "1"})
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "skipped" in proc.stderr.lower()
    assert not _denied(proc)
    assert "Memory not hydrated" not in proc.stderr
    assert "Memory not hydrated" not in proc.stdout


def test_claude_gate_still_invoked() -> None:
    proc = _run("gate", GATE, {"CLAUDECODE": "1"})
    assert "skipped" not in proc.stderr.lower()
    assert _denied(proc), proc.stdout + proc.stderr


def test_kill_switch_disables_guard() -> None:
    proc = _run(
        "gate",
        GATE,
        {"CURSOR_AGENT": "1", "L9_SURFACE_GUARD": "0"},
    )
    assert "skipped" not in proc.stderr.lower()
    assert _denied(proc), proc.stdout + proc.stderr


def test_unknown_surface_fail_toward_enforcing() -> None:
    proc = _run("gate", GATE, {})
    assert "skipped" not in proc.stderr.lower()
    assert _denied(proc), proc.stdout + proc.stderr

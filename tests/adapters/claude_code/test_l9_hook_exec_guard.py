"""l9_hook_exec.sh surface guard: Claude observers stay on Claude; named gates retain policy."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HOOK = ROOT / "environment" / "agents" / "adapters" / "claude-code" / "hooks" / "l9_hook_exec.sh"
GATE = "memory_gate.py"
OBSERVER = "memory_prefetch.py"


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


def test_cursor_projected_claude_observer_skips_without_context() -> None:
    proc = _run(
        "observer",
        OBSERVER,
        {"CURSOR_AGENT": "1", "L9_GOVERNANCE_SURFACE": "claude-code"},
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "observer" in proc.stderr.lower()
    assert "skipped" in proc.stderr.lower()
    assert proc.stdout.strip() == ""


def test_cursor_projected_claude_memory_gate_still_takes_named_skip() -> None:
    proc = _run(
        "gate",
        GATE,
        {"CURSOR_AGENT": "1", "L9_GOVERNANCE_SURFACE": "claude-code"},
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "skipped" in proc.stderr.lower()
    assert not _denied(proc)
    assert "Memory not hydrated" not in proc.stderr
    assert "Memory not hydrated" not in proc.stdout


def test_cursor_merge_gate_is_not_added_to_the_claude_only_skip_table() -> None:
    proc = _run(
        "gate",
        "merge_gate_wrap.py",
        {"CURSOR_AGENT": "1", "L9_GOVERNANCE_SURFACE": "claude-code"},
    )
    assert "Claude-only gate" not in proc.stderr
    assert "gate merge_gate_wrap.py skipped" not in proc.stderr


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


def test_unknown_observer_skips_but_unknown_gate_enforces() -> None:
    observer = _run("observer", OBSERVER, {})
    assert observer.returncode == 0, observer.stderr + observer.stdout
    assert "skipped" in observer.stderr.lower()
    assert observer.stdout.strip() == ""

    gate = _run("gate", GATE, {})
    assert "skipped" not in gate.stderr.lower()
    assert _denied(gate), gate.stdout + gate.stderr

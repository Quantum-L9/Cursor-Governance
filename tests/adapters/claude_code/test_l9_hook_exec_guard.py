"""l9_hook_exec.sh surface guard: Claude observers stay on Claude; named gates retain policy."""

from __future__ import annotations

import functools
import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HOOK = ROOT / "environment" / "agents" / "adapters" / "claude-code" / "hooks" / "l9_hook_exec.sh"
GATE = "memory_gate.py"
OBSERVER = "memory_prefetch.py"

#: Kept alive for the module's lifetime; dropping the handle removes the tree.
_HOME_HANDLE: tempfile.TemporaryDirectory[str] | None = None


@functools.cache
def _home_for_this_checkout() -> str:
    """A HOME whose ``.cursor-governance`` is this checkout.

    The launcher resolves its governance tree as ``$HOME/.cursor-governance``
    and honours nothing else (INV-1c), so pointing it at the checkout under
    test is a HOME move, not an ``L9_GOVERNANCE_DIR`` export. The sibling
    launcher suites already drive it this way; this one used the variable and
    was the last caller depending on a redirect that could equally well aim a
    gate at a tree nobody reviewed.
    """
    global _HOME_HANDLE
    _HOME_HANDLE = tempfile.TemporaryDirectory()
    home = Path(_HOME_HANDLE.name)
    (home / ".cursor-governance").symlink_to(ROOT, target_is_directory=True)
    return str(home)


def _run(hook_class: str, hook_name: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    cleaned = {
        k: v
        for k, v in os.environ.items()
        if k
        not in {
            "CURSOR_AGENT",
            "CURSOR_CONVERSATION_ID",
            "CURSOR_EXTENSION_HOST_ROLE",
            "CLAUDECODE",
            "CLAUDE_CODE_ENTRYPOINT",
            "CLAUDE_CODE_SESSION_ID",
            "CLAUDE_CODE_REMOTE",
            "L9_GOVERNANCE_SURFACE",
            "L9_SURFACE_GUARD",
            "L9_GOVERNANCE_DIR",
        }
        and not k.startswith("CURSOR_")
    }
    cleaned["HOME"] = _home_for_this_checkout()
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
    assert proc.returncode == 0, proc.stderr + proc.stdout
    blob = (proc.stderr + proc.stdout).lower()
    assert "cannot evaluate" not in blob
    assert "cannot_run" not in blob
    assert "Claude-only gate" not in proc.stderr
    assert "gate merge_gate_wrap.py skipped" not in proc.stderr


def test_claude_gate_still_invoked() -> None:
    # Not skipped on Claude. Since 691f0216 (CANONICAL_LAW §8.9, SessionStart is
    # memory health-only) no governed write declares a memory precondition, so
    # the invoked memory gate ALLOWS: no deny, no skip line, exit 0. The old
    # assertion that it denied an unhydrated Edit encoded the retired contract.
    proc = _run("gate", GATE, {"CLAUDECODE": "1"})
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "skipped" not in proc.stderr.lower()
    assert not _denied(proc), proc.stdout + proc.stderr
    assert "Memory not hydrated" not in proc.stdout + proc.stderr


def test_claude_gate_decision_reaches_the_host() -> None:
    """A Claude-only gate that does deny proves the launcher runs gates, not
    just declines to skip them: the coding-agent binding gate denies a file
    mutation while a run is active without a verified binding."""
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        run_dir = workspace / ".l9" / "coding-agent"
        run_dir.mkdir(parents=True)
        (run_dir / "run.json").write_text(
            json.dumps({"schema": "l9.coding-agent-run/v1", "binding_record": "binding.json"})
        )
        cleaned = {k: v for k, v in os.environ.items() if not k.startswith("CURSOR_")}
        cleaned.pop("L9_CODING_BINDING_AUTHORIZED", None)
        cleaned.update({"HOME": _home_for_this_checkout(), "CLAUDECODE": "1"})
        proc = subprocess.run(
            ["bash", str(HOOK), "--class", "gate", "coding_agent_binding_gate.py"],
            cwd=str(ROOT),
            env=cleaned,
            capture_output=True,
            text=True,
            input=json.dumps(
                {
                    "tool_name": "Write",
                    "tool_input": {"file_path": str(workspace / "src" / "app.py")},
                    "cwd": str(workspace),
                }
            ),
            check=False,
        )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "skipped" not in proc.stderr.lower()
    assert _denied(proc), proc.stdout + proc.stderr
    assert "coding-agent binding gate" in proc.stdout


def test_kill_switch_disables_guard() -> None:
    # The shell guard is off, so this is not the launcher skip line. The gate
    # itself still allows a Cursor host: Cursor must not wait on a Claude
    # prefetch. L9_SURFACE_GUARD=0 does not turn that allow back into a deny.
    proc = _run(
        "gate",
        GATE,
        {"CURSOR_AGENT": "1", "L9_SURFACE_GUARD": "0"},
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "skipped" not in proc.stderr.lower()
    assert not _denied(proc)


def test_unknown_observer_skips_but_unknown_gate_enforces() -> None:
    observer = _run("observer", OBSERVER, {})
    assert observer.returncode == 0, observer.stderr + observer.stdout
    assert "skipped" in observer.stderr.lower()
    assert observer.stdout.strip() == ""

    gate = _run("gate", GATE, {})
    # memory_gate enforces only on a Claude runtime. An unknown surface is
    # not one, so the launcher skips it instead of denying.
    assert gate.returncode == 0, gate.stderr + gate.stdout
    assert "skipped" in gate.stderr.lower()
    assert "claude-runtime only" in gate.stderr.lower()
    assert not _denied(gate)

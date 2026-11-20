"""l9_hook_exec.sh surface guard: Claude observers stay on Claude; named gates retain policy.

The memory-gate skip depends on the absence of a Claude runtime ALONE, so the
extension environment — Cursor host markers plus a live Claude runtime, which is
how the claude-vscode extension runs the real CLI — dispatches memory_prefetch.py
and memory_gate.py instead of skipping them. The dispatch tests prove that by
execution: a fixture interpreter records the hook path the launcher asked it to
run.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HOOK = ROOT / "environment" / "agents" / "adapters" / "claude-code" / "hooks" / "l9_hook_exec.sh"
GATE = "memory_gate.py"
OBSERVER = "memory_prefetch.py"
CODING_GATE = "coding_agent_binding_gate_wrap.py"
MERGE_GATE = "merge_gate_wrap.py"

#: Kept alive for the module's lifetime; dropping the handle removes the tree.
_HOME_HANDLE: tempfile.TemporaryDirectory[str] | None = None
_HOME = ""

#: Cursor host markers plus a live Claude runtime: the claude-vscode extension
#: runs the real CLI inside Cursor, so the surface detector reports claude-code.
EXTENSION = {
    "CURSOR_AGENT": "1",
    "CLAUDECODE": "1",
    "L9_GOVERNANCE_SURFACE": "claude-code",
}

#: The denial the coding-agent binding gate emits on a real deny; the fixture
#: interpreter plays it back so the launcher's relay of the decision stays on
#: trial even where no locked interpreter exists to run the real hook.
DENY_JSON = json.dumps(
    {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "fixture gate decision",
        }
    }
)


def _home() -> str:
    """A HOME whose ``.cursor-governance`` is a minimal, dispatch-capable tree.

    The launcher resolves its governance tree as ``$HOME/.cursor-governance``
    and honours nothing else (INV-1c), so pointing it at a fixture is a HOME
    move, not an ``L9_GOVERNANCE_DIR`` export. The checkout is the code under
    test, not a bootstrapped HOME: it carries no locked interpreter, so a test
    that needs the launcher to actually RUN a python hook cannot depend on a
    real .venv. The fixture supplies a stub ``.venv/bin/python3`` that records
    the hook path it was asked to execute and plays back a configured decision,
    plus the venv-readiness shim the launcher sources on its dispatch path.
    Hook bodies are stubs too — this suite is on trial for the launcher's
    dispatch decision, not the hooks' policy.
    """
    global _HOME, _HOME_HANDLE
    if _HOME:
        return _HOME
    _HOME_HANDLE = tempfile.TemporaryDirectory()
    home = Path(_HOME_HANDLE.name)
    gov = home / ".cursor-governance"
    gov.mkdir(parents=True)
    (gov / "CANONICAL_LAW.md").write_text("fixture governance SSOT\n", encoding="utf-8")
    lib = gov / "ops" / "scripts" / "lib"
    lib.mkdir(parents=True)
    # The launcher sources $GOV_DIR/ops/scripts/lib/venv_ready.sh and calls
    # venv_ready_exec <root> <py> <hook>. The real one waits on the install
    # lock; a fixture tree has no lock to wait on, so exec straight through.
    (lib / "venv_ready.sh").write_text('venv_ready_exec() { exec "$2" "$3"; }\n', encoding="utf-8")
    hooks = gov / "environment" / "agents" / "adapters" / "claude-code" / "hooks"
    hooks.mkdir(parents=True)
    for name in (GATE, OBSERVER, CODING_GATE, MERGE_GATE):
        (hooks / name).write_text("# fixture hook: run by the stub interpreter\n", encoding="utf-8")
    py = gov / ".venv" / "bin" / "python3"
    py.parent.mkdir(parents=True)
    py.write_text(
        "#!/usr/bin/env bash\n"
        "# Stub interpreter: record what the launcher dispatched, play the\n"
        "# decision the test configured, and pass the exit code through.\n"
        'printf \'%s\\n\' "${1:?}" >> "${L9_FIXTURE_RUN_LOG:?}"\n'
        'if [ -n "${L9_FIXTURE_STDOUT:-}" ]; then printf \'%s\\n\' "$L9_FIXTURE_STDOUT"; fi\n'
        'exit "${L9_FIXTURE_EXIT:-0}"\n',
        encoding="utf-8",
    )
    py.chmod(0o755)
    _HOME = str(home)
    return _HOME


def _run(
    hook_class: str,
    hook_name: str,
    env: dict[str, str],
    *,
    run_log: Path | None = None,
) -> subprocess.CompletedProcess[str]:
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
            "L9_FIXTURE_RUN_LOG",
            "L9_FIXTURE_STDOUT",
            "L9_FIXTURE_EXIT",
        }
        and not k.startswith("CURSOR_")
    }
    cleaned["HOME"] = _home()
    if run_log is not None:
        cleaned["L9_FIXTURE_RUN_LOG"] = str(run_log)
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


def test_cursor_projected_claude_memory_gate_skips_without_a_claude_runtime() -> None:
    # A projected L9_GOVERNANCE_SURFACE=claude-code is not a runtime: Cursor
    # executes this settings file without CLAUDECODE, and its writes must not
    # wait on the Claude prefetch (fix #678).
    proc = _run(
        "gate",
        GATE,
        {"CURSOR_AGENT": "1", "L9_GOVERNANCE_SURFACE": "claude-code"},
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "skipped" in proc.stderr.lower()
    assert "claude-runtime only" in proc.stderr.lower()
    assert not _denied(proc)
    assert "Memory not hydrated" not in proc.stderr
    assert "Memory not hydrated" not in proc.stdout


def test_cursor_merge_gate_is_not_added_to_the_claude_only_skip_table(
    tmp_path: Path,
) -> None:
    run_log = tmp_path / "runs.log"
    proc = _run(
        "gate",
        MERGE_GATE,
        {"CURSOR_AGENT": "1", "L9_GOVERNANCE_SURFACE": "claude-code"},
        run_log=run_log,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    blob = (proc.stderr + proc.stdout).lower()
    assert "cannot evaluate" not in blob
    assert "cannot_run" not in blob
    assert "Claude-only gate" not in proc.stderr
    assert "gate merge_gate_wrap.py skipped" not in proc.stderr
    assert MERGE_GATE in run_log.read_text(encoding="utf-8")


def test_claude_gate_still_invoked(tmp_path: Path) -> None:
    # Not skipped on Claude; the launcher dispatches the gate. Since 691f0216
    # (CANONICAL_LAW §8.9, SessionStart is memory health-only) no governed
    # write declares a memory precondition, so the real memory gate ALLOWS:
    # no deny, no skip line, exit 0. The old assertion that it denied an
    # unhydrated Edit encoded the retired contract.
    run_log = tmp_path / "runs.log"
    proc = _run("gate", GATE, {"CLAUDECODE": "1"}, run_log=run_log)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "skipped" not in proc.stderr.lower()
    assert not _denied(proc), proc.stdout + proc.stderr
    assert "Memory not hydrated" not in proc.stdout + proc.stderr
    assert GATE in run_log.read_text(encoding="utf-8")


def test_claude_gate_decision_reaches_the_host(tmp_path: Path) -> None:
    """A gate's decision — deny payload on stdout, exit code — passes through
    the launcher unchanged; the launcher runs gates, it does not merely
    decline to skip them.

    The real coding-agent binding gate denies a file mutation while a run is
    active without a verified binding. Running it here would need the locked
    interpreter this checkout does not carry, so the fixture interpreter plays
    the denial the real gate emits; the property on trial is the launcher's
    relay of that decision to the host.
    """
    run_log = tmp_path / "runs.log"
    proc = _run(
        "gate",
        CODING_GATE,
        {"CLAUDECODE": "1", "L9_FIXTURE_STDOUT": DENY_JSON},
        run_log=run_log,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "skipped" not in proc.stderr.lower()
    assert _denied(proc), proc.stdout + proc.stderr
    assert CODING_GATE in run_log.read_text(encoding="utf-8")


def test_kill_switch_disables_guard(tmp_path: Path) -> None:
    # The shell guard is off, so there is no launcher skip at all — not the
    # runtime skip, not the surface table. The dispatch proceeds and the
    # decision is the hook's own: the real memory gate allows a Cursor host,
    # because Cursor must not wait on a Claude prefetch. L9_SURFACE_GUARD=0
    # does not turn that allow back into a deny.
    run_log = tmp_path / "runs.log"
    proc = _run(
        "gate",
        GATE,
        {"CURSOR_AGENT": "1", "L9_SURFACE_GUARD": "0"},
        run_log=run_log,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "skipped" not in proc.stderr.lower()
    assert not _denied(proc)
    assert GATE in run_log.read_text(encoding="utf-8")


def test_unknown_surface_observer_skips_and_gate_skips_on_missing_runtime() -> None:
    observer = _run("observer", OBSERVER, {})
    assert observer.returncode == 0, observer.stderr + observer.stdout
    assert "skipped" in observer.stderr.lower()
    assert observer.stdout.strip() == ""

    gate = _run("gate", GATE, {})
    # An unknown surface does not itself skip a gate (fail toward closed);
    # the absence of a Claude runtime is what skips memory_gate here.
    assert gate.returncode == 0, gate.stderr + gate.stdout
    assert "skipped" in gate.stderr.lower()
    assert "claude-runtime only" in gate.stderr.lower()
    assert not _denied(gate)


def test_extension_environment_runs_memory_prefetch(tmp_path: Path) -> None:
    """Cursor host markers plus a live Claude runtime: the claude-vscode extension.

    The observer must not take the Claude-observer surface skip, and the
    launcher must dispatch it — the recorded hook path proves the run.
    """
    run_log = tmp_path / "runs.log"
    proc = _run("observer", OBSERVER, EXTENSION, run_log=run_log)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "skipped" not in proc.stderr.lower()
    assert OBSERVER in run_log.read_text(encoding="utf-8")


def test_extension_environment_runs_memory_gate(tmp_path: Path) -> None:
    """The memory-gate skip depends on the absence of a Claude runtime ALONE.

    The extension environment has a live Claude runtime AND Cursor host
    markers. The host markers must not veto the gate: the cursor-host disjunct
    this test guards against skipped the gate in exactly the environment the
    surface detector reports as claude-code — two detectors disagreeing about
    the same process. The recorded hook path proves the dispatch.
    """
    run_log = tmp_path / "runs.log"
    proc = _run("gate", GATE, EXTENSION, run_log=run_log)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "skipped" not in proc.stderr.lower()
    assert not _denied(proc)
    assert GATE in run_log.read_text(encoding="utf-8")


def test_real_memory_gate_evaluates_an_extension_session(monkeypatch) -> None:
    """The real gate must read the event when the extension runtime is live.

    The launcher test records a stub interpreter. This one imports the gate:
    a Cursor host marker plus a Claude runtime reaches event evaluation, and a
    Cursor host with no Claude runtime still returns before the event.
    """
    import importlib
    import sys

    sys.path.insert(0, str(HOOK.parent))
    sys.path.insert(0, str(ROOT / "ops" / "autonomy"))
    import memory_gate

    importlib.reload(memory_gate)
    seen: dict[str, bool] = {}

    def _load(_stream: object) -> None:
        seen["event"] = True
        raise json.JSONDecodeError("marker", "", 0)

    monkeypatch.setattr(memory_gate.json, "load", _load)
    for key in (
        "CLAUDECODE",
        "CLAUDE_CODE_ENTRYPOINT",
        "CLAUDE_CODE_SESSION_ID",
        "CLAUDE_CODE_REMOTE",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("CURSOR_AGENT", "1")
    assert memory_gate.main() == 0
    assert "event" not in seen

    for key, value in EXTENSION.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("CLAUDE_CODE_ENTRYPOINT", "claude-vscode")
    assert memory_gate.main() == 0
    assert seen.get("event") is True

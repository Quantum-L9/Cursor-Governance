"""CI-parity Claude hooks: push detection, gate verdicts, Cursor invariance."""

from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
REPO_ROOT = Path(__file__).resolve().parents[5]


def _load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"{name}_test", HOOKS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def claude(monkeypatch: pytest.MonkeyPatch) -> None:
    autonomy = str(REPO_ROOT / "ops" / "autonomy")
    if autonomy not in sys.path:
        sys.path.insert(0, autonomy)
    from surface_detect import scrub_cursor_host_markers

    scrub_cursor_host_markers(monkeypatch.delenv)
    monkeypatch.delenv("L9_CI_PARITY", raising=False)
    monkeypatch.setenv("L9_GOVERNANCE_SURFACE", "claude-code")


def _stub_runner(tmp_path: Path, rc: int, out: str) -> Path:
    stub = tmp_path / "runner.py"
    stub.write_text(f"import sys\nprint({out!r})\nsys.exit({rc})\n")
    return stub


def _run_main(module: ModuleType, event: dict, monkeypatch: pytest.MonkeyPatch) -> int:
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    return module.main()


@pytest.mark.parametrize(
    "command, expected",
    [
        ("git push", "."),
        ("git push -u origin feat/x", "."),
        ("cd x && git -C sub push origin HEAD", "sub"),
        ("VAR=1 git -c core.x=y push", "."),
        ("git push --dry-run", None),
        ("git push origin --delete old", None),
        ("git status && echo push", None),
        ("gitk push", None),
        ("make pr", None),
    ],
)
def test_push_target(command: str, expected: str | None, tmp_path: Path) -> None:
    gate = _load("ci_parity_push_gate")
    got = gate.push_target(command, tmp_path)
    assert got == (
        None
        if expected is None
        else (tmp_path / expected).resolve()
        if expected != "."
        else tmp_path
    )


def test_push_hook_does_not_scan(
    claude: None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    gate = _load("ci_parity_push_gate")
    rc = _run_main(
        gate,
        {"tool_name": "Bash", "tool_input": {"command": "git push"}, "cwd": str(tmp_path)},
        monkeypatch,
    )
    captured = capsys.readouterr()
    assert rc == 0 and captured.err == "" and captured.out == ""
    assert "--gate" not in (HOOKS / "ci_parity_push_gate.py").read_text()


def test_gate_ignores_non_push_commands(
    claude: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = _load("ci_parity_push_gate")
    rc = _run_main(
        gate,
        {"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}, "cwd": str(tmp_path)},
        monkeypatch,
    )
    assert rc == 0


@pytest.mark.parametrize(
    "env", [{"CURSOR_AGENT": "1"}, {"L9_CI_PARITY": "0", "L9_GOVERNANCE_SURFACE": "claude-code"}]
)
def test_gate_is_silent_on_cursor_and_with_the_kill_switch(
    env: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    gate = _load("ci_parity_push_gate")
    rc = _run_main(
        gate,
        {"tool_name": "Bash", "tool_input": {"command": "git push"}, "cwd": str(tmp_path)},
        monkeypatch,
    )
    captured = capsys.readouterr()
    assert rc == 0 and captured.out == "" and captured.err == ""


def test_posttool_edit_returns_findings_as_context(
    claude: None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    hook = _load("ci_parity_posttool")
    monkeypatch.setattr(
        hook,
        "RUNNER",
        _stub_runner(tmp_path, 0, "ci-parity (edited lines):\n  a.sh:3: [error] SC1000 — bad"),
    )
    target = tmp_path / "a.sh"
    target.write_text("x\n")
    rc = _run_main(
        hook, {"tool_name": "Edit", "tool_input": {"file_path": str(target)}}, monkeypatch
    )
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    assert "a.sh:3" in payload["hookSpecificOutput"]["additionalContext"]


def test_posttool_is_silent_on_cursor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CURSOR_AGENT", "1")
    hook = _load("ci_parity_posttool")
    monkeypatch.setattr(hook, "RUNNER", _stub_runner(tmp_path, 0, "findings"))
    target = tmp_path / "a.sh"
    target.write_text("x\n")
    assert (
        _run_main(
            hook, {"tool_name": "Edit", "tool_input": {"file_path": str(target)}}, monkeypatch
        )
        == 0
    )
    assert capsys.readouterr().out == ""


def test_push_gate_is_not_a_fail_closed_gate() -> None:
    # A fail-closed gate on every Bash call blocked the whole shell when the
    # governance clone lacked this file (observed while publishing this change).
    launcher = (HOOKS / "l9_hook_exec.sh").read_text()
    assert "ci_parity_push_gate.py" not in launcher


def test_settings_register_both_hooks_through_the_launcher() -> None:
    for path in (HOOKS.parent / "settings.template.json", REPO_ROOT / ".claude" / "settings.json"):
        hooks = json.loads(path.read_text())["hooks"]
        pre = json.dumps(hooks["PreToolUse"])
        post = json.dumps(hooks["PostToolUse"])
        assert "--class observer ci_parity_push_gate.py" in pre
        assert "--class gate ci_parity_push_gate.py" not in pre
        assert "--class observer ci_parity_posttool.py" in post


def test_absent_push_gate_fails_open_through_the_real_launcher(tmp_path: Path) -> None:
    """The lockout regression: governance clone without the hook file → allow, not block."""
    gov = tmp_path / ".cursor-governance"
    hooks_dir = gov / "environment" / "agents" / "adapters" / "claude-code" / "hooks"
    hooks_dir.mkdir(parents=True)
    (gov / "CANONICAL_LAW.md").write_text("stub\n")
    launcher = hooks_dir / "l9_hook_exec.sh"
    launcher.write_text((HOOKS / "l9_hook_exec.sh").read_text())
    env = {
        "HOME": str(tmp_path),
        "PATH": "/usr/bin:/bin",
        "L9_GOVERNANCE_SURFACE": "claude-code",
        "L9_HOOK_SKIP_LOG": str(tmp_path / "skips.log"),
    }
    proc = subprocess.run(
        ["bash", str(launcher), "--class", "observer", "ci_parity_push_gate.py"],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "git push"}}),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr


def test_make_pr_does_not_start_ci_parity() -> None:
    text = (REPO_ROOT / "ops" / "scripts" / "run_pr_gate.sh").read_text()
    assert "_gate_ci_parity_enabled" not in text
    assert "_gate_run_ci_parity" not in text
    assert "_wave_start ci-parity" not in text


def test_deps_hook_self_heals_and_fingerprints_package_lock_json() -> None:
    deps = (HOOKS / "session_deps_cloud.sh").read_text()
    assert '"$_CI_PARITY_INSTALL" --check' in deps and "setsid" in deps
    assert "package-lock.json" in deps and "package-lock.yaml" not in deps
    setup = (HOOKS.parent / "web" / "setup.sh").read_text()
    assert "ops/ci_parity/install.py" in setup and "SessionStart retries" in setup

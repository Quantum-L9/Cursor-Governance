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
    monkeypatch.delenv("CURSOR_AGENT", raising=False)
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


def test_gate_blocks_with_findings_on_stderr(
    claude: None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    gate = _load("ci_parity_push_gate")
    monkeypatch.setattr(gate, "RUNNER", _stub_runner(tmp_path, 2, "BLOCK a.py:3: [error] rule — m"))
    rc = _run_main(
        gate,
        {"tool_name": "Bash", "tool_input": {"command": "git push"}, "cwd": str(tmp_path)},
        monkeypatch,
    )
    err = capsys.readouterr().err
    assert rc == 2 and "BLOCK a.py:3" in err and "L9_CI_PARITY=0" in err


def test_gate_allows_a_clean_push_silently(
    claude: None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    gate = _load("ci_parity_push_gate")
    monkeypatch.setattr(gate, "RUNNER", _stub_runner(tmp_path, 0, "clean"))
    rc = _run_main(
        gate,
        {"tool_name": "Bash", "tool_input": {"command": "git push"}, "cwd": str(tmp_path)},
        monkeypatch,
    )
    captured = capsys.readouterr()
    assert rc == 0 and captured.err == "" and captured.out == ""


def test_gate_ignores_non_push_commands(
    claude: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate = _load("ci_parity_push_gate")
    monkeypatch.setattr(gate, "RUNNER", _stub_runner(tmp_path, 2, "would block"))
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
    monkeypatch.setattr(gate, "RUNNER", _stub_runner(tmp_path, 2, "would block"))
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


def test_launcher_treats_the_push_gate_as_claude_only() -> None:
    launcher = (HOOKS / "l9_hook_exec.sh").read_text()
    assert "local_execution_gate_wrap.py|memory_gate.py|ci_parity_push_gate.py)" in launcher


def test_settings_register_both_hooks_through_the_launcher() -> None:
    for path in (HOOKS.parent / "settings.template.json", REPO_ROOT / ".claude" / "settings.json"):
        hooks = json.loads(path.read_text())["hooks"]
        pre = json.dumps(hooks["PreToolUse"])
        post = json.dumps(hooks["PostToolUse"])
        assert "--class gate ci_parity_push_gate.py" in pre
        assert "--class observer ci_parity_posttool.py" in post


def _gate_fn() -> str:
    text = (REPO_ROOT / "ops" / "scripts" / "run_pr_gate.sh").read_text()
    start = text.index("_gate_ci_parity_enabled() {")
    end = text.index("\n}\n", start) + 3
    return text[start:end]


@pytest.mark.parametrize(
    "env, expected",
    [
        ({"L9_GOVERNANCE_SURFACE": "claude-code"}, "yes"),
        ({"CURSOR_AGENT": "1"}, "no"),
        ({"L9_GOVERNANCE_SURFACE": "claude-code", "L9_CI_PARITY": "0"}, "no"),
    ],
)
def test_make_pr_wave_runs_ci_parity_only_on_claude(env: dict, expected: str) -> None:
    script = f"GOV_ROOT={REPO_ROOT}\n{_gate_fn()}\n_gate_ci_parity_enabled && echo yes || echo no\n"
    base = {"PATH": "/usr/bin:/bin", "HOME": str(Path.home())}
    out = subprocess.run(
        ["bash", "-c", script], env={**base, **env}, capture_output=True, text=True, check=True
    )
    assert out.stdout.strip() == expected


def test_wave_start_is_guarded() -> None:
    text = (REPO_ROOT / "ops" / "scripts" / "run_pr_gate.sh").read_text()
    assert (
        "if _gate_ci_parity_enabled; then\n  _wave_start ci-parity _gate_run_ci_parity\nfi" in text
    )


def test_deps_hook_self_heals_and_fingerprints_package_lock_json() -> None:
    deps = (HOOKS / "session_deps_cloud.sh").read_text()
    assert '"$_CI_PARITY_INSTALL" --check' in deps and "setsid" in deps
    assert "package-lock.json" in deps and "package-lock.yaml" not in deps
    setup = (HOOKS.parent / "web" / "setup.sh").read_text()
    assert "ops/ci_parity/install.py" in setup and "SessionStart retries" in setup

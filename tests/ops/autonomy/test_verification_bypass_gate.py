"""The verification-bypass plane must deny the reflex, not ordinary git.

The failure this gate exists to stop: an agent that learned "commits run hooks"
elsewhere types `--no-verify` or `-c core.hooksPath=` here, where no commit hook
exists at all. The command succeeds, looks like a bypass that worked, and the
real verification (`make pr-check` / `make pr`) is never run.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ops" / "autonomy"))

from verification_bypass_gate import (  # noqa: E402
    POLICY_PATH,
    command_bypasses_verification,
    human_authorized,
    policy,
)


@pytest.mark.parametrize(
    "command",
    [
        "git commit --no-verify -m x",
        "git commit -n -m x",
        "git -c core.hooksPath=/dev/null commit -m x",
        "git -c core.hookspath=/dev/null commit -m x",
        "cd /repo && git commit -n -m x",
        "HUSKY=0 git commit -m x",
        "SKIP=ruff make pr",
        "PRE_COMMIT_ALLOW_NO_CONFIG=1 pre-commit run",
        "GIT_CONFIG_GLOBAL=/dev/null git commit -m x",
    ],
)
def test_bypass_is_denied(command: str) -> None:
    reason = command_bypasses_verification(command)
    assert reason, f"gate missed a verification bypass: {command}"
    assert "make pr-check" in reason, "the deny must name where verification actually runs"


@pytest.mark.parametrize(
    "command",
    [
        "git commit -m x",
        "git commit --amend -m x",
        'git commit -m "document --no-verify usage"',
        "git -C /repo commit -m x",
        "git log -n 5",
        "git rebase -n main",  # -n is not --no-verify on rebase
        "echo --no-verify",
        "make pr-check",
        "",
    ],
)
def test_ordinary_commands_are_untouched(command: str) -> None:
    assert command_bypasses_verification(command) is None


def test_the_exact_command_from_the_incident_is_denied() -> None:
    """2026-08-28: this ran, and nothing stopped it."""
    reason = command_bypasses_verification(
        "git -c core.hooksPath=/dev/null commit -q -F - <<'EOF'\nmsg\nEOF"
    )
    assert reason and "core.hooksPath" in reason


def test_human_authorization_needs_a_real_reason() -> None:
    env_name = policy()["authorization_env"]
    assert human_authorized({env_name: ""}) is False
    assert human_authorized({env_name: "1"}) is False
    assert human_authorized({env_name: "yes"}) is False
    assert human_authorized({env_name: "ops: rotating a signing key"}) is True


def test_authorized_human_may_proceed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(policy()["authorization_env"], "ops: recovering a corrupt hook env")
    assert command_bypasses_verification("git commit --no-verify -m x") is None


def test_unreadable_policy_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """No classification is possible without the policy, so nothing is allowed."""
    import verification_bypass_gate as gate

    monkeypatch.setattr(gate, "POLICY_PATH", ROOT / "ops" / "config" / "does-not-exist.json")
    gate.policy.cache_clear()
    try:
        reason = gate.command_bypasses_verification("git commit -m x")
        assert reason and "fail closed" in reason
    finally:
        gate.policy.cache_clear()


def test_policy_is_the_single_machine_readable_source() -> None:
    data = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    assert data["schema"] == "l9.verification-bypass.v1"
    # The tokens the gate enforces come from the file, never from a second list.
    assert "--no-verify" in data["bypass_flags"]
    assert "core.hooksPath" in data["bypass_config_keys"]
    assert "git commit" in data["guarded_commands"]


def test_gate_plane_denies_through_local_execution_gate(tmp_path: Path) -> None:
    """Wired ahead of the git/gh exemption, or a git command would slip past."""
    sys.path.insert(0, str(ROOT / "ops" / "autonomy"))
    import local_execution_gate as leg

    reason = leg.evaluate("Bash", {"command": "git commit --no-verify -m x"}, root=tmp_path)
    assert reason and "verification-bypass" in reason


def _claude(raw: str) -> str:
    """Run the Claude PreToolUse entry point over a raw payload, return stdout."""
    import io
    import json as _json
    from contextlib import redirect_stdout

    sys.path.insert(0, str(ROOT / "ops" / "autonomy"))
    import local_execution_gate as leg

    stdin, sys.stdin = sys.stdin, io.StringIO(raw)
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            leg.main_claude()
    finally:
        sys.stdin = stdin
    out = buf.getvalue().strip()
    return _json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out else "allow"


def test_payload_plane_denies_before_the_git_exemption() -> None:
    """The regression that made the first wiring dead code.

    ``payload_is_git_or_gh`` short-circuits ``main_claude`` before the event is
    parsed, so a plane wired only into ``evaluate()`` never sees a git command.
    Wiring it into ``evaluate`` alone passed its unit test and denied nothing.
    """
    raw = (
        '{"tool_name":"Bash","tool_input":'
        '{"command":"git -c core.hooksPath=/dev/null commit -q -m x"},"cwd":"."}'
    )
    assert _claude(raw) == "deny"


def test_payload_plane_leaves_ordinary_commits_alone() -> None:
    raw = '{"tool_name":"Bash","tool_input":{"command":"git commit -m x"},"cwd":"."}'
    assert _claude(raw) == "allow"


def test_cursor_surface_denies_the_same_command() -> None:
    import io
    import json as _json
    from contextlib import redirect_stdout

    sys.path.insert(0, str(ROOT / "ops" / "autonomy"))
    import local_execution_gate as leg

    stdin, sys.stdin = sys.stdin, io.StringIO('{"command":"git commit --no-verify -m x"}')
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            leg.main_cursor_shell()
    finally:
        sys.stdin = stdin
    assert _json.loads(buf.getvalue())["permission"] == "deny"

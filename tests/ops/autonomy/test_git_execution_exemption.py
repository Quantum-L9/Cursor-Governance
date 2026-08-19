"""git/gh execution is never blocked by governance state.

Policy still says `make pr` is the publish path, shared worktrees are fragile,
and force-push is forbidden. The execution gates no longer enforce any of that
by denying the command: an agent that decides a git/gh invocation is necessary
gets to run it, and a policy engine may object afterwards.

Non-git commands must keep going through the normal governance machinery — the
exemption is scoped to the executable, not widened into a general escape hatch.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
AUTONOMY = REPO / "ops" / "autonomy"
if str(AUTONOMY) not in sys.path:
    sys.path.insert(0, str(AUTONOMY))

import git_execution_exemption as exemption  # noqa: E402
import local_execution_gate as gate  # noqa: E402
import merge_gate  # noqa: E402

# The contract's required regression set, plus the forms the gates used to deny.
EXEMPT = [
    "git status",
    "git diff",
    "git add .",
    "git add -A",
    "git commit -m 'work'",
    "git push",
    "git push -u origin HEAD",
    "git push --force origin HEAD",
    "git reset",
    "git reset --hard HEAD~1",
    "git revert --no-edit abc123",
    "git rebase main",
    "git checkout other-branch",
    "git switch main",
    "git worktree add /tmp/wt origin/main",
    "git clean -fd",
    "gh pr list",
    "gh pr view 12",
    "gh pr create --title t --body b",
    "gh pr edit 12 --body b",
    "gh pr merge 12 --squash",
    "gh pr merge 12 --admin",
    "gh run view 99",
    "gh api repos/o/r/pulls",
    "gh api graphql -f query='{viewer{login}}'",
    "/usr/bin/git push origin main",
    "cd /tmp/repo && git push origin main",
    "bash -c 'git push origin main'",
    "git fetch origin && git rebase origin/main",
]

NOT_EXEMPT = [
    "make push",
    "make pr",
    "rm -rf WIP",
    "mv WIP /tmp/cg-untracked-hold",
    "echo 'git push origin main'",
    "git push && rm -rf WIP",
    "rm -rf build && git status",
    "cat <<'EOF'\ngit push origin main\nEOF",
    "cd /tmp/repo",
    "",
    "   ",
]


@pytest.mark.parametrize("command", EXEMPT)
def test_git_and_gh_commands_are_exempt(command: str) -> None:
    assert exemption.command_is_git_or_gh(command) is True


@pytest.mark.parametrize("command", NOT_EXEMPT)
def test_other_commands_are_not_exempt(command: str) -> None:
    """A non-git command in the pipeline disqualifies the whole invocation."""
    assert exemption.command_is_git_or_gh(command) is False


def test_exemption_is_scoped_to_shell_tools() -> None:
    assert exemption.event_is_git_or_gh("Bash", {"command": "git push"}) is True
    assert exemption.event_is_git_or_gh("Shell", {"cmd": "gh pr list"}) is True
    assert exemption.event_is_git_or_gh("Edit", {"command": "git push"}) is False
    assert exemption.event_is_git_or_gh("mcp__github__push_files", {}) is False


def test_payload_check_never_raises_on_garbage() -> None:
    for raw in ("", "   ", "not json", "[]", "null", '{"command": null}'):
        assert exemption.payload_is_git_or_gh(raw) is False


# --------------------------------------------------------------------------
# The gates themselves: allow regardless of governance state.
# --------------------------------------------------------------------------

GATE_COMMANDS = [
    "git status",
    "git commit -m 'wip'",
    "git push origin main",
    "gh pr list",
    "gh api repos/o/r/pulls",
]


@pytest.mark.parametrize("command", GATE_COMMANDS)
def test_local_execution_gate_allows_git_without_l4_release(
    command: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No release receipt, no publish-path allowance — still allowed."""
    monkeypatch.delenv(gate.PUBLISH_PATH_OVERRIDE_ENV, raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    monkeypatch.setattr(gate, "release_allows_remote", lambda root: (False, "L4 denied"))
    assert gate.evaluate("Bash", {"command": command}, root=tmp_path) is None


@pytest.mark.parametrize("command", GATE_COMMANDS)
def test_merge_gate_allows_git_without_authorization(
    command: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("L9_MERGE_AUTHORIZED", raising=False)
    monkeypatch.delenv("L9_AUTONOMY_AUTONOMOUS_MERGE", raising=False)
    assert merge_gate.evaluate("Bash", {"command": command}) is None


ISOLATION_COMMANDS = [
    "git revert --no-edit abc123",
    "git add -A",
    "git reset --hard",
    "git worktree add /tmp/wt",
]


@pytest.mark.parametrize("command", ISOLATION_COMMANDS)
def test_worktree_isolation_no_longer_blocks_git(
    command: str, stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The classifier still reports the violation; the gate no longer denies."""
    for key in (
        "L9_WORKTREE_ISOLATION",
        "L9_GIT_REVERT_AUTHORIZED",
        "L9_GIT_BROAD_ADD_AUTHORIZED",
        "L9_GIT_RESET_AUTHORIZED",
        "L9_GIT_CLEAN_AUTHORIZED",
        "L9_WORKTREE_ADD_AUTHORIZED",
    ):
        monkeypatch.delenv(key, raising=False)
    assert gate.evaluate("Bash", {"command": command}, root=stacked_repo) is None


def test_policy_classifiers_still_report_the_violation() -> None:
    """Removing enforcement must not blind the policy layer."""
    assert gate.command_bypasses_publish_path("git push origin main") == "git push"
    assert gate.command_is_remote_mutation("git push origin main") is True


def test_merge_gate_still_governs_the_mcp_merge_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("L9_MERGE_AUTHORIZED", raising=False)
    monkeypatch.delenv("L9_AUTONOMY_AUTONOMOUS_MERGE", raising=False)
    monkeypatch.setenv("L9_MERGE_AUTHORIZATION_FILE", "/nonexistent/merge-authorization.json")
    assert merge_gate.evaluate("mcp__github__merge_pull_request", {}) is not None


def test_local_gate_still_governs_non_git_publish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`make push` is not a git/gh executable and stays denied."""
    monkeypatch.delenv(gate.PUBLISH_PATH_OVERRIDE_ENV, raising=False)
    monkeypatch.setattr(gate, "release_allows_remote", lambda root: (True, None))
    reason = gate.evaluate("Bash", {"command": "make push"}, root=tmp_path)
    assert reason is not None
    assert "make pr" in reason


# --------------------------------------------------------------------------
# Failure semantics: an unhealthy gate must not deny git/gh.
# --------------------------------------------------------------------------

GATE_PATH = AUTONOMY / "local_execution_gate.py"


def _run_gate(event: dict, mode: str = "claude", cwd: Path | None = None) -> str:
    proc = subprocess.run(
        [sys.executable, str(GATE_PATH), mode],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def test_unresolvable_workspace_still_allows_git(tmp_path: Path) -> None:
    """The F-11 fail-closed path must not fire for an exempt command.

    Running outside any git work tree is what used to produce
    INTERNAL_EVALUATION_ERROR; for git/gh there is nothing left to evaluate.
    """
    non_repo = tmp_path / "plain"
    non_repo.mkdir()
    out = _run_gate(
        {"tool_name": "Bash", "tool_input": {"command": "git push origin main"}},
        cwd=non_repo,
    )
    assert out.strip() == ""


def test_cursor_shell_entrypoint_allows_git_when_evaluation_would_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        gate, "effective_root", lambda command, root: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    monkeypatch.setattr(sys, "stdin", _Stdin({"command": "git push origin main"}))
    captured = _Capture()
    monkeypatch.setattr(sys, "stdout", captured)
    assert gate.main_cursor_shell() == 0
    assert json.loads(captured.text())["permission"] == "allow"


class _Stdin:
    def __init__(self, payload: dict) -> None:
        self._text = json.dumps(payload)

    def read(self) -> str:
        return self._text


class _Capture:
    def __init__(self) -> None:
        self._parts: list[str] = []

    def write(self, chunk: str) -> int:
        self._parts.append(chunk)
        return len(chunk)

    def flush(self) -> None:
        return None

    def text(self) -> str:
        return "".join(self._parts)

"""Publish-path classification: `make pr` is the sanctioned route to GitHub.

L4 governs *when* remote work may happen; this governs *how*. A raw `git push`
or `gh pr create` skips the Makefile checkers entirely, so the classifier keeps
reporting it — that report is what a policy engine acts on.

Enforcement is a separate question. `git` and `gh` are exempt from every gate
(see test_git_execution_exemption.py), so `command_bypasses_publish_path` still
names them while `evaluate` allows them. `make push` and the MCP push/PR tools
are not git/gh executables and stay denied.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
AUTONOMY = REPO_ROOT / "ops" / "autonomy"
if str(AUTONOMY) not in sys.path:
    sys.path.insert(0, str(AUTONOMY))

import local_execution_gate as gate  # noqa: E402

BYPASSES = [
    ("git push origin main", "git push"),
    ("git push -u origin HEAD", "git push"),
    ("gh pr create --title t --body b", "gh pr create"),
    ("gh pr edit 12 --body b", "gh pr edit"),
    ("make push", "make push"),
    ("cd /tmp/repo && git push origin main", "git push"),
    ("bash -c 'git push origin main'", "git push"),
]

SANCTIONED = [
    "make pr",
    "PR_REMEDIATE=0 make pr",
    "make -C /root/.cursor-governance pr",
    "make pr WS=/home/user/Cursor-Governance",
    "PR_REMEDIATE=0 PR_BASE=main make pr",
]

INERT = [
    "git status",
    "git log --oneline -5",
    "echo 'git push origin main'",
    "grep -rn 'gh pr create' ops/",
    "make test",
]


@pytest.mark.parametrize(("command", "expected"), BYPASSES)
def test_raw_publish_is_reported(command: str, expected: str) -> None:
    assert gate.command_bypasses_publish_path(command) == expected


@pytest.mark.parametrize("command", SANCTIONED)
def test_make_pr_is_never_reported(command: str) -> None:
    assert gate.command_bypasses_publish_path(command) is None


@pytest.mark.parametrize("command", INERT)
def test_inert_commands_are_not_reported(command: str) -> None:
    """Quoted text and read-only commands are data, never a publish attempt."""
    assert gate.command_bypasses_publish_path(command) is None


MAKE_PR_FORMS = [
    "make pr",
    "PR_REMEDIATE=0 make pr",
    "make -C /root/.cursor-governance pr",
    "make pr WS=/home/user/Cursor-Governance",
    "make -j 4 pr",
    "/usr/bin/make pr",
]

NOT_MAKE_PR = ["make push", "make test", "make pr-check", "git push origin main", ""]


@pytest.mark.parametrize("command", MAKE_PR_FORMS)
def test_is_make_pr_accepts_real_invocations(command: str) -> None:
    assert gate.is_make_pr(command) is True


@pytest.mark.parametrize("command", NOT_MAKE_PR)
def test_is_make_pr_rejects_other_goals(command: str) -> None:
    """`make pr-check` runs the gate but never pushes, so it is not the publish path."""
    assert gate.is_make_pr(command) is False


class TestMakeGoalsAreExactTokens:
    """`make pr-check` is the local quality gate and never reaches GitHub.

    A regex for `make pr` matches `make pr-check` too — \\b closes on the hyphen
    — so the L4 remote gate denied the one command an agent is supposed to run
    before publishing. Goals are matched as exact tokens instead.
    """

    def test_pr_check_is_not_a_remote_mutation(self) -> None:
        assert gate.command_is_remote_mutation("make pr-check") is False
        assert gate.command_bypasses_publish_path("make pr-check") is None

    def test_pr_check_passes_the_gate_without_a_release_receipt(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
        monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
        monkeypatch.setattr(gate, "release_allows_remote", lambda root: (False, "L4 denied"))
        assert gate.evaluate("Bash", {"command": "make pr-check"}, root=tmp_path) is None

    @pytest.mark.parametrize(
        "command",
        ["make pr", "make push", "PR_REMEDIATE=0 make pr", "make -C /tmp/repo pr"],
    )
    def test_real_publish_goals_still_classify(self, command: str) -> None:
        assert gate.command_is_remote_mutation(command) is True

    def test_dash_c_publish_was_previously_missed(self) -> None:
        """`make -C <path> pr` never matched `\\bmake\\s+pr\\b` — a fail-open hole.

        The old regex needed `pr` right after `make`, so a publish run against
        another checkout skipped the L4 receipt check entirely.
        """
        assert gate.command_is_remote_mutation("make -C /tmp/repo pr") is True
        assert gate.is_make_pr("make -C /tmp/repo pr") is True

    def test_goal_lists_are_scanned_whole(self) -> None:
        """`make pr-check pr` runs both goals, so the publish must be seen."""
        assert gate.is_make_pr("make pr-check pr") is True
        assert gate.command_is_remote_mutation("make pr-check pr") is True
        assert gate.make_goals("make pr-check pr") == ("pr-check", "pr")

    @pytest.mark.parametrize(
        "command", ["make test", "make lint", "make improve", "make start", "make pr-check"]
    )
    def test_local_goals_are_never_remote(self, command: str) -> None:
        assert gate.command_is_remote_mutation(command) is False

    def test_non_make_segments_have_no_goals(self) -> None:
        assert gate.make_goals("git push origin main") == ()
        assert gate.make_goals("") == ()


def test_publish_matcher_is_linear_not_exponential() -> None:
    """Regression: CodeQL py/redos on PR #168.

    The matcher runs inside a PreToolUse gate on every shell command, so input
    that merely *looks* like flags must not be able to stall it. The original
    regex took ~9.8 s at n=18 and ~455 s at n=22 on this input; a linear scan
    stays in microseconds. The bound is loose enough not to flake on a busy
    runner but far below any exponential curve.
    """
    import time

    evil = "make" + " -! -!" * 22 + " X"
    start = time.perf_counter()
    assert gate.is_make_pr(evil) is False
    assert time.perf_counter() - start < 1.0


def test_heredoc_body_is_data_not_a_push() -> None:
    command = "cat <<'EOF'\ngit push origin main\nEOF"
    assert gate.command_bypasses_publish_path(command) is None


def test_non_git_publish_bypass_stays_denied(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """L4 authorization is not a licence to skip the checkers.

    `make push` reaches GitHub without running them and is not a git/gh
    executable, so the gate still denies it even when release is authorized.
    """
    monkeypatch.delenv(gate.PUBLISH_PATH_OVERRIDE_ENV, raising=False)
    monkeypatch.setattr(gate, "release_allows_remote", lambda root: (True, None))

    reason = gate.evaluate("Bash", {"command": "make push"}, root=tmp_path)
    assert reason is not None
    assert "make pr" in reason

    # ...while the sanctioned path is untouched by this rule.
    assert gate.evaluate("Bash", {"command": "PR_REMEDIATE=0 make pr"}, root=tmp_path) is None


def test_raw_git_push_is_reported_but_not_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Policy still names it; the gate no longer blocks it."""
    monkeypatch.delenv(gate.PUBLISH_PATH_OVERRIDE_ENV, raising=False)
    monkeypatch.setattr(gate, "release_allows_remote", lambda root: (False, "L4 denied"))

    assert gate.command_bypasses_publish_path("git push origin main") == "git push"
    assert gate.evaluate("Bash", {"command": "git push origin main"}, root=tmp_path) is None


def test_mcp_push_tools_denied_even_when_release_authorized(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(gate.PUBLISH_PATH_OVERRIDE_ENV, raising=False)
    monkeypatch.setattr(gate, "release_allows_remote", lambda root: (True, None))
    for tool in ("mcp__github__create_pull_request", "mcp__github__push_files"):
        reason = gate.evaluate(tool, {}, root=tmp_path)
        assert reason is not None, tool
        assert "make pr" in reason


REMEDIATOR_GIT_COMMANDS = [
    "git push origin HEAD",
    "git push -u origin HEAD",
    "git push origin HEAD | tail -8",
    "make precommit-repo && git push origin HEAD",
    "PR_BASE=origin/main make precommit-repo && git push",
    "cd /tmp/repo && make precommit-repo && git push origin HEAD",
    "gh pr edit 12 --body b",
    "git status && git fetch origin && git push origin HEAD",
]


@pytest.mark.parametrize("command", REMEDIATOR_GIT_COMMANDS)
def test_remediator_git_push_is_not_workflow_denied(
    command: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F-14 Allow + remediator velocity: git/gh publish is not a workflow deny.

    Bare ``git push``, a pipe, and ``make precommit-repo && git push`` must
    share one verdict. Classifiers still name the raw publish.
    """
    monkeypatch.delenv(gate.PUBLISH_PATH_OVERRIDE_ENV, raising=False)
    monkeypatch.setattr(gate, "release_allows_remote", lambda root: (False, "L4 denied"))
    assert gate.evaluate("Bash", {"command": command}, root=tmp_path) is None
    assert gate.publish_path_workflow_deny(command) is None


def test_piped_git_push_matches_bare_verdict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(gate.PUBLISH_PATH_OVERRIDE_ENV, raising=False)
    monkeypatch.setattr(gate, "release_allows_remote", lambda root: (False, "L4 denied"))
    bare = gate.evaluate("Bash", {"command": "git push origin HEAD"}, root=tmp_path)
    piped = gate.evaluate("Bash", {"command": "git push origin HEAD | tail -1"}, root=tmp_path)
    assert bare is None
    assert piped == bare


def test_cursor_shell_allows_remediator_git_push(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cursor beforeShellExecution is the live remediator deny surface."""
    monkeypatch.delenv(gate.PUBLISH_PATH_OVERRIDE_ENV, raising=False)
    monkeypatch.setattr(gate, "release_allows_remote", lambda root: (False, "L4 denied"))
    monkeypatch.setattr(gate, "workspace_from_event", lambda event: tmp_path)
    monkeypatch.setattr(gate, "effective_root", lambda command, root: root)
    monkeypatch.setattr(gate, "command_requires_human", lambda command, root=None: None)
    monkeypatch.setattr(
        gate, "command_violates_worktree_isolation", lambda command, root=None: None
    )

    class _Stdin:
        def read(self) -> str:
            return (
                '{"command": "PR_BASE=origin/main make precommit-repo '
                '&& git push origin HEAD"}'
            )

    class _Capture:
        def __init__(self) -> None:
            self.parts: list[str] = []

        def write(self, chunk: str) -> int:
            self.parts.append(chunk)
            return len(chunk)

        def flush(self) -> None:
            return None

    captured = _Capture()
    monkeypatch.setattr(sys, "stdin", _Stdin())
    monkeypatch.setattr(sys, "stdout", captured)
    assert gate.main_cursor_shell() == 0
    assert json.loads("".join(captured.parts))["permission"] == "allow"


def test_human_override_restores_prior_behaviour(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Breakglass is human/ops only, and hands control back to the L4 check.

    Exercised through `make push`: git/gh never reach the publish-path rule at
    all now, so the override's remaining subject is the non-git bypass forms.
    """
    monkeypatch.setenv(gate.PUBLISH_PATH_OVERRIDE_ENV, "incident-1234")
    monkeypatch.setattr(gate, "release_allows_remote", lambda root: (True, None))
    assert gate.evaluate("Bash", {"command": "make push"}, root=tmp_path) is None

    # Override does not bypass L4 itself — an unauthorized workspace still denies.
    monkeypatch.setattr(gate, "release_allows_remote", lambda root: (False, "L4 denied"))
    assert gate.evaluate("Bash", {"command": "make push"}, root=tmp_path) == "L4 denied"

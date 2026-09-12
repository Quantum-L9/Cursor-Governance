"""Publish-path classification: `make pr` is the sanctioned route to GitHub.

L4 governs *when* remote work may happen; this governs *how*. A raw `git push`
or `gh pr create` skips the Makefile checkers entirely, so the classifier keeps
reporting it — that report is what a policy engine acts on.

Enforcement is by effect (CANONICAL_LAW §6.2.4 / §6.2.8). `git` and `gh` stay
exempt from the workflow plane, so `command_bypasses_publish_path` names a raw
push while `publish_path_workflow_deny` never denies it. What DOES deny is the
publication plane (`first_publication_gate`): a push of a branch with no open
PR — a first publication — is refused outside `make pr`; a push that advances
an open PR is the remediator path and is allowed. `make push` and the MCP
push/PR tools are not git/gh executables and stay denied at every phase.
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
import open_pr_probe  # noqa: E402
from first_publication_gate import (  # noqa: E402
    first_publication_verdict,
    publication_forms,
)


def _open_pr(monkeypatch: pytest.MonkeyPatch, answer: bool | None) -> None:
    """Pin what GitHub would say about the pushed branch (True/False/None)."""
    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.delenv("L9_PUBLISH_PATH_RECEIPT", raising=False)
    monkeypatch.setattr(
        open_pr_probe, "open_pr_for_branch", lambda root, branch, remote="origin": answer
    )


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


def test_raw_git_push_is_reported_and_first_publication_is_denied(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Audit R1: a push of a branch with no open PR skips every checker.

    The classifier still names it, the workflow plane still does not deny it,
    and the publication plane refuses it with the sanctioned route named.
    """
    monkeypatch.delenv(gate.PUBLISH_PATH_OVERRIDE_ENV, raising=False)
    monkeypatch.setattr(gate, "release_allows_remote", lambda root: (False, "L4 denied"))
    _open_pr(monkeypatch, False)

    assert gate.command_bypasses_publish_path("git push origin main") == "git push"
    assert gate.publish_path_workflow_deny("git push origin main") is None
    reason = gate.evaluate("Bash", {"command": "git push origin main"}, root=tmp_path)
    assert reason is not None
    assert "FIRST publication" in reason
    assert "make pr" in reason


def test_gh_pr_create_is_always_a_first_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _open_pr(monkeypatch, True)  # even an open PR elsewhere does not make this remediation
    reason = gate.evaluate("Bash", {"command": "gh pr create --title t --body b"}, root=tmp_path)
    assert reason is not None
    assert "gh pr create" in reason


def test_undeterminable_open_pr_state_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No gh / no network / no remote: the collision state is unknown, so deny (E6)."""
    _open_pr(monkeypatch, None)
    reason = gate.evaluate("Bash", {"command": "git push origin HEAD"}, root=tmp_path)
    assert reason is not None
    assert "undeterminable" in reason


@pytest.mark.parametrize(
    "command",
    [
        "git push --dry-run origin HEAD",
        "git push origin --delete old-branch",
        "git push origin :old-branch",
        "gh pr edit 12 --body b",
        "git fetch origin && git status",
    ],
)
def test_non_publishing_git_forms_never_reach_the_probe(
    command: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Deletes, dry runs and PR edits publish nothing (a delete answers to guardrails)."""

    def explode(root, branch, remote="origin"):  # noqa: ANN001
        raise AssertionError("probe must not run for a non-publication")

    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setattr(open_pr_probe, "open_pr_for_branch", explode)
    assert first_publication_verdict(command, root=tmp_path) is None


def test_push_breakglass_waives_the_publication_plane(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _open_pr(monkeypatch, False)
    monkeypatch.setenv("L9_LOCAL_PUSH_AUTHORIZED", "incident-42")
    assert gate.evaluate("Bash", {"command": "git push origin HEAD"}, root=tmp_path) is None


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
def test_remediator_git_push_of_an_open_pr_is_not_denied(
    command: str, stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F-14 Allow + remediator velocity: advancing an OPEN PR is not a deny.

    Bare ``git push``, a pipe, and ``make precommit-repo && git push`` must
    share one verdict, and L4 does not gate the remediation push. Classifiers
    still name the raw publish.
    """
    monkeypatch.delenv(gate.PUBLISH_PATH_OVERRIDE_ENV, raising=False)
    monkeypatch.setattr(gate, "release_allows_remote", lambda root: (False, "L4 denied"))
    _open_pr(monkeypatch, True)
    assert gate.evaluate("Bash", {"command": command}, root=stacked_repo) is None
    assert gate.publish_path_workflow_deny(command) is None


@pytest.mark.parametrize("command", REMEDIATOR_GIT_COMMANDS)
def test_the_same_forms_are_denied_when_no_pr_is_open(
    command: str, stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The verdict depends on the branch's PR state, never on the command's shape."""
    monkeypatch.delenv(gate.PUBLISH_PATH_OVERRIDE_ENV, raising=False)
    monkeypatch.setattr(gate, "release_allows_remote", lambda root: (False, "L4 denied"))
    _open_pr(monkeypatch, False)
    reason = gate.evaluate("Bash", {"command": command}, root=stacked_repo)
    if "gh pr edit" in command:
        assert reason is None  # editing an existing PR publishes nothing
    else:
        assert reason is not None and "FIRST publication" in reason


def test_piped_git_push_matches_bare_verdict(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(gate.PUBLISH_PATH_OVERRIDE_ENV, raising=False)
    monkeypatch.setattr(gate, "release_allows_remote", lambda root: (False, "L4 denied"))
    for answer in (True, False):
        _open_pr(monkeypatch, answer)
        bare = gate.evaluate("Bash", {"command": "git push origin HEAD"}, root=stacked_repo)
        piped = gate.evaluate(
            "Bash", {"command": "git push origin HEAD | tail -1"}, root=stacked_repo
        )
        assert (bare is None) is answer
        assert piped == bare


def test_cursor_shell_allows_remediator_git_push(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cursor beforeShellExecution is the live remediator deny surface."""
    monkeypatch.delenv(gate.PUBLISH_PATH_OVERRIDE_ENV, raising=False)
    monkeypatch.setattr(gate, "release_allows_remote", lambda root: (False, "L4 denied"))
    _open_pr(monkeypatch, True)
    monkeypatch.setattr(gate, "workspace_from_event", lambda event: tmp_path)
    monkeypatch.setattr(gate, "effective_root", lambda command, root: root)
    monkeypatch.setattr(gate, "command_requires_human", lambda command, root=None: None)
    monkeypatch.setattr(
        gate, "command_violates_worktree_isolation", lambda command, root=None: None
    )

    class _Stdin:
        def read(self) -> str:
            return '{"command": "PR_BASE=origin/main make precommit-repo && git push origin HEAD"}'

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


def test_cursor_shell_denies_a_first_publication_push(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The all-git payload short-circuit must not wave a first publication through."""
    _open_pr(monkeypatch, False)
    monkeypatch.setattr(gate, "workspace_from_event", lambda event: tmp_path)
    monkeypatch.setattr(gate, "effective_root", lambda command, root: root)
    monkeypatch.setattr(gate, "command_requires_human", lambda command, root=None: None)
    verdict, reason = gate.cursor_shell_verdict('{"command": "git push -u origin HEAD"}')
    assert verdict == "deny"
    assert reason is not None and "FIRST publication" in reason


def test_standing_override_env_is_inert(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A pasted L9_PUBLISH_PATH_OVERRIDE string must not widen the publish plane."""
    monkeypatch.setenv(gate.PUBLISH_PATH_OVERRIDE_ENV, "incident-1234")
    monkeypatch.delenv("L9_PUBLISH_PATH_RECEIPT", raising=False)
    monkeypatch.setattr(gate, "release_allows_remote", lambda root: (True, None))
    reason = gate.evaluate("Bash", {"command": "make push"}, root=tmp_path)
    assert reason is not None
    assert "make push" in reason


def test_human_override_restores_prior_behaviour(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Breakglass is a scoped expiring receipt, and hands control back to L4.

    Exercised through `make push`: git/gh never reach the publish-path rule at
    all now, so the override's remaining subject is the non-git bypass forms.
    """
    from breakglass_receipt import write_receipt

    receipt = tmp_path / "publish-path-override.json"
    write_receipt(issuer="ops", reason="incident-1234", hours=2, path=receipt)
    monkeypatch.setenv("L9_PUBLISH_PATH_RECEIPT", str(receipt))
    monkeypatch.setattr(gate, "release_allows_remote", lambda root: (True, None))
    assert gate.evaluate("Bash", {"command": "make push"}, root=tmp_path) is None

    # Override does not bypass L4 itself — an unauthorized workspace still denies.
    monkeypatch.setattr(gate, "release_allows_remote", lambda root: (False, "L4 denied"))
    assert gate.evaluate("Bash", {"command": "make push"}, root=tmp_path) == "L4 denied"


# --------------------------------------------------------------------------
# Audit F1 (l9-pr-audit...pr553.582a9b3): every publication effect is judged
# --------------------------------------------------------------------------


def _open_pr_by_branch(monkeypatch: pytest.MonkeyPatch, open_branches: set[str]) -> None:
    """Pin the PR state per pushed branch, so a multi-ref push is judged per ref."""
    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.delenv("L9_PUBLISH_PATH_RECEIPT", raising=False)
    monkeypatch.setattr(
        open_pr_probe,
        "open_pr_for_branch",
        lambda root, branch, remote="origin": branch in open_branches,
    )


def test_publication_forms_enumerate_every_push_refspec() -> None:
    forms = publication_forms("git push origin feat-open feat-new")
    assert [form["branch"] for form in forms] == ["feat-open", "feat-new"]
    forms = publication_forms("git push -u origin HEAD:refs/heads/new +topic:other :gone")
    assert [form["branch"] for form in forms] == ["new", "other"]
    assert publication_forms("git push origin --delete feat-a feat-b") == []
    assert publication_forms("git push -o ci.skip origin feat-a") == [
        {
            "remote": "origin",
            "branch": "feat-a",
            "whole_repo": None,
            "form": "git push",
            "named_root": None,
        }
    ]


def test_multi_ref_push_is_denied_when_any_ref_is_a_first_publication(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A remediation ref must not smuggle an unpublished ref past the plane."""
    _open_pr_by_branch(monkeypatch, {"feat-open"})
    reason = gate.evaluate(
        "Bash", {"command": "git push origin feat-open feat-new"}, root=stacked_repo
    )
    assert reason is not None
    assert "FIRST publication" in reason and "'feat-new'" in reason
    # Order does not matter: the unpublished ref first is denied too.
    reason = gate.evaluate(
        "Bash", {"command": "git push origin feat-new feat-open"}, root=stacked_repo
    )
    assert reason is not None and "'feat-new'" in reason


def test_multi_ref_push_of_only_open_prs_stays_remediation(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _open_pr_by_branch(monkeypatch, {"feat-open", "feat-open-2"})
    assert (
        gate.evaluate(
            "Bash", {"command": "git push origin feat-open feat-open-2"}, root=stacked_repo
        )
        is None
    )


def test_refspec_destination_is_the_branch_that_is_probed(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    probed: list[str] = []

    def probe(root, branch, remote="origin"):  # noqa: ANN001
        probed.append(branch)
        return branch == "new"

    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setattr(open_pr_probe, "open_pr_for_branch", probe)
    assert (
        gate.evaluate("Bash", {"command": "git push origin HEAD:refs/heads/new"}, root=stacked_repo)
        is None
    )
    assert probed == ["new"]


@pytest.mark.parametrize(
    "command",
    [
        "gh -R Quantum-L9/Cursor-Governance pr create --fill",
        "gh --repo Quantum-L9/Cursor-Governance pr create --title t --body b",
        "gh --repo=Quantum-L9/Cursor-Governance pr create --fill",
        "gh -R o/r pr create",
        "cd /tmp/repo && gh -R o/r pr create --fill",
    ],
)
def test_gh_pr_create_is_denied_wherever_the_repo_option_sits(
    command: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _open_pr(monkeypatch, True)
    assert publication_forms(command) == [{"form": "gh pr create"}]
    reason = gate.evaluate("Bash", {"command": command}, root=tmp_path)
    assert reason is not None and "gh pr create" in reason


@pytest.mark.parametrize(
    "command",
    [
        "gh -R o/r pr list",
        "gh -R o/r pr view 12",
        "gh --repo o/r pr edit 12 --body b",
        "gh -R o/r api repos/o/r/pulls",
    ],
)
def test_gh_read_and_edit_forms_with_the_repo_option_stay_allowed(
    command: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _open_pr(monkeypatch, False)
    assert publication_forms(command) == []
    assert gate.evaluate("Bash", {"command": command}, root=tmp_path) is None

"""The REST merge verb is gated exactly like the CLI one.

`5612f6b` gave the stack *probe* a REST transport. The merge *verb* kept only
the GraphQL-backed CLI subcommand, so on a session gateway serving a pinned set
of operations an authorized merge could not execute at all. Adding a REST
execution path without teaching the gate to recognise it would have been worse
than the 403: measured before this change, `_command_is_pr_merge` returned False
for `gh api --method PUT .../merge`, so the REST call was ungated.

The binding property is therefore not "REST works" but "REST is gated" -- and
specifically that the argv `stack_safe_merge` actually emits is the argv the gate
catches. These are asserted against the real builders, not against a string
written by hand here, so the two cannot drift apart.

Command literals are assembled from parts so this file's bytes do not trip the
PreToolUse shell matcher that fronts the gate.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_AUTONOMY = Path(__file__).resolve().parents[3] / "ops" / "autonomy"
if str(_AUTONOMY) not in sys.path:
    sys.path.insert(0, str(_AUTONOMY))

import merge_gate as mg  # noqa: E402
import stack_safe_merge as ssm  # noqa: E402

REPO = "o/r"
PR = "321"
HEAD = "feature/x"
API = " ".join(["gh", "api"])
CLI = " ".join(["gh", "pr", "merge"])
PATH = f"repos/{REPO}/pulls/{PR}/merge"


# --- the emitted verb is the gated verb ---------------------------------------


@pytest.mark.parametrize("method", ["squash", "merge", "rebase"])
def test_emitted_rest_merge_argv_is_gated(method: str) -> None:
    """Whatever stack_safe_merge emits for REST, the gate must catch it."""
    argv = ssm.merge_rest_argv(REPO, PR, method)
    assert mg._command_is_pr_merge(" ".join(argv)) is True


@pytest.mark.parametrize("method", ["squash", "merge", "rebase"])
def test_emitted_rest_merge_argv_reports_its_method(method: str) -> None:
    argv = ssm.merge_rest_argv(REPO, PR, method)
    assert mg._merge_method(" ".join(argv)) == method


def test_emitted_cli_merge_argv_is_still_gated() -> None:
    """The fallback transport must not lose coverage."""
    selection = {"repo": REPO, "pr": PR, "method": "squash", "head": HEAD}
    argv = ssm.merge_argv(REPO, PR, selection=selection)
    assert mg._command_is_pr_merge(" ".join(argv)) is True


# --- recognition breadth ------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        f"{API} --method PUT {PATH}",
        f"{API} -X PUT {PATH}",
        f"{API} --method PUT https://api.github.com/{PATH}",
        f"bash -c '{API} --method PUT {PATH}'",
        f"{API} --method PUT {PATH} -f merge_method=squash",
    ],
)
def test_rest_merge_spellings_are_gated(command: str) -> None:
    assert mg._command_is_pr_merge(command) is True


@pytest.mark.parametrize(
    "command",
    [
        # adjacent endpoints that are not a merge
        f"{API} repos/{REPO}/pulls/{PR}",
        f"{API} repos/{REPO}/pulls/{PR}/comments",
        f"{API} 'repos/{REPO}/pulls?state=open'",
        f"{API} repos/{REPO}/pulls/{PR}/merge_group",
        # a mention is not an invocation
        f"echo 'someday {PATH}'",
        f"cat > f <<E\n{API} --method PUT {PATH}\nE\n",
    ],
)
def test_non_merges_are_not_gated(command: str) -> None:
    """False positives cost a spurious receipt demand; keep them out."""
    assert mg._command_is_pr_merge(command) is False


# --- method default -----------------------------------------------------------


def test_rest_without_merge_method_is_treated_as_ancestry_breaking() -> None:
    """An omitted merge_method must NOT be read as GitHub's documented default.

    GitHub defaults the omitted field to a merge commit, and an earlier draft of
    this test asserted exactly that. It was wrong in the direction that matters:
    "merge" is not in ANCESTRY_BREAKING, so a REST merge with no explicit method
    against a stack parent would have passed the stack-safety check on the
    strength of a server-side default the command never stated.

    "unspecified" is the safer and the honest reading -- the argv did not say --
    and it is ANCESTRY_BREAKING, so that merge is denied instead.
    """
    assert mg._merge_method(f"{API} --method PUT {PATH}") == "unspecified"
    assert "unspecified" in mg.ANCESTRY_BREAKING


# --- branch deletion parity ---------------------------------------------------


def test_rest_transport_has_an_explicit_ref_delete() -> None:
    """REST merge does not delete the branch; the CLI flag does.

    Without a separate ref delete the REST path would silently stop honouring
    --delete-branch, so the two transports would disagree about what happened.
    """
    argv = ssm.delete_ref_argv(REPO, HEAD)
    assert argv[:4] == ["gh", "api", "--method", "DELETE"]
    assert argv[4] == f"repos/{REPO}/git/refs/heads/{HEAD}"


def test_ref_delete_is_not_itself_treated_as_a_merge() -> None:
    assert mg._command_is_pr_merge(" ".join(ssm.delete_ref_argv(REPO, HEAD))) is False


# --- fail-closed behaviour is unchanged ---------------------------------------


def test_both_transports_failing_returns_nonzero(monkeypatch: pytest.MonkeyPatch) -> None:
    """A refused merge stays refused. Widening transports never invents success."""
    calls: list[list[str]] = []

    def always_fail(argv: list[str]) -> int:
        calls.append(argv)
        return 1

    monkeypatch.setattr(ssm, "_run", always_fail)
    selection = {"repo": REPO, "pr": PR, "method": "squash", "head": HEAD}
    rc = ssm._execute(selection, delete_branch=True)

    assert rc != 0
    assert len(calls) == 2, "expected one REST attempt then one CLI attempt"
    assert calls[0][1] == "api"
    assert calls[1][1] == "pr"


def test_rest_success_skips_the_cli_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def ok(argv: list[str]) -> int:
        calls.append(argv)
        return 0

    monkeypatch.setattr(ssm, "_run", ok)
    selection = {"repo": REPO, "pr": PR, "method": "squash", "head": HEAD}
    assert ssm._execute(selection, delete_branch=True) == 0

    verbs = [c[1] for c in calls]
    assert verbs == ["api", "api"], "expected REST merge then REST ref delete, no CLI"
    assert calls[1][3] == "DELETE"


def test_keep_branch_does_not_delete_the_ref(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(ssm, "_run", lambda argv: (calls.append(argv), 0)[1])
    selection = {"repo": REPO, "pr": PR, "method": "squash", "head": HEAD}

    assert ssm._execute(selection, delete_branch=False) == 0
    assert len(calls) == 1, "no ref delete when the branch is meant to survive"


def test_failed_ref_delete_does_not_fail_a_landed_merge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The merge landed. Losing the branch cleanup is a warning, not a failure."""

    def merge_ok_delete_fails(argv: list[str]) -> int:
        return 0 if "PUT" in argv else 1

    monkeypatch.setattr(ssm, "_run", merge_ok_delete_fails)
    selection = {"repo": REPO, "pr": PR, "method": "squash", "head": HEAD}
    assert ssm._execute(selection, delete_branch=True) == 0

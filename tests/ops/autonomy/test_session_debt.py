"""Tests for ops/autonomy/session_debt.py.

The gate exists because doctrine did not hold three operator rules: commit
implies push, a known bug is work, and a pre-existing error is in scope once
identified. Each is reduced to a debt item the Stop hook can fail closed on.

The hard requirement is not "detects unpushed work" — it is "detects unpushed
work AND can be cleared by pushing". A gate that fires on an already-published
branch is unsatisfiable, and an unsatisfiable gate trains people to bypass
gates. The single-branch-refspec case below is that exact trap: it is how every
cloud clone is configured, and a detector trusting local remote-tracking refs
reports a pushed branch as unpushed forever.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "autonomy"))

import session_debt  # noqa: E402


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def make_origin(path: Path) -> Path:
    subprocess.run(
        ["git", "init", "-q", "--bare", "-b", "main", str(path)], check=True, capture_output=True
    )
    return path


def make_clone(origin: Path, path: Path, *, single_branch: bool = False) -> Path:
    subprocess.run(["git", "clone", "-q", str(origin), str(path)], check=True, capture_output=True)
    git(path, "config", "user.email", "t@example.com")
    git(path, "config", "user.name", "t")
    (path / "f.txt").write_text("base", encoding="utf-8")
    git(path, "add", "-A")
    git(path, "commit", "-q", "-m", "base")
    git(path, "push", "-q", "-u", "origin", "main")
    if single_branch:
        # Exactly how a cloud clone is configured: origin/<feature> never exists.
        git(
            path,
            "config",
            "--replace-all",
            "remote.origin.fetch",
            "+refs/heads/main:refs/remotes/origin/main",
        )
    return path


@pytest.fixture
def origin(tmp_path: Path) -> Path:
    return make_origin(tmp_path / "origin.git")


@pytest.fixture
def clone(origin: Path, tmp_path: Path) -> Path:
    return make_clone(origin, tmp_path / "work")


def commit_on_branch(root: Path, branch: str) -> None:
    git(root, "checkout", "-q", "-b", branch)
    (root / "feature.txt").write_text("work", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "feature work")


# --- Rule 1: commit implies push --------------------------------------------


def test_unpushed_branch_is_debt(clone: Path) -> None:
    commit_on_branch(clone, "feat/x")
    debt = session_debt.publish_debt(clone)
    assert debt is not None
    assert debt["branch"] == "feat/x"
    assert "not on origin" in debt["detail"]


def test_pushing_clears_the_debt(clone: Path) -> None:
    commit_on_branch(clone, "feat/x")
    assert session_debt.publish_debt(clone) is not None
    git(clone, "push", "-q", "-u", "origin", "feat/x")
    assert session_debt.publish_debt(clone) is None


def test_pushed_branch_with_single_branch_refspec_is_not_debt(origin: Path, tmp_path: Path) -> None:
    """The unsatisfiable-gate trap, and the reason this is not a one-liner.

    With a main-only refspec no refs/remotes/origin/feat/x is ever created, so
    local refs cannot prove publication however many times the branch is
    pushed. The remote must be consulted or the gate can never be cleared.
    """
    work = make_clone(origin, tmp_path / "single", single_branch=True)
    commit_on_branch(work, "feat/x")
    git(work, "push", "-q", "origin", "feat/x")
    assert git(work, "for-each-ref", "--format=%(refname)", "refs/remotes/origin/feat") == ""
    assert session_debt.publish_debt(work) is None


def test_new_commit_after_a_push_is_debt_again(clone: Path) -> None:
    commit_on_branch(clone, "feat/x")
    git(clone, "push", "-q", "-u", "origin", "feat/x")
    (clone / "more.txt").write_text("more", encoding="utf-8")
    git(clone, "add", "-A")
    git(clone, "commit", "-q", "-m", "more work")
    debt = session_debt.publish_debt(clone)
    assert debt is not None
    assert debt["remote_sha"]


def test_checkout_behind_the_remote_tip_is_not_debt(origin: Path, tmp_path: Path) -> None:
    """A second worktree left on an older commit has no unpushed work.

    Debt is unpushed *work*, not a stale checkout. Reporting it would also be
    unclearable: pushing does nothing when the remote is already ahead.
    """
    first = make_clone(origin, tmp_path / "first")
    commit_on_branch(first, "feat/x")
    git(first, "push", "-q", "origin", "feat/x")
    behind = git(first, "rev-parse", "HEAD")

    (first / "later.txt").write_text("later", encoding="utf-8")
    git(first, "add", "-A")
    git(first, "commit", "-q", "-m", "later work")
    git(first, "push", "-q", "origin", "feat/x")

    second = tmp_path / "second"
    subprocess.run(
        ["git", "clone", "-q", str(origin), str(second)], check=True, capture_output=True
    )
    git(second, "fetch", "-q", "origin", "feat/x")
    git(second, "checkout", "-q", "-b", "feat/x", behind)
    assert git(second, "rev-parse", "HEAD") == behind
    assert session_debt.publish_debt(second) is None


def test_merged_and_deleted_branch_is_not_debt(clone: Path) -> None:
    """CI-036's own case, reproduced inside the checker.

    A squash merge gives the branch's commits no ancestry to main by design, and
    the merge deletes the branch, so absence upstream is indistinguishable from
    never-pushed by reachability alone. Reporting it would attach the remedy
    "push it" to a branch the merge deleted.
    """
    commit_on_branch(clone, "feat/x")
    git(clone, "push", "-q", "-u", "origin", "feat/x")
    # Squash-merge into main and delete the branch, exactly as GitHub does.
    git(clone, "checkout", "-q", "main")
    git(clone, "merge", "-q", "--squash", "feat/x")
    git(clone, "commit", "-q", "-m", "feat: squashed (#1)")
    git(clone, "push", "-q", "origin", "main")
    git(clone, "push", "-q", "origin", "--delete", "feat/x")
    git(clone, "checkout", "-q", "feat/x")

    assert git(clone, "ls-remote", "--heads", "origin", "feat/x") == ""
    head = git(clone, "rev-parse", "HEAD")
    unreachable = subprocess.run(
        ["git", "-C", str(clone), "merge-base", "--is-ancestor", head, "origin/main"],
        capture_output=True,
        check=False,
    )
    assert unreachable.returncode != 0, "squash merge must leave HEAD unreachable from main"
    assert session_debt.publish_debt(clone) is None


def test_never_pushed_branch_is_still_debt_when_absent_upstream(clone: Path) -> None:
    """The direction that matters: absence upstream must still catch real debt.

    Both cases look identical to ls-remote. Only upstream config separates them,
    so this pins that a branch with none is not excused by the check above.
    """
    commit_on_branch(clone, "feat/never")
    # `config --get` exits 1 on a missing key, so this cannot use the checked helper.
    upstream = subprocess.run(
        ["git", "-C", str(clone), "config", "--get", "branch.feat/never.remote"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert upstream.returncode != 0 and upstream.stdout.strip() == ""
    debt = session_debt.publish_debt(clone)
    assert debt is not None
    assert debt["branch"] == "feat/never"


def test_feature_branch_merely_ahead_of_main_is_not_debt(clone: Path) -> None:
    """Being ahead of origin/main is what a feature branch IS, not debt."""
    commit_on_branch(clone, "feat/x")
    git(clone, "push", "-q", "origin", "feat/x")
    assert session_debt.publish_debt(clone) is None


def test_main_is_never_publish_debt(clone: Path) -> None:
    (clone / "g.txt").write_text("x", encoding="utf-8")
    git(clone, "add", "-A")
    git(clone, "commit", "-q", "-m", "on main")
    assert session_debt.publish_debt(clone) is None


def test_unreachable_remote_keeps_debt_but_marks_it_unverified(clone: Path) -> None:
    """Fail closed on the decision, honest about the evidence."""
    commit_on_branch(clone, "feat/x")
    git(clone, "remote", "set-url", "origin", str(clone / "does-not-exist"))
    debt = session_debt.publish_debt(clone)
    assert debt is not None
    assert debt["verified"] is False
    assert "cannot reach origin" in debt["detail"]


# --- Rules 2 and 3: a known bug is work, whoever wrote it --------------------


def test_recorded_finding_is_open_debt(clone: Path) -> None:
    ledger = session_debt.load_ledger(clone)
    ledger["findings"].append({"id": "F-1", "state": "open", "detail": "pre-existing drift"})
    session_debt.save_ledger(clone, ledger)
    report = session_debt.collect([clone])
    assert [f["id"] for f in report["open_findings"]] == ["F-1"]
    assert report["clean"] is False


def test_closing_a_finding_clears_it(clone: Path) -> None:
    ledger = session_debt.load_ledger(clone)
    ledger["findings"].append({"id": "F-1", "state": "closed", "detail": "fixed"})
    session_debt.save_ledger(clone, ledger)
    assert session_debt.collect([clone])["open_findings"] == []


def test_deferring_does_not_discharge_it(clone: Path) -> None:
    """Deferral is weaker than closing on purpose: the next session inherits it.

    This is what stops "pre-existing, not mine" from being an exit (rule 3).
    """
    ledger = session_debt.load_ledger(clone)
    ledger["findings"].append({"id": "F-1", "state": "deferred", "reason": "needs owner"})
    session_debt.save_ledger(clone, ledger)
    report = session_debt.collect([clone])
    assert [f["id"] for f in report["open_findings"]] == ["F-1"]
    assert report["clean"] is False


def test_corrupt_ledger_is_not_an_empty_ledger(clone: Path) -> None:
    """An unreadable ledger must not silently discharge everything it held."""
    path = clone / ".l9" / "autonomy" / session_debt.LEDGER_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json", encoding="utf-8")
    report = session_debt.collect([clone])
    assert report["clean"] is False
    assert str(clone) in report["unreadable_ledgers"]


# --- Gate behaviour ----------------------------------------------------------


def _run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REPO / "ops" / "autonomy" / "session_debt.py"), *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        env={"PATH": "/usr/bin:/bin", "HOME": str(root), "L9_SESSION_DEBT_ROOTS": str(root)},
    )


def test_check_exits_two_on_open_debt(clone: Path) -> None:
    commit_on_branch(clone, "feat/x")
    result = _run(clone, "check")
    assert result.returncode == 2
    assert "abandoned" in result.stderr
    assert "feat/x" in result.stderr


def test_check_exits_zero_when_clean(clone: Path) -> None:
    commit_on_branch(clone, "feat/x")
    git(clone, "push", "-q", "origin", "feat/x")
    assert _run(clone, "check").returncode == 0


def test_record_then_close_round_trip(clone: Path) -> None:
    assert _run(clone, "record", "F-9", "--detail", "a real bug").returncode == 0
    assert _run(clone, "check").returncode == 2
    assert _run(clone, "close", "F-9", "--evidence", "fixed in abc123").returncode == 0
    payload = json.loads((clone / ".l9" / "autonomy" / session_debt.LEDGER_NAME).read_text())
    assert payload["findings"][0]["state"] == "closed"
    assert payload["findings"][0]["evidence"] == "fixed in abc123"


def test_status_never_fails_the_caller(clone: Path) -> None:
    commit_on_branch(clone, "feat/x")
    result = _run(clone, "status")
    assert result.returncode == 0
    assert "UNPUSHED" in result.stdout

"""Tests for ops/scripts/repo_hygiene.py.

The invariant under test is that nothing is deleted without positive evidence
that its content survives elsewhere, and that squash merges -- which break
ancestry -- are still recognised as landed.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "scripts"))

import repo_hygiene  # noqa: E402


def git(root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
    )
    return proc.stdout.strip()


def commit(root: Path, name: str, body: str = "x") -> None:
    (root / name).parent.mkdir(parents=True, exist_ok=True)
    (root / name).write_text(body, encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-m", f"add {name}")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A work repo with an `origin` remote whose main branch we control."""
    upstream = tmp_path / "upstream.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(upstream)], check=True)

    root = tmp_path / "work"
    subprocess.run(["git", "init", "-b", "main", str(root)], check=True)
    git(root, "config", "user.email", "t@example.com")
    git(root, "config", "user.name", "t")
    git(root, "remote", "add", "origin", str(upstream))
    commit(root, "base.txt")
    git(root, "push", "-u", "origin", "main")
    return root


def report_for(root: Path, **kwargs) -> repo_hygiene.Report:
    """Build a report without consulting GitHub."""
    g = repo_hygiene.Git(root)
    kwargs.setdefault("max_stash_age", repo_hygiene.DEFAULT_STASH_AGE_HOURS)
    return repo_hygiene.build_report(g, **kwargs)


def finding(report: repo_hygiene.Report, name: str) -> repo_hygiene.BranchFinding:
    return next(b for b in report.branches if b.name == name)


def test_squash_merged_branch_is_recognised_as_landed(repo: Path) -> None:
    """Ancestry says unmerged; content says landed. Content must win."""
    git(repo, "checkout", "-b", "feat/thing")
    commit(repo, "thing.txt", "hello")
    commit(repo, "thing2.txt", "world")
    git(repo, "checkout", "main")
    git(repo, "merge", "--squash", "feat/thing")
    git(repo, "commit", "-m", "squashed feat/thing")
    git(repo, "push", "origin", "main")

    assert git(repo, "branch", "--merged", "main").find("feat/thing") == -1
    result = finding(report_for(repo), "feat/thing")
    assert result.status == "absorbed"
    assert result.action == "delete"


def test_branch_with_unlanded_commits_is_kept(repo: Path) -> None:
    git(repo, "checkout", "-b", "feat/unlanded")
    commit(repo, "unlanded.txt", "not in main")
    git(repo, "checkout", "main")

    result = finding(report_for(repo), "feat/unlanded")
    assert result.status == "unmerged_no_pr"
    assert result.action == "keep"


def test_reused_branch_after_merge_is_kept(repo: Path) -> None:
    """Branch name reused after its PR merged: later commits must not be dropped."""
    git(repo, "checkout", "-b", "feat/reused")
    commit(repo, "landed.txt", "in main")
    git(repo, "checkout", "main")
    git(repo, "merge", "--squash", "feat/reused")
    git(repo, "commit", "-m", "squashed")
    git(repo, "push", "origin", "main")
    git(repo, "checkout", "feat/reused")
    commit(repo, "later.txt", "written after the merge")
    git(repo, "checkout", "main")

    g = repo_hygiene.Git(repo)
    prs = {"feat/reused": {"number": 7, "state": "MERGED"}}
    result = repo_hygiene.classify_branch(g, "feat/reused", prs, {})
    assert result.status == "reused_after_merge"
    assert result.action == "keep"


def test_closed_pr_with_unique_commits_is_flagged(repo: Path) -> None:
    git(repo, "checkout", "-b", "feat/closed")
    commit(repo, "orphan.txt", "never landed")
    git(repo, "checkout", "main")

    g = repo_hygiene.Git(repo)
    prs = {"feat/closed": {"number": 200, "state": "CLOSED"}}
    result = repo_hygiene.classify_branch(g, "feat/closed", prs, {})
    assert result.status == "closed_unlanded"
    assert result.action == "keep"


def test_main_is_never_deleted(repo: Path) -> None:
    assert finding(report_for(repo), "main").status == "protected"


def test_apply_preserves_before_deleting(repo: Path) -> None:
    git(repo, "checkout", "-b", "feat/gone")
    commit(repo, "gone.txt", "content")
    git(repo, "checkout", "main")
    git(repo, "merge", "--squash", "feat/gone")
    git(repo, "commit", "-m", "squashed")
    git(repo, "push", "origin", "main")
    tip = git(repo, "rev-parse", "feat/gone")

    g = repo_hygiene.Git(repo)
    report = report_for(repo)
    repo_hygiene.apply_report(g, report)

    assert "feat/gone" not in git(repo, "branch", "--list")
    assert report.preserved_refs, "a preserve ref must exist before any delete"
    preserved = [git(repo, "rev-parse", ref) for ref in report.preserved_refs]
    assert tip in preserved, "the deleted tip must still be reachable"


def test_dirty_worktree_is_never_removed(repo: Path, tmp_path: Path) -> None:
    git(repo, "checkout", "-b", "feat/wt")
    commit(repo, "wt.txt", "content")
    git(repo, "checkout", "main")
    git(repo, "merge", "--squash", "feat/wt")
    git(repo, "commit", "-m", "squashed")
    git(repo, "push", "origin", "main")

    wt = tmp_path / "wt"
    git(repo, "worktree", "add", str(wt), "feat/wt")
    (wt / "uncommitted.txt").write_text("precious", encoding="utf-8")

    report = report_for(repo)
    entry = next(w for w in report.worktrees if Path(w.path) == wt)
    assert entry.status == "dirty"
    assert entry.action == "keep"
    assert finding(report, "feat/wt").action == "blocked-by-worktree"

    repo_hygiene.apply_report(repo_hygiene.Git(repo), report)
    assert (wt / "uncommitted.txt").read_text(encoding="utf-8") == "precious"
    assert "feat/wt" in git(repo, "branch", "--list")


def test_untracked_files_are_reported_never_deleted(repo: Path) -> None:
    (repo / "scratch.txt").write_text("keep me", encoding="utf-8")
    report = report_for(repo)
    assert any("scratch.txt" in entry for entry in report.untracked)

    repo_hygiene.apply_report(repo_hygiene.Git(repo), report)
    assert (repo / "scratch.txt").read_text(encoding="utf-8") == "keep me"


def test_stash_is_preserved_before_drop(repo: Path) -> None:
    (repo / "base.txt").write_text("modified", encoding="utf-8")
    git(repo, "stash", "push", "-m", "work in progress")
    assert git(repo, "stash", "list")

    g = repo_hygiene.Git(repo)
    report = report_for(repo, max_stash_age=0.0)
    assert report.stashes[0].action == "preserve+drop"
    tip = report.stashes[0].tip

    repo_hygiene.apply_report(g, report)
    assert git(repo, "stash", "list") == ""
    preserved = [git(repo, "rev-parse", ref) for ref in report.preserved_refs]
    assert tip in preserved
    assert "modified" in git(repo, "show", f"{tip}:base.txt")


def test_recent_stash_is_left_alone(repo: Path) -> None:
    (repo / "base.txt").write_text("modified", encoding="utf-8")
    git(repo, "stash", "push", "-m", "fresh work")
    report = report_for(repo, max_stash_age=24.0)
    assert report.stashes[0].action == "keep"
    repo_hygiene.apply_report(repo_hygiene.Git(repo), report)
    assert git(repo, "stash", "list")


# --- L4 receipts ---------------------------------------------------------------
#
# A receipt naming a branch the checkout is not on still reads as authoritative
# to local_execution_gate.py, which then refuses an unrelated publish citing a
# branch nobody recognises. Expiring them keeps that gate's message truthful.


def write_receipt(repo: Path, name: str, branch: str, started_at: str) -> Path:
    path = repo / ".l9" / "autonomy" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"stacked_branch": branch, "contract_id": "c1", "started_at": started_at}),
        encoding="utf-8",
    )
    return path


def now_iso(hours_ago: float = 0.0) -> str:
    stamp = datetime.now(UTC) - timedelta(hours=hours_ago)
    return stamp.strftime("%Y-%m-%dT%H:%M:%SZ")


def test_receipt_for_another_branch_is_archived(repo: Path) -> None:
    path = write_receipt(repo, "l4-release-receipt.json", "fix/some-other-branch", now_iso())
    report = report_for(repo)
    entry = report.receipts[0]
    assert entry.status == "foreign-branch"
    assert "fix/some-other-branch" in entry.detail and "main" in entry.detail

    repo_hygiene.apply_report(repo_hygiene.Git(repo), report)
    assert not path.exists()
    archived = list((repo / ".l9" / "autonomy" / "expired").glob("*l4-release-receipt.json"))
    assert len(archived) == 1, "receipts are archived as evidence, never deleted"


def test_current_branch_receipt_is_kept(repo: Path) -> None:
    path = write_receipt(repo, "l4-release-receipt.json", "main", now_iso())
    report = report_for(repo)
    assert report.receipts[0].status == "current"
    assert report.receipts[0].action == "keep"
    repo_hygiene.apply_report(repo_hygiene.Git(repo), report)
    assert path.exists()


def test_stale_receipt_for_current_branch_expires_on_age(repo: Path) -> None:
    write_receipt(repo, "l4-local-phase.json", "main", now_iso(hours_ago=48))
    report = report_for(repo, max_receipt_age=12.0)
    assert report.receipts[0].status == "expired"
    assert report.receipts[0].action == "archive"


def test_unreadable_receipt_is_archived(repo: Path) -> None:
    path = repo / ".l9" / "autonomy" / "l4-release-receipt.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json", encoding="utf-8")
    report = report_for(repo)
    assert report.receipts[0].status == "unreadable"


def test_no_receipts_is_not_an_error(repo: Path) -> None:
    assert report_for(repo).receipts == []


def test_assert_origin_mismatch_exits_nonzero(repo: Path) -> None:
    code = repo_hygiene.main(
        ["--workspace", str(repo), "--assert-origin", "Quantum-L9/Cursor-Governance"]
    )
    assert code == 3


def test_origin_slug_parses_ssh_and_https() -> None:
    assert repo_hygiene.origin_slug("git@github.com:Quantum-L9/Cursor-Governance.git") == (
        "Quantum-L9/Cursor-Governance"
    )
    assert repo_hygiene.origin_slug("https://github.com/Quantum-L9/Cursor-Governance") == (
        "Quantum-L9/Cursor-Governance"
    )


# -- CI-036: prune and origin/HEAD are one operation, not two ----------------
# #325 established that pruning ALONE converts an overcount into silence. The
# session-start path ships both halves; repo_hygiene -- the tool that DELETES
# branches on this evidence -- pruned without ever ensuring the fallback it
# creates a dependence on.


def _bare_upstream_with_clone(tmp_path: Path) -> tuple[Path, Path]:
    upstream = tmp_path / "upstream.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(upstream)], check=True)
    seed = tmp_path / "seed"
    subprocess.run(["git", "clone", "-q", str(upstream), str(seed)], check=True)
    for key, val in (("user.email", "t@example.com"), ("user.name", "t")):
        subprocess.run(["git", "-C", str(seed), "config", key, val], check=True)
    (seed / "a.txt").write_text("v1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(seed), "add", "a.txt"], check=True)
    subprocess.run(["git", "-C", str(seed), "commit", "-qm", "base"], check=True)
    subprocess.run(["git", "-C", str(seed), "push", "-q", "origin", "main"], check=True)
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", str(upstream), str(clone)], check=True)
    return upstream, clone


def test_sync_remote_refs_sets_origin_head_when_missing(tmp_path: Path) -> None:
    """The half repo_hygiene was missing: a pruned ref must leave a fallback."""
    _, clone = _bare_upstream_with_clone(tmp_path)
    subprocess.run(
        ["git", "-C", str(clone), "symbolic-ref", "-d", "refs/remotes/origin/HEAD"],
        check=True,
        capture_output=True,
    )
    git = repo_hygiene.Git(clone)
    assert not git.ok("symbolic-ref", "--quiet", "refs/remotes/origin/HEAD")

    assert repo_hygiene.sync_remote_refs(git) is None
    assert git.ok("symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"), (
        "prune without origin/HEAD is the state that makes counts read 0"
    )


def test_sync_remote_refs_prunes_a_branch_deleted_upstream(tmp_path: Path) -> None:
    upstream, clone = _bare_upstream_with_clone(tmp_path)
    subprocess.run(
        ["git", "-C", str(clone), "push", "-q", "origin", "HEAD:refs/heads/gone"], check=True
    )
    subprocess.run(["git", "-C", str(clone), "fetch", "-q", "origin"], check=True)
    git = repo_hygiene.Git(clone)
    assert git.ok("rev-parse", "--verify", "refs/remotes/origin/gone")

    subprocess.run(["git", "-C", str(upstream), "update-ref", "-d", "refs/heads/gone"], check=True)
    assert repo_hygiene.sync_remote_refs(git) is None
    assert not git.ok("rev-parse", "--verify", "refs/remotes/origin/gone")


def test_sync_remote_refs_is_fail_soft_without_a_remote(tmp_path: Path) -> None:
    """No network, or no origin, is not a reason to abort hygiene."""
    solo = tmp_path / "solo"
    solo.mkdir()
    subprocess.run(["git", "-C", str(solo), "init", "-q"], check=True)
    assert repo_hygiene.sync_remote_refs(repo_hygiene.Git(solo)) is None

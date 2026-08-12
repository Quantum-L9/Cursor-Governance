"""Shared-worktree isolation — block scoop/revert/switch of foreign dirty work."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ops" / "autonomy"))

from local_execution_gate import evaluate  # noqa: E402
from worktree_isolation_gate import command_violates_worktree_isolation  # noqa: E402


def test_denies_git_revert(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("L9_GIT_REVERT_AUTHORIZED", raising=False)
    monkeypatch.delenv("L9_WORKTREE_ISOLATION", raising=False)
    reason = command_violates_worktree_isolation("git revert --no-edit fc346c8")
    assert reason is not None
    assert "revert" in reason


def test_allows_revert_with_escape(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("L9_GIT_REVERT_AUTHORIZED", "human confirmed scoped")
    assert command_violates_worktree_isolation("git revert --no-edit abc") is None


def test_denies_diff_name_pipe_add_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("L9_GIT_BROAD_ADD_AUTHORIZED", raising=False)
    cmd = """
git diff --name-only | while read f; do
  case "$f" in
    WIP/*) echo skip ;;
    *) git add -- "$f" ;;
  esac
done
"""
    reason = command_violates_worktree_isolation(cmd)
    assert reason is not None
    assert "scoop" in reason or "piping" in reason


def test_denies_broad_add(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("L9_GIT_BROAD_ADD_AUTHORIZED", raising=False)
    for cmd in ("git add -A", "git add --all", "git add .", "git add -u"):
        assert command_violates_worktree_isolation(cmd) is not None, cmd


def test_allows_explicit_path_add(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("L9_GIT_BROAD_ADD_AUTHORIZED", raising=False)
    assert command_violates_worktree_isolation("git add -- commands/plan.md") is None


def test_denies_branch_checkout_when_dirty(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("L9_GIT_SWITCH_AUTHORIZED", raising=False)
    (stacked_repo / "dirt.txt").write_text("x\n", encoding="utf-8")
    assert (
        command_violates_worktree_isolation("git checkout main", root=stacked_repo)
        is not None
    )
    assert (
        command_violates_worktree_isolation("git switch feat/other", root=stacked_repo)
        is not None
    )


def test_allows_branch_checkout_when_clean(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("L9_GIT_SWITCH_AUTHORIZED", raising=False)
    assert (
        command_violates_worktree_isolation("git checkout main", root=stacked_repo)
        is None
    )


def test_allows_create_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("L9_GIT_SWITCH_AUTHORIZED", raising=False)
    assert command_violates_worktree_isolation("git checkout -b feat/new") is None
    assert command_violates_worktree_isolation("git switch -c feat/new") is None


def test_allows_path_checkout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("L9_GIT_SWITCH_AUTHORIZED", raising=False)
    assert (
        command_violates_worktree_isolation("git checkout -- AGENTS.md CANONICAL_LAW.md")
        is None
    )
    assert (
        command_violates_worktree_isolation(
            "git checkout origin/main -- AGENTS.md CANONICAL_LAW.md"
        )
        is None
    )


def test_denies_reset_when_dirty(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("L9_GIT_RESET_AUTHORIZED", raising=False)
    (stacked_repo / "dirt.txt").write_text("x\n", encoding="utf-8")
    assert (
        command_violates_worktree_isolation("git reset HEAD -- .", root=stacked_repo)
        is not None
    )


def test_evaluate_shell_hits_isolation(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("L9_GIT_REVERT_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    reason = evaluate(
        "Bash",
        {"command": "git revert --no-edit HEAD"},
        root=stacked_repo,
    )
    assert reason is not None
    assert "shared-worktree isolation" in reason


def test_isolation_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("L9_WORKTREE_ISOLATION", "0")
    assert command_violates_worktree_isolation("git revert HEAD") is None

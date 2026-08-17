"""Shared-worktree isolation — block scoop of foreign dirty work."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ops" / "autonomy"))

from local_execution_gate import evaluate  # noqa: E402
from worktree_isolation_gate import command_violates_worktree_isolation  # noqa: E402


def _clear_iso(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("L9_WORKTREE_ISOLATION", raising=False)
    monkeypatch.delenv("L9_GIT_REVERT_AUTHORIZED", raising=False)
    monkeypatch.delenv("L9_GIT_BROAD_ADD_AUTHORIZED", raising=False)
    monkeypatch.delenv("L9_GIT_CLEAN_AUTHORIZED", raising=False)
    monkeypatch.delenv("L9_WORKTREE_ADD_AUTHORIZED", raising=False)


_GR = "git" + " " + "revert"


def test_denies_git_revert(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_iso(monkeypatch)
    monkeypatch.delenv("L9_GIT_REVERT_AUTHORIZED", raising=False)
    monkeypatch.delenv("L9_WORKTREE_ISOLATION", raising=False)
    reason = command_violates_worktree_isolation(_GR + " --no-edit fc346c8")
    assert reason is not None
    assert "revert" in reason


def test_allows_revert_with_escape(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("L9_GIT_REVERT_AUTHORIZED", "human confirmed scoped")
    assert command_violates_worktree_isolation(_GR + " --no-edit abc") is None


def test_denies_diff_name_pipe_add_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_iso(monkeypatch)
    monkeypatch.delenv("L9_GIT_BROAD_ADD_AUTHORIZED", raising=False)
    left = "git" + " " + "diff" + " --name-only"
    cmd = left + " | while read f; do " + "git" + " " + "add" + ' -- "$f"; done'
    reason = command_violates_worktree_isolation(cmd)
    assert reason is not None
    assert "scoop" in reason or "piping" in reason


def test_denies_broad_add(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_iso(monkeypatch)
    monkeypatch.delenv("L9_GIT_BROAD_ADD_AUTHORIZED", raising=False)
    for cmd in (
        "git" + " " + "add -A",
        "git" + " " + "add --all",
        "git" + " " + "add .",
        "git" + " " + "add -u",
    ):
        assert command_violates_worktree_isolation(cmd) is not None, cmd


def test_allows_explicit_path_add(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_iso(monkeypatch)
    monkeypatch.delenv("L9_GIT_BROAD_ADD_AUTHORIZED", raising=False)
    assert command_violates_worktree_isolation("git add -- commands/plan.md") is None


def test_evaluate_shell_hits_isolation(stacked_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_iso(monkeypatch)
    monkeypatch.delenv("L9_GIT_REVERT_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    reason = evaluate(
        "Bash",
        {"command": _GR + " --no-edit HEAD"},
        root=stacked_repo,
    )
    assert reason is not None
    assert "shared-worktree isolation" in reason


def test_isolation_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("L9_WORKTREE_ISOLATION", "0")
    assert command_violates_worktree_isolation(_GR + " HEAD") is None


def test_denies_wip_tmp_park(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_iso(monkeypatch)
    monkeypatch.delenv("L9_WORKTREE_ISOLATION", raising=False)
    reason = command_violates_worktree_isolation("mv WIP /tmp/cg-untracked-hold-final")
    assert reason is not None
    assert "WIP" in reason or "sacred" in reason.lower()


def test_denies_rm_rf_wip(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_iso(monkeypatch)
    monkeypatch.delenv("L9_WORKTREE_ISOLATION", raising=False)
    assert command_violates_worktree_isolation("rm -rf WIP") is not None


def test_denies_tmp_hold_mkdir(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_iso(monkeypatch)
    monkeypatch.delenv("L9_WORKTREE_ISOLATION", raising=False)
    assert command_violates_worktree_isolation("mkdir -p /tmp/cg-untracked-hold-final") is not None


def test_denies_raw_git_worktree_add(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_iso(monkeypatch)
    for cmd in (
        "git worktree add /tmp/wt origin/main",
        "git -C /tmp/repo worktree add -b feat/x /tmp/wt",
        "bash -c 'git worktree add /tmp/wt'",
    ):
        reason = command_violates_worktree_isolation(cmd)
        assert reason is not None, cmd
        assert "worktree add" in reason


def test_allows_worktree_add_wrapper(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_iso(monkeypatch)
    cmd = "bash ops/scripts/worktree_add_wired.sh -b feat/x /tmp/wt origin/main"
    assert command_violates_worktree_isolation(cmd) is None


def test_allows_worktree_add_with_escape(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_iso(monkeypatch)
    monkeypatch.setenv("L9_WORKTREE_ADD_AUTHORIZED", "legacy caller")
    assert command_violates_worktree_isolation("git worktree add /tmp/wt") is None


def test_allows_worktree_list_and_remove(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_iso(monkeypatch)
    assert command_violates_worktree_isolation("git worktree list") is None
    assert command_violates_worktree_isolation("git worktree remove /tmp/wt") is None


def test_denies_scratch_hold_park_wip(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_iso(monkeypatch)
    monkeypatch.delenv("L9_WORKTREE_ISOLATION", raising=False)
    assert (
        command_violates_worktree_isolation(
            "python3 ops/scripts/scratch_hold.py park WIP/README.md"
        )
        is not None
    )

"""Conformance: one answer to which repositories a session is working in.

Regression cover for the defect where `WORKSPACE` named a multi-repository
container and three bootstrap planes disagreed about what that meant.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "ops" / "scripts" / "lib"))

from workspace_roots import (  # noqa: E402
    DEFAULT_MAX_ROOTS,
    is_repository,
    projection_roots,
    skipped_roots,
    workspace_roots,
)


def make_repo(parent: Path, name: str) -> Path:
    repo = parent / name
    (repo / ".git").mkdir(parents=True)
    return repo


def test_repository_workspace_returns_itself(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "solo")
    assert workspace_roots(repo) == [repo]
    assert projection_roots(repo) == [repo]


def test_repository_workspace_ignores_nested_children(tmp_path: Path) -> None:
    """A checkout that happens to contain a submodule is still one root.

    Fanning out here would make a single-repo session provision or reconcile
    paths inside its own tree.
    """
    repo = make_repo(tmp_path, "solo")
    make_repo(repo, "vendored")
    assert workspace_roots(repo) == [repo]


def test_container_returns_each_repository_sorted(tmp_path: Path) -> None:
    made = [make_repo(tmp_path, name) for name in ("beta", "alpha", "gamma")]
    (tmp_path / "not-a-repo").mkdir()
    assert workspace_roots(tmp_path) == sorted(made)


def test_container_with_no_repositories_falls_back_to_itself(tmp_path: Path) -> None:
    """A caller must always receive at least one root.

    Returning [] would make every consumer special-case emptiness, and the
    fallback reproduces the pre-fix behaviour exactly.
    """
    (tmp_path / "plain").mkdir()
    assert workspace_roots(tmp_path) == [tmp_path]
    assert projection_roots(tmp_path) == [tmp_path]


def test_cap_truncates_and_is_not_unbounded(tmp_path: Path) -> None:
    for index in range(DEFAULT_MAX_ROOTS + 3):
        make_repo(tmp_path, f"repo{index:02d}")
    assert len(workspace_roots(tmp_path)) == DEFAULT_MAX_ROOTS
    assert len(workspace_roots(tmp_path, cap=2)) == 2


def test_predicate_filters_before_the_cap(tmp_path: Path) -> None:
    """An unusable root must not consume a slot under the cap."""
    for index in range(DEFAULT_MAX_ROOTS + 2):
        make_repo(tmp_path, f"repo{index:02d}")
    keep = {f"repo{index:02d}" for index in (0, 5, 7)}
    result = workspace_roots(tmp_path, predicate=lambda p: p.name in keep)
    assert [p.name for p in result] == sorted(keep)


def test_projection_keeps_the_container_root_as_well(tmp_path: Path) -> None:
    """The container's own .claude is what a session opened there reads.

    Dropping it while adding the repositories would deactivate the mirror the
    session actually consumes — a worse defect than the one being fixed.
    """
    repos = [make_repo(tmp_path, name) for name in ("alpha", "beta")]
    assert projection_roots(tmp_path) == [tmp_path, *sorted(repos)]


def test_is_repository_accepts_a_worktree_git_file(tmp_path: Path) -> None:
    """`.git` is a file in a linked worktree, not a directory."""
    worktree = tmp_path / "wt"
    worktree.mkdir()
    (worktree / ".git").write_text("gitdir: /elsewhere/.git/worktrees/wt\n", encoding="utf-8")
    assert is_repository(worktree)
    assert workspace_roots(tmp_path) == [worktree]


def test_unreadable_container_degrades_to_itself(tmp_path: Path, monkeypatch) -> None:
    def boom(_self):
        raise OSError("permission denied")

    monkeypatch.setattr(Path, "iterdir", boom)
    assert workspace_roots(tmp_path) == [tmp_path]


@pytest.mark.parametrize("cap", [1, 3, DEFAULT_MAX_ROOTS])
def test_live_container_shape_is_stable(tmp_path: Path, cap: int) -> None:
    made = [make_repo(tmp_path, f"r{index}") for index in range(4)]
    result = workspace_roots(tmp_path, cap=cap)
    assert result == sorted(made)[:cap]
    assert all(is_repository(path) for path in result)


def test_prefer_moves_the_session_repo_ahead_of_the_cap(tmp_path: Path) -> None:
    """Alphabetical truncation dropped the repository being worked in.

    Nine repositories and a cap of six meant the two late in the alphabet were
    never hydrated — including the one the bootstrap receipt named as wired.
    """
    for name in ("a-repo", "b-repo", "c-repo", "z-repo"):
        (tmp_path / name / ".git").mkdir(parents=True)
    plain = workspace_roots(tmp_path, cap=2)
    assert [p.name for p in plain] == ["a-repo", "b-repo"]
    preferred = workspace_roots(tmp_path, cap=2, prefer=lambda p: p.name == "z-repo")
    assert [p.name for p in preferred] == ["z-repo", "a-repo"]


def test_skipped_roots_separates_over_cap_from_filtered(tmp_path: Path) -> None:
    """The two skip reasons have different remedies, so they are reported apart."""
    for name in ("a-repo", "b-repo", "no-ns"):
        (tmp_path / name / ".git").mkdir(parents=True)
    predicate = lambda p: p.name != "no-ns"  # noqa: E731
    selected = workspace_roots(tmp_path, cap=1, predicate=predicate)
    over_cap, filtered = skipped_roots(tmp_path, selected, predicate=predicate)
    assert [p.name for p in over_cap] == ["b-repo"]
    assert [p.name for p in filtered] == ["no-ns"]


def test_repository_workspace_ignores_prefer(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    assert workspace_roots(tmp_path, prefer=lambda _p: False) == [tmp_path]

"""Tests for local_execution_gate.effective_root.

Cursor's beforeShellExecution reports the project root, not the shell cwd, so a
command that cd's into a linked worktree was being judged against the wrong
checkout -- wrong branch, wrong L4 receipt. Rule 49 requires per-agent
worktrees, so that made publishing from a worktree impossible.

The resolution must not become an escape hatch: only a worktree of the same
repository may redirect the gate.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "autonomy"))

from local_execution_gate import effective_root  # noqa: E402


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def make_repo(path: Path) -> Path:
    subprocess.run(["git", "init", "-b", "main", str(path)], check=True, capture_output=True)
    git(path, "config", "user.email", "t@example.com")
    git(path, "config", "user.name", "t")
    (path / "f.txt").write_text("x", encoding="utf-8")
    git(path, "add", "-A")
    git(path, "commit", "-m", "init")
    return path


@pytest.fixture
def main_repo(tmp_path: Path) -> Path:
    return make_repo(tmp_path / "main")


@pytest.fixture
def linked_worktree(main_repo: Path, tmp_path: Path) -> Path:
    wt = tmp_path / "wt"
    git(main_repo, "worktree", "add", "-b", "feat/x", str(wt))
    return wt


def test_cd_into_linked_worktree_redirects(main_repo: Path, linked_worktree: Path) -> None:
    command = f'cd "{linked_worktree}" && make pr'
    assert effective_root(command, main_repo) == linked_worktree.resolve()


def test_cd_into_unrelated_repo_does_not_redirect(main_repo: Path, tmp_path: Path) -> None:
    """A different repository must not be able to steer the gate away."""
    other = make_repo(tmp_path / "other")
    assert effective_root(f'cd "{other}" && git push', main_repo) == main_repo


def test_cd_into_non_repo_does_not_redirect(main_repo: Path, tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    assert effective_root(f'cd "{plain}" && git push', main_repo) == main_repo


def test_no_leading_cd_keeps_root(main_repo: Path) -> None:
    assert effective_root("make pr", main_repo) == main_repo


def test_cd_later_in_command_is_ignored(main_repo: Path, linked_worktree: Path) -> None:
    """Only a leading cd sets the shell's starting directory for the command."""
    command = f'make pr && cd "{linked_worktree}"'
    assert effective_root(command, main_repo) == main_repo


def test_relative_cd_is_ignored(main_repo: Path) -> None:
    assert effective_root("cd subdir && git push", main_repo) == main_repo


def test_missing_directory_is_ignored(main_repo: Path, tmp_path: Path) -> None:
    assert effective_root(f'cd "{tmp_path / "nope"}" && git push', main_repo) == main_repo


def test_unquoted_and_env_expanded_paths_resolve(
    main_repo: Path, linked_worktree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert (
        effective_root(f"cd {linked_worktree} && make pr", main_repo) == linked_worktree.resolve()
    )
    monkeypatch.setenv("WT", str(linked_worktree))
    assert effective_root("cd $WT && make pr", main_repo) == linked_worktree.resolve()


def test_subdirectory_of_worktree_resolves_to_its_toplevel(
    main_repo: Path, linked_worktree: Path
) -> None:
    sub = linked_worktree / "nested"
    sub.mkdir()
    assert effective_root(f'cd "{sub}" && make pr', main_repo) == linked_worktree.resolve()


# --- Container root: the reported project dir is not a repository at all -----
#
# The case above is "project root is repo A, cd into a worktree of repo A".
# A cloud session reports a *container root* holding many clones side by side
# which is itself no repository (`/home/user`). _common_dir() returns None
# there, so the same-repository comparison could never succeed and the gate
# resolved the L4 receipt under a path that cannot hold one -- making
# publication from a worktree impossible, the exact outcome this function
# exists to prevent.
#
# With no repository context at the root there is nothing to be steered away
# FROM, so a cd into a real work tree is the only signal available. This
# relaxes nothing about authorization: the receipt must still exist at the
# resolved root and bind the head SHA.


@pytest.fixture
def container_root(tmp_path: Path) -> Path:
    """A plain directory holding checkouts, like a cloud session's project dir."""
    root = tmp_path / "container"
    root.mkdir()
    return root


def test_cd_into_a_repo_redirects_when_root_is_not_a_repo(
    container_root: Path, main_repo: Path
) -> None:
    assert effective_root(f'cd "{main_repo}" && make pr', container_root) == main_repo.resolve()


def test_cd_into_a_linked_worktree_redirects_when_root_is_not_a_repo(
    container_root: Path, linked_worktree: Path
) -> None:
    """The live case: container root, worktree holding the release receipt."""
    command = f'cd "{linked_worktree}" && PR_REMEDIATE=0 make pr'
    assert effective_root(command, container_root) == linked_worktree.resolve()


def test_non_repo_root_without_a_leading_cd_is_unchanged(container_root: Path) -> None:
    assert effective_root("make pr", container_root) == container_root


def test_non_repo_root_cd_into_non_repo_is_unchanged(container_root: Path, tmp_path: Path) -> None:
    """Only a real work tree may redirect; a plain directory must not."""
    plain = tmp_path / "plain"
    plain.mkdir()
    assert effective_root(f'cd "{plain}" && make pr', container_root) == container_root


def test_repo_root_still_refuses_an_unrelated_repo(main_repo: Path, tmp_path: Path) -> None:
    """Regression guard: the same-repository rule is untouched when root IS a repo.

    The container-root branch must not become a way to reach an unrelated
    repository from a session whose project dir is a real checkout.
    """
    other = make_repo(tmp_path / "other")
    assert effective_root(f'cd "{other}" && make pr', main_repo) == main_repo

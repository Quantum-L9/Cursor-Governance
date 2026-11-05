"""ops/scripts/lib/ci_pr_scope.sh: PR changed-file scope for Core's `make test`.

Each case runs the helper in a real temporary git repository. The PR shape is
the one GitHub tests for pull_request: a two-parent merge commit whose first
parent is the base tip. Every state that is not that shape must fall back to
the full suite (exit 1), because a wrong scope would hide tests.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

HELPER = Path(__file__).resolve().parents[3] / "ops" / "scripts" / "lib" / "ci_pr_scope.sh"

_GIT_ENV = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.invalid",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
}


def _base_env() -> dict[str, str]:
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("GITHUB_", "GIT_")) and k != "L9_CI_FULL_SUITE"
    }
    env.update(_GIT_ENV)
    return env


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, env=_base_env(), check=True, capture_output=True, text=True
    ).stdout.strip()


def _write(root: Path, name: str, text: str) -> None:
    (root / name).write_text(text, encoding="utf-8")


def _run(cwd: Path, **env: str) -> subprocess.CompletedProcess[str]:
    full_env = _base_env()
    full_env.update(env)
    return subprocess.run(
        ["bash", "-c", f'source "{HELPER}"; l9_ci_pr_changed_files'],
        cwd=cwd,
        env=full_env,
        capture_output=True,
        text=True,
        check=False,
    )


PR = {"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "pull_request"}


@pytest.fixture
def merged(tmp_path: Path) -> Path:
    """main <- merge of a feature that edits a.txt, adds c.txt, deletes b.txt.

    main also gains keep.txt after the branch point, so a diff against the
    merge base instead of the first parent would wrongly list it.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _write(repo, "a.txt", "a\n")
    _write(repo, "b.txt", "b\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    _git(repo, "switch", "-q", "-c", "feature")
    _write(repo, "a.txt", "a2\n")
    _write(repo, "c.txt", "c\n")
    _git(repo, "rm", "-q", "b.txt")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "feature")
    _git(repo, "switch", "-q", "main")
    _write(repo, "keep.txt", "k\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "main moves")
    _git(repo, "merge", "-q", "--no-ff", "-m", "merge", "feature")
    return repo


def test_pull_request_merge_commit_lists_changed_paths_on_head(merged: Path) -> None:
    result = _run(merged, **PR)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["a.txt", "c.txt"]
    assert "[ci-scope] pull_request: 2 changed path(s)" in result.stderr


def test_depth_one_checkout_fetches_the_parents(merged: Path, tmp_path: Path) -> None:
    shallow = tmp_path / "shallow"
    _git(tmp_path, "clone", "-q", "--depth=1", f"file://{merged}", str(shallow))
    assert _git(shallow, "rev-parse", "--is-shallow-repository") == "true"
    result = _run(shallow, **PR)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["a.txt", "c.txt"]


def test_unfetchable_parents_fall_back_to_full_suite(merged: Path, tmp_path: Path) -> None:
    shallow = tmp_path / "shallow"
    _git(tmp_path, "clone", "-q", "--depth=1", f"file://{merged}", str(shallow))
    _git(shallow, "remote", "set-url", "origin", f"file://{tmp_path / 'missing'}")
    result = _run(shallow, **PR)
    assert result.returncode == 1
    assert result.stdout == ""
    assert "could not fetch" in result.stderr


@pytest.mark.parametrize(
    ("env", "reason"),
    [
        ({"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "push"}, "event push"),
        ({"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "workflow_dispatch"}, "event workflow"),
        ({**PR, "L9_CI_FULL_SUITE": "1"}, "L9_CI_FULL_SUITE=1"),
    ],
)
def test_non_pr_or_forced_runs_use_full_suite(
    merged: Path, env: dict[str, str], reason: str
) -> None:
    result = _run(merged, **env)
    assert result.returncode == 1
    assert result.stdout == ""
    assert reason in result.stderr


def test_local_shell_uses_full_suite_silently(merged: Path) -> None:
    result = _run(merged, GITHUB_EVENT_NAME="pull_request")
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == ""


def test_single_parent_head_uses_full_suite(merged: Path) -> None:
    _git(merged, "switch", "-q", "feature")
    result = _run(merged, **PR)
    assert result.returncode == 1
    assert "not a two-parent merge commit" in result.stderr


def test_merge_that_changes_nothing_uses_full_suite(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _write(repo, "a.txt", "a\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    _git(repo, "switch", "-q", "-c", "feature")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "empty")
    _git(repo, "switch", "-q", "main")
    _git(repo, "merge", "-q", "--no-ff", "-m", "merge", "feature")
    result = _run(repo, **PR)
    assert result.returncode == 1
    assert "changes no files" in result.stderr


def test_deletion_only_pr_scopes_to_nothing(tmp_path: Path) -> None:
    """Matches the Test Suite: missing-on-HEAD paths drop, an empty set is not full."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _write(repo, "a.txt", "a\n")
    _write(repo, "b.txt", "b\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    _git(repo, "switch", "-q", "-c", "feature")
    _git(repo, "rm", "-q", "b.txt")
    _git(repo, "commit", "-q", "-m", "drop b")
    _git(repo, "switch", "-q", "main")
    _git(repo, "merge", "-q", "--no-ff", "-m", "merge", "feature")
    result = _run(repo, **PR)
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert "0 changed path(s)" in result.stderr


def test_pr_full_forces_the_full_suite_on_its_test_prerequisite() -> None:
    """`make pr-full` is the full gate even inside a pull_request CI job.

    Read make's own database (-p) without running anything (-n -q): pr-full
    must carry the target-specific export, which GNU make passes to `test`.
    """
    repo = HELPER.parents[3]
    db = subprocess.run(
        ["make", "-C", str(repo), "-p", "-n", "-q", "pr-full"],
        env=_base_env(),
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    ).stdout
    # make -p prints a target-specific variable as `<target>: NAME := value`.
    assert "pr-full: L9_CI_FULL_SUITE := 1" in db.splitlines(), (
        "make does not attach L9_CI_FULL_SUITE := 1 to pr-full"
    )
    # -p does not show `export`; without it the recipe's shell never sees the value.
    publish = (repo / "ops" / "make" / "publish.mk").read_text(encoding="utf-8")
    assert "pr-full: export L9_CI_FULL_SUITE := 1" in publish.splitlines()

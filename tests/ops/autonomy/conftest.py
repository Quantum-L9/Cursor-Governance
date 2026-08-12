"""Shared fixtures for ops/autonomy tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def git_in(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def stacked_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git_in(repo, "init")
    git_in(repo, "config", "user.email", "test@example.com")
    git_in(repo, "config", "user.name", "test")
    (repo / "README.md").write_text("x\n", encoding="utf-8")
    git_in(repo, "add", "README.md")
    git_in(repo, "commit", "-m", "init")
    git_in(repo, "branch", "-M", "main")
    git_in(repo, "checkout", "-b", "feat/l4-stack")
    (repo / "a.txt").write_text("a\n", encoding="utf-8")
    git_in(repo, "add", "a.txt")
    git_in(repo, "commit", "-m", "local work")
    return repo

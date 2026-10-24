"""Fixtures for the governance-generation tooling: an isolated, committed copy of its inputs."""

from __future__ import annotations

import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
COPIED = ("tools/authority", "contracts/schemas", "skills/l9-global-architect")
PACK = "skills/l9-global-architect"


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@invalid", *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


class GovRepo:
    """A git repository holding only what the generation tooling reads, committed once."""

    def __init__(self, root: Path) -> None:
        self.root = root
        for rel in COPIED:
            shutil.copytree(REPO / rel, root / rel, ignore=shutil.ignore_patterns("__pycache__"))
        git(root, "init", "-q")
        self.commit("inputs")

    def commit(self, message: str) -> None:
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "--allow-empty", "-m", message)

    def run(self, tool: str, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(self.root / "tools/authority" / tool),
                "--root",
                str(self.root),
                *args,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def generate(self) -> subprocess.CompletedProcess[str]:
        return self.run("generate_contract_registry.py")

    def edit(self, rel: str, transform: Callable[[str], str]) -> None:
        path = self.root / rel
        before = path.read_text(encoding="utf-8")
        after = transform(before)
        assert after != before, f"edit of {rel} changed nothing"
        path.write_text(after, encoding="utf-8")


@pytest.fixture
def gov_repo(tmp_path: Path) -> GovRepo:
    return GovRepo(tmp_path / "gov")


@pytest.fixture
def generated_repo(gov_repo: GovRepo) -> GovRepo:
    """Inputs committed, outputs generated and committed: the state a merged PR leaves."""
    result = gov_repo.generate()
    assert result.returncode == 0, result.stdout + result.stderr
    gov_repo.commit("generated")
    return gov_repo

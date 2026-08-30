"""Tests for ops/scripts/verify_worktree_clean.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "scripts"))

import verify_worktree_clean as verify  # noqa: E402


def git(root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def commit(root: Path, name: str, body: str = "x") -> None:
    (root / name).parent.mkdir(parents=True, exist_ok=True)
    (root / name).write_text(body, encoding="utf-8")
    git(root, "add", "--", name)
    git(root, "commit", "-m", f"add {name}")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    upstream = tmp_path / "upstream.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(upstream)], check=True)
    root = tmp_path / "work"
    subprocess.run(["git", "init", "-b", "main", str(root)], check=True)
    git(root, "config", "user.email", "t@example.com")
    git(root, "config", "user.name", "t")
    git(root, "remote", "add", "origin", str(upstream))
    commit(root, "base.txt", "base")
    git(root, "push", "-u", "origin", "main")
    return root


def test_clean_main_passes(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("L9_DIRT_CLOSE_QUIET_SECONDS", "0")

    def fake_dirt(root: Path, baseline: str) -> dict:
        return {"dirty_unique": 0, "dirty_files": []}

    monkeypatch.setattr(verify, "_run_dirt_status", fake_dirt)
    ok, errors, _warnings = verify.verify(repo, fetch=False)
    assert ok
    assert not errors


def test_unpushed_commit_fails(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("L9_DIRT_CLOSE_QUIET_SECONDS", "0")
    commit(repo, "extra.txt", "local only")
    monkeypatch.setattr(verify, "_run_dirt_status", lambda _r, _b: {"dirty_unique": 0})
    ok, errors, _warnings = verify.verify(repo, fetch=False)
    assert not ok
    assert any("ahead" in e for e in errors)


def test_dirty_unique_fails(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(verify, "_run_dirt_status", lambda _r, _b: {"dirty_unique": 2})
    ok, errors, _warnings = verify.verify(repo, fetch=False)
    assert not ok
    assert any("dirty_unique" in e for e in errors)


def test_cli_json(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(verify, "_run_dirt_status", lambda _r, _b: {"dirty_unique": 0})
    assert verify.main(["--workspace", str(repo), "--no-fetch", "--json"]) == 0

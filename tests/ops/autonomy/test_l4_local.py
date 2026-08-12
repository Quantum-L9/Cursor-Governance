"""Tests for L4 local autonomy phase machine + remote gate."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ops" / "autonomy"))

from l4_local import (  # noqa: E402
    authorize_release,
    begin,
    record_kernels,
    release_allows_remote,
)
from local_execution_gate import evaluate  # noqa: E402


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture()
def stacked_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "test")
    (repo / "README.md").write_text("x\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "init")
    _git(repo, "branch", "-M", "main")
    _git(repo, "checkout", "-b", "feat/l4-stack")
    (repo / "a.txt").write_text("a\n", encoding="utf-8")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-m", "local work")
    return repo


def test_denies_remote_without_release(stacked_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    allowed, reason = release_allows_remote(stacked_repo)
    assert not allowed
    assert "mid-execution" in reason or "L4" in reason


def test_begin_kernels_authorize_allows_push(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    begin(stacked_repo, contract_id="c1")
    assert release_allows_remote(stacked_repo)[0] is False
    record_kernels(stacked_repo)
    assert release_allows_remote(stacked_repo)[0] is False
    receipt = authorize_release(stacked_repo)
    assert receipt["phase"] == "release_authorized"
    allowed, reason = release_allows_remote(stacked_repo)
    assert allowed
    assert "release_authorized" in reason


def test_gate_denies_git_push(stacked_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    reason = evaluate(
        "Bash",
        {"command": "git push -u origin HEAD"},
        root=stacked_repo,
    )
    assert reason is not None


def test_gate_allows_local_commit(stacked_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    reason = evaluate(
        "Bash",
        {"command": "git commit -m 'local only'"},
        root=stacked_repo,
    )
    assert reason is None


def test_breakglass_allows(stacked_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("L9_LOCAL_PUSH_AUTHORIZED", "human override")
    allowed, _ = release_allows_remote(stacked_repo)
    assert allowed


def test_cli_check_remote_exit_codes(stacked_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    cli = ROOT / "ops" / "autonomy" / "l4_local.py"
    denied = subprocess.run(
        [sys.executable, str(cli), "--workspace", str(stacked_repo), "check-remote"],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "L9_L4_LOCAL_AUTONOMY": "1"},
    )
    assert denied.returncode == 2
    begin(stacked_repo)
    record_kernels(stacked_repo)
    authorize_release(stacked_repo)
    ok = subprocess.run(
        [sys.executable, str(cli), "--workspace", str(stacked_repo), "check-remote"],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "L9_L4_LOCAL_AUTONOMY": "1"},
    )
    assert ok.returncode == 0
    assert json.loads(ok.stdout)["allowed"] is True

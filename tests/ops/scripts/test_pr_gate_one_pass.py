"""Prove make pr resolves changed files once and runs pre-commit once.

GATE-002 requires an execution count, not source inspection alone.
"""

from __future__ import annotations

import os
import stat
import subprocess
from collections import Counter
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
GATE = REPO_ROOT / "ops" / "scripts" / "run_pr_gate.sh"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def fixture_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "ws"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "test")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-qm", "base")
    (repo / "README.md").write_text("changed\n", encoding="utf-8")
    return repo


def test_make_pr_resolves_and_precommits_once(tmp_path: Path, fixture_repo: Path) -> None:
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    precommit = stub_bin / "pre-commit"
    precommit.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    precommit.chmod(precommit.stat().st_mode | stat.S_IEXEC)

    trace = tmp_path / "pr-gate.trace"
    env = {
        **os.environ,
        "PATH": f"{stub_bin}{os.pathsep}{os.environ['PATH']}",
        "WS": str(fixture_repo),
        "PR_BASE": "HEAD",
        "L9_PR_GATE_TRACE": str(trace),
        "L9_PR_GATE_SELFTEST": "1",
        "L9_REPO_WRITE_LOCK": "0",
    }
    proc = subprocess.run(
        ["bash", str(GATE)],
        cwd=fixture_repo,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    events = Counter(
        line.strip() for line in trace.read_text(encoding="utf-8").splitlines() if line.strip()
    )
    assert events["resolve_changed_files"] == 1, events
    assert events["precommit"] == 1, events
    assert events["outer_ruff"] == 0, events
    assert events["outer_sync_generated"] == 0, events


def test_outer_gate_does_not_reinvoke_precommit_owned_hooks() -> None:
    text = GATE.read_text(encoding="utf-8")
    assert "ruff check" not in text
    assert "ruff format" not in text
    assert "sync_generated_artifacts.py" not in text

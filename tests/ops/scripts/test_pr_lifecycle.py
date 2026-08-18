"""Capability-graph PR lifecycle: improve, preflight, soft-empty, gate receipt."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "ops" / "scripts"
L4 = ROOT / "ops" / "autonomy" / "l4_local.py"


def git_in(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _init_repo(tmp_path: Path, *, feature: bool = True) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git_in(repo, "init")
    git_in(repo, "config", "user.email", "test@example.com")
    git_in(repo, "config", "user.name", "test")
    (repo / ".gitignore").write_text(".l9/\n", encoding="utf-8")
    (repo / "README.md").write_text("x\n", encoding="utf-8")
    git_in(repo, "add", ".gitignore", "README.md")
    git_in(repo, "commit", "-m", "init")
    git_in(repo, "branch", "-M", "main")
    git_in(repo, "branch", "origin-main")
    if feature:
        git_in(repo, "checkout", "-b", "feat/stack")
        (repo / "a.txt").write_text("a\n", encoding="utf-8")
        git_in(repo, "add", "a.txt")
        git_in(repo, "commit", "-m", "local work")
    return repo


def _run(args: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = {**os.environ, **(env or {})}
    return subprocess.run(
        args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
        env=merged,
    )


def test_resolver_empty_fails_closed(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path, feature=False)
    proc = _run(
        ["bash", str(SCRIPTS / "resolve_changed_files.sh")],
        cwd=repo,
        env={"PR_BASE": "main", "WS": str(repo), "PR_ALLOW_EMPTY": "0"},
    )
    assert proc.returncode == 1
    assert "empty change set" in proc.stderr


def test_resolver_empty_soft_pass(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path, feature=False)
    proc = _run(
        ["bash", str(SCRIPTS / "resolve_changed_files.sh")],
        cwd=repo,
        env={"PR_BASE": "main", "WS": str(repo), "PR_ALLOW_EMPTY": "1"},
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""
    assert "SOURCE:empty" in proc.stderr


def test_preflight_fails_on_main(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path, feature=False)
    proc = _run(
        ["bash", str(SCRIPTS / "pr_preflight.sh"), str(repo)],
        cwd=repo,
        env={"PR_BASE": "main", "WS": str(repo), "L9_L4_LOCAL_AUTONOMY": "1"},
    )
    assert proc.returncode == 1
    assert "main" in proc.stderr or "main" in proc.stdout


def test_preflight_fails_without_l4(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path, feature=True)
    proc = _run(
        ["bash", str(SCRIPTS / "pr_preflight.sh"), str(repo)],
        cwd=repo,
        env={"PR_BASE": "main", "WS": str(repo), "L9_L4_LOCAL_AUTONOMY": "1"},
    )
    assert proc.returncode == 1
    assert "make improve" in proc.stderr


def test_preflight_passes_after_authorize(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path, feature=True)
    env = {"L9_L4_LOCAL_AUTONOMY": "1", "WS": str(repo), "PR_BASE": "main"}
    assert (
        _run(["python3", str(L4), "--workspace", str(repo), "begin"], cwd=repo, env=env).returncode
        == 0
    )
    assert (
        _run(
            ["python3", str(L4), "--workspace", str(repo), "record-kernels"],
            cwd=repo,
            env=env,
        ).returncode
        == 0
    )
    assert (
        _run(
            ["python3", str(L4), "--workspace", str(repo), "authorize-release"],
            cwd=repo,
            env=env,
        ).returncode
        == 0
    )
    proc = _run(
        ["bash", str(SCRIPTS / "pr_preflight.sh"), str(repo)],
        cwd=repo,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    assert "OK: pr-preflight" in proc.stdout


def test_improve_record_refused_without_phase(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path, feature=True)
    proc = _run(
        ["bash", str(SCRIPTS / "run_improve.sh")],
        cwd=repo,
        env={"WS": str(repo), "IMPROVE_RECORD": "1", "PR_BASE": "main"},
    )
    assert proc.returncode == 1
    assert "IMPROVE_RECORD refused" in proc.stderr


def test_improve_begin_then_record(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path, feature=True)
    env = {"WS": str(repo), "PR_BASE": "main", "IMPROVE_RECORD": "0"}
    begin = _run(["bash", str(SCRIPTS / "run_improve.sh")], cwd=repo, env=env)
    assert begin.returncode == 0, begin.stderr
    assert "L9_AGENT_REQUIRED" in begin.stdout
    rec = _run(
        ["bash", str(SCRIPTS / "run_improve.sh")],
        cwd=repo,
        env={**env, "IMPROVE_RECORD": "1"},
    )
    assert rec.returncode == 0, rec.stderr
    receipt = json.loads((repo / ".l9" / "autonomy" / "l4-release-receipt.json").read_text())
    assert receipt["phase"] == "release_authorized"


def test_gate_receipt_skip_on_unchanged_state(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path, feature=True)
    head = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    digest = subprocess.check_output(
        ["bash", "-c", "git status --porcelain | cksum | awk '{print $1}'"],
        cwd=str(repo),
        text=True,
    ).strip()
    receipt_dir = repo / ".l9" / "pr"
    receipt_dir.mkdir(parents=True)
    (receipt_dir / "gate-receipt.json").write_text(
        json.dumps(
            {
                "schema": "l9.pr_gate_receipt.v1",
                "head": head,
                "worktree_digest": digest,
                "pr_base": "main",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    proc = _run(
        ["bash", str(SCRIPTS / "run_pr_gate.sh")],
        cwd=repo,
        env={"WS": str(repo), "PR_BASE": "main", "PR_LOCK_WAIT_S": "1"},
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "receipt reuse" in proc.stdout


def test_precommit_reuses_changed_file(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path, feature=True)
    listed = tmp_path / "changed.txt"
    listed.write_text("", encoding="utf-8")
    proc = _run(
        ["bash", str(SCRIPTS / "run_pr_precommit.sh"), str(repo)],
        cwd=repo,
        env={"WS": str(repo), "PR_BASE": "main", "PR_CHANGED_FILE": str(listed)},
    )
    assert proc.returncode == 0, proc.stderr
    assert "no changed files for pre-commit" in proc.stdout

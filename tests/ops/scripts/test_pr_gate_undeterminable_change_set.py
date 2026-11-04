"""Regression guard: an undeterminable change set must not leave a STOP LOOPING receipt.

When the clone lacks the base history, ``resolve_changed_files.sh`` cannot
compute the change set (no merge base). That is a state of the clone, not of
the tree: deepening the clone cures it without moving the tree digest. The gate
used to exit through its trap and write ``.l9/pr/gate-failure.json``, which then
refused every re-run ("FAIL receipt matches unchanged state") even after the
deepen, until the receipt was deleted by hand (observed 2026-11-03 publishing
Cursor-Governance #813 from an agent worktree).

The resolver now exits 3 for that case and the gate blocks publication without a
receipt. A branch with no history in common with ``origin/main`` reproduces the
condition in a full (non-shallow) clone, so the deepen retry cannot mask it.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GATE = ROOT / "ops" / "scripts" / "run_pr_gate.sh"
RESOLVER = ROOT / "ops" / "scripts" / "resolve_changed_files.sh"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _unrelated_branch_workspace(tmp_path: Path) -> Path:
    origin = tmp_path / "acme" / "site.git"
    origin.parent.mkdir()
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
    repo = tmp_path / "work"
    subprocess.run(
        ["git", "clone", "-q", f"file://{origin}", str(repo)], check=True, capture_output=True
    )
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "test")
    (repo / ".gitignore").write_text(".l9/\n", encoding="utf-8")
    (repo / "base.txt").write_text("base\n", encoding="utf-8")
    _git(repo, "add", ".gitignore", "base.txt")
    _git(repo, "commit", "-qm", "init")
    _git(repo, "branch", "-M", "main")
    _git(repo, "push", "-q", "origin", "main")
    # A branch sharing no ancestor with origin/main: merge-base fails outright.
    _git(repo, "checkout", "-q", "--orphan", "feat")
    (repo / "feature.txt").write_text("feature\n", encoding="utf-8")
    _git(repo, "add", ".gitignore", "feature.txt")
    _git(repo, "commit", "-qm", "unrelated history")
    return repo


def _gate(repo: Path) -> subprocess.CompletedProcess[str]:
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in {"PR_OVERLAP", "PR_OVERLAP_TELEMETRY", "PR_STACK", "PR_REMEDIATE"}
    }
    env.update(
        {
            "WS": str(repo),
            "PR_BASE": "origin/main",
            "L9_AUTONOMY_ENABLED": "1",
            "PR_LOCK_WAIT_S": "1",
        }
    )
    return subprocess.run(
        ["bash", str(GATE)],
        cwd=str(repo),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_resolver_exits_3_when_the_change_set_is_undeterminable(tmp_path: Path) -> None:
    repo = _unrelated_branch_workspace(tmp_path)
    result = subprocess.run(
        ["bash", str(RESOLVER)],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PR_BASE": "origin/main", "WS": str(repo), "PR_ALLOW_EMPTY": "1"},
    )
    assert result.returncode == 3, result.stdout + result.stderr
    assert "no merge base" in result.stderr


def test_undeterminable_change_set_blocks_without_a_stop_looping_receipt(tmp_path: Path) -> None:
    repo = _unrelated_branch_workspace(tmp_path)
    failure = repo / ".l9" / "pr" / "gate-failure.json"

    first = _gate(repo)
    out = first.stdout + first.stderr
    assert first.returncode != 0, out
    assert "change set undeterminable" in out, out
    assert "no STOP LOOPING receipt written" in out, out
    assert not failure.exists(), "an environment block latched a STOP LOOPING receipt"

    # The re-run the message asks for reaches the resolver again instead of
    # being refused by a receipt for an unchanged tree.
    second = _gate(repo)
    out2 = second.stdout + second.stderr
    assert "receipt matches unchanged state" not in out2, out2
    assert "change set undeterminable" in out2, out2

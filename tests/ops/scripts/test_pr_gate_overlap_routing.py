"""Regression guard: an early-overlap block must not leave a STOP LOOPING receipt.

``.l9/pr/gate-failure.json`` keys on paths_digest + content_digest + pr_base +
head_sha, and refuses the next ``make pr`` while those are unchanged. That is
right for a red tree. An overlap block is not one: it is routing state about the
base and other open PRs, and the options the block itself prints --
``PR_STACK=auto``, ``PR_BASE=origin/<open-pr-head>``, ``PR_OVERLAP=ignore`` -- do
not move the tree digest. With a receipt written, every one of them was refused
("FAIL receipt matches unchanged state") and the receipt had to be deleted by
hand (Quantum-L9/Website-Bot, 2026-10-24).

The end-to-end test runs the real gate and the real ``pr_overlap_check.py``
against a local bare origin. A fake ``gh`` on PATH reports one open PR whose
head (served from the origin as ``refs/pull/7/head``) edits the same line, so
the merge-tree probe finds a real conflict.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GATE = ROOT / "ops" / "scripts" / "run_pr_gate.sh"

_FAKE_GH = """#!/bin/sh
[ "$1" = "--version" ] && { echo "gh fake"; exit 0; }
case "$2" in
  *pulls/7/files*)
    [ -n "${FAKE_GH_FILES_FAIL:-}" ] && exit 1
    case "$2" in *page=1) echo shared.txt ;; esac ;;
  *pulls\\?state=open*) case "$2" in *page=1) printf '7\\tother\\tmain\\n' ;; esac ;;
esac
exit 0
"""


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _overlapping_workspace(tmp_path: Path) -> tuple[Path, Path]:
    """A feature branch whose only change conflicts with open PR #7."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(_FAKE_GH, encoding="utf-8")
    gh.chmod(0o755)

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
    (repo / "shared.txt").write_text("base\n", encoding="utf-8")
    _git(repo, "add", ".gitignore", "shared.txt")
    _git(repo, "commit", "-qm", "init")
    _git(repo, "branch", "-M", "main")
    _git(repo, "push", "-q", "origin", "main")

    _git(repo, "checkout", "-qb", "other")
    (repo / "shared.txt").write_text("theirs\n", encoding="utf-8")
    _git(repo, "commit", "-qam", "open PR #7")
    _git(repo, "push", "-q", "origin", "other:refs/pull/7/head")

    _git(repo, "checkout", "-q", "main")
    _git(repo, "checkout", "-qb", "feat")
    (repo / "shared.txt").write_text("ours\n", encoding="utf-8")
    _git(repo, "commit", "-qam", "this branch")
    return repo, bin_dir


def _gate(repo: Path, bin_dir: Path, **extra: str) -> subprocess.CompletedProcess[str]:
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in {"PR_OVERLAP", "PR_OVERLAP_TELEMETRY", "PR_STACK", "PR_REMEDIATE"}
    }
    env.update(
        {
            "PATH": f"{bin_dir}{os.pathsep}{env.get('PATH', '')}",
            "WS": str(repo),
            "PR_BASE": "origin/main",
            "PR_EARLY_OVERLAP": "1",
            "L9_AUTONOMY_ENABLED": "1",
            "PR_LOCK_WAIT_S": "1",
            **extra,
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


def test_overlap_block_writes_no_receipt_and_ignore_rerun_reaches_full_gate(
    tmp_path: Path,
) -> None:
    repo, bin_dir = _overlapping_workspace(tmp_path)
    failure = repo / ".l9" / "pr" / "gate-failure.json"

    blocked = _gate(repo, bin_dir)
    out = blocked.stdout + blocked.stderr
    assert blocked.returncode == 1, out
    assert "BLOCK: PR overlap" in out
    assert "routing decision, not a red tree" in out
    assert "no STOP LOOPING receipt written" in out
    assert not failure.exists(), failure.read_text(encoding="utf-8")

    rerun = _gate(repo, bin_dir, PR_OVERLAP="ignore")
    out = rerun.stdout + rerun.stderr
    assert rerun.returncode != 2, out
    assert "STOP LOOPING" not in out
    assert "PR_OVERLAP=ignore — overlap gate skipped" in out
    assert "=== reader wave" in out


def test_own_base_conflict_writes_stop_looping_receipt(tmp_path: Path) -> None:
    """A conflict with the branch's own base is a red tree, not a routing choice.

    ``pr_overlap_check.py`` returns 1 and tells the caller to refresh and
    resolve. That changes the tree digest, so the STOP LOOPING receipt must be
    written and an unchanged re-run must be refused. Open-PR overlap stays
    receipt-free (see the sibling test).
    """
    repo, bin_dir = _overlapping_workspace(tmp_path)
    _git(repo, "checkout", "-q", "main")
    (repo / "shared.txt").write_text("landed\n", encoding="utf-8")
    _git(repo, "commit", "-qam", "landed on main")
    _git(repo, "push", "-q", "origin", "main")
    _git(repo, "checkout", "-q", "feat")
    failure = repo / ".l9" / "pr" / "gate-failure.json"

    blocked = _gate(repo, bin_dir)
    out = blocked.stdout + blocked.stderr
    assert blocked.returncode == 1, out
    assert "conflicts with its own base" in out
    assert "red tree; STOP LOOPING receipt applies" in out
    assert "no STOP LOOPING receipt written" not in out
    assert failure.is_file(), out

    rerun = _gate(repo, bin_dir)
    out = rerun.stdout + rerun.stderr
    assert rerun.returncode == 2, out
    assert "STOP LOOPING" in out
    assert "=== reader wave" not in out


def test_telemetry_denial_after_warned_base_conflict_writes_no_receipt(tmp_path: Path) -> None:
    """Exit 3 wins over the own-base text a PR_OVERLAP=warn run already printed.

    Under ``warn`` the base probe prints "conflicts with its own base" and
    continues; a later open-PR file-list failure then denies on telemetry (3).
    That is an outage, not a red tree, so no receipt may be written.
    """
    repo, bin_dir = _overlapping_workspace(tmp_path)
    _git(repo, "checkout", "-q", "main")
    (repo / "shared.txt").write_text("landed\n", encoding="utf-8")
    _git(repo, "commit", "-qam", "landed on main")
    _git(repo, "push", "-q", "origin", "main")
    _git(repo, "checkout", "-q", "feat")
    failure = repo / ".l9" / "pr" / "gate-failure.json"

    blocked = _gate(repo, bin_dir, PR_OVERLAP="warn", FAKE_GH_FILES_FAIL="1")
    out = blocked.stdout + blocked.stderr
    assert blocked.returncode == 1, out
    assert "conflicts with its own base" in out
    assert "telemetry unavailable, not a red tree" in out
    assert "no STOP LOOPING receipt written" in out
    assert not failure.exists(), failure.read_text(encoding="utf-8")


def test_receipt_suppression_is_confined_to_fetch_and_overlap() -> None:
    """A genuine red-tree failure must still write the STOP LOOPING receipt.

    Only the base fetch and the early overlap stage may set ``_gate_env_block``;
    every later stage (reader wave, pytest, security) exits through the trap
    with the receipt intact.
    """
    gate = GATE.read_text(encoding="utf-8")
    overlap_at = gate.index("--- early overlap")
    wave_at = gate.index("=== reader wave")
    sets = [i for i in range(len(gate)) if gate.startswith("_gate_env_block=1", i)]
    assert sets
    assert all(i < wave_at for i in sets)
    overlap_block = gate[overlap_at:wave_at]
    assert "_gate_env_block=1" in overlap_block
    assert '[[ "$_overlap_rc" -eq 3 ]] && _gate_env_block=1' not in gate
    assert 'python3 "$_GATE_FAILURE_PY" write "$_GATE_FAILURE"' in gate

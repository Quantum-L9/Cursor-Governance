"""Conformance: a linked worktree of a shallow clone deepens before failing closed.

`$(git rev-parse --git-dir)/shallow` names `.git/worktrees/<name>/shallow` in a linked
worktree, which never exists: the shallow file lives in the common dir. The resolver
skipped its --deepen retry and reported "no merge base" from every agent worktree
(agent_worktree_start.sh) once the depth-1 base advanced.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
RESOLVER = REPO_ROOT / "ops" / "scripts" / "resolve_changed_files.sh"


def git(*args: str, cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=check)


def run_resolver(cwd: Path, base: str = "origin/main") -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(RESOLVER)],
        cwd=cwd,
        capture_output=True,
        text=True,
        env={
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "HOME": str(cwd),
            "PR_ALLOW_EMPTY": "1",
            "PR_BASE": base,
            "WS": str(cwd),
        },
        check=False,
        timeout=120,
    )


def _commit(repo: Path, name: str) -> None:
    (repo / name).write_text(f"{name}\n", encoding="utf-8")
    git("add", "--", name, cwd=repo)
    git("-c", "user.email=t@e", "-c", "user.name=t", "commit", "-qm", name, cwd=repo)


def test_shallow_worktree_deepens_before_failing(tmp_path: Path) -> None:
    """A linked worktree of a shallow clone must take the deepen path too.

    `$(git rev-parse --git-dir)/shallow` names `.git/worktrees/<name>/shallow` in a
    linked worktree, which never exists: the shallow file lives in the common dir.
    The resolver skipped the deepen and reported "no merge base" on an ordinary
    feature branch whose base had advanced by one commit (observed 2026-11-03 on
    Cursor-Governance #818, publishing from an agent worktree).
    """
    upstream = tmp_path / "upstream"
    upstream.mkdir()
    git("init", "-q", "-b", "main", ".", cwd=upstream)
    for name in ("c1", "c2", "c3"):
        _commit(upstream, name)

    clone = tmp_path / "clone"
    git("clone", "-q", "--depth", "1", f"file://{upstream}", str(clone), cwd=tmp_path)
    worktree = tmp_path / "wt"
    git("worktree", "add", "-q", "-b", "feature", str(worktree), "origin/main", cwd=clone)
    _commit(worktree, "f1")

    _commit(upstream, "c4")
    _commit(upstream, "c5")
    git("fetch", "-q", "--depth", "1", "origin", "main", cwd=clone)
    assert git("merge-base", "origin/main", "HEAD", cwd=worktree, check=False).returncode != 0

    result = run_resolver(worktree)
    assert result.returncode == 0, result.stderr
    assert "f1" in result.stdout.split()

#!/usr/bin/env python3
"""Commit valuable leftover dirt with explicit pathspecs. Never git add -A.

Runs inside an already-prepared worktree (same-repo or other-repo extract).
Does not push. /ff calls this before reconcile + make pr.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def _run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def commit_valuable_dirt(
    worktree: Path,
    paths: list[str],
    *,
    message: str,
    src_root: Path | None = None,
) -> dict[str, str]:
    if not paths:
        return {"committed": "0", "head": _run(worktree, "rev-parse", "HEAD").stdout.strip()}
    src = src_root or worktree
    copied: list[str] = []
    for rel in paths:
        src_path = src / rel
        dst = worktree / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src_path.is_file() or src_path.is_symlink():
            dst.write_bytes(src_path.read_bytes())
            copied.append(rel)
        elif not src_path.exists():
            if (worktree / rel).exists():
                _run(worktree, "rm", "--", rel)
                copied.append(rel)
    if not copied:
        return {"committed": "0", "head": _run(worktree, "rev-parse", "HEAD").stdout.strip()}
    staged = _run(worktree, "add", "--", *copied)
    if staged.returncode != 0:
        raise SystemExit(staged.stderr.strip() or "git add -- <paths> failed")
    porcelain = _run(worktree, "status", "--porcelain")
    if not porcelain.stdout.strip():
        return {"committed": "0", "head": _run(worktree, "rev-parse", "HEAD").stdout.strip()}
    committed = _run(worktree, "commit", "-m", message)
    if committed.returncode != 0:
        raise SystemExit(committed.stderr.strip() or "git commit failed")
    return {
        "committed": "1",
        "head": _run(worktree, "rev-parse", "HEAD").stdout.strip(),
        "paths": ",".join(copied),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worktree", required=True)
    parser.add_argument("--src", default="")
    parser.add_argument("--message", default="chore(ff): commit valuable leftover dirt")
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args()
    worktree = Path(args.worktree).expanduser().resolve()
    src = Path(args.src).expanduser().resolve() if args.src else worktree
    result = commit_valuable_dirt(worktree, args.paths, message=args.message, src_root=src)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

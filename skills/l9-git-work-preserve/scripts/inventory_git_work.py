#!/usr/bin/env python3
"""Inventory git work: unpushed, dirty, worktrees, orphans, stale, stashes."""

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


def _lines(proc: subprocess.CompletedProcess[str]) -> list[str]:
    if proc.returncode != 0:
        return []
    return [ln for ln in proc.stdout.splitlines() if ln.strip()]


def inventory(repo: Path, baseline: str) -> dict:
    inside = _run(repo, "rev-parse", "--is-inside-work-tree")
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        raise SystemExit(f"not a git work tree: {repo}")

    head = _run(repo, "rev-parse", "HEAD").stdout.strip()
    branch = _run(repo, "branch", "--show-current").stdout.strip()
    porcelain = _lines(_run(repo, "status", "--porcelain"))
    worktrees = _lines(_run(repo, "worktree", "list", "--porcelain"))
    stashes = _lines(_run(repo, "stash", "list"))

    branches: list[dict] = []
    ref_fmt = "%(refname:short)|%(upstream:short)|%(upstream:track)|%(objectname:short)"
    for line in _lines(_run(repo, "for-each-ref", f"--format={ref_fmt}", "refs/heads")):
        parts = line.split("|")
        if len(parts) < 4:
            continue
        name, upstream, track, tip = parts[0], parts[1], parts[2], parts[3]
        ahead = _run(repo, "rev-list", "--count", f"{baseline}..{name}")
        unique = int(ahead.stdout.strip() or "0") if ahead.returncode == 0 else -1
        branches.append(
            {
                "name": name,
                "upstream": upstream or None,
                "track": track or None,
                "tip": tip,
                "ahead_of_baseline": unique,
                "orphan_gone": "gone" in (track or "").lower(),
            }
        )

    unpushed = [
        b
        for b in branches
        if b["ahead_of_baseline"] > 0
        and (not b["upstream"] or "ahead" in (b["track"] or "").lower() or b["orphan_gone"])
    ]

    return {
        "schema": "l9.git_work_preserve.inventory/v1",
        "repo": str(repo.resolve()),
        "baseline": baseline,
        "head": head,
        "branch": branch or None,
        "dirty": bool(porcelain),
        "dirty_paths": porcelain,
        "branches": branches,
        "unpushed_or_diverged": unpushed,
        "worktrees_porcelain": worktrees,
        "stashes": stashes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="Git work tree path")
    parser.add_argument("--baseline", default="origin/main", help="Compare tip")
    parser.add_argument("--json", action="store_true", help="Print JSON (default)")
    args = parser.parse_args()
    repo = Path(args.repo).expanduser().resolve()
    data = inventory(repo, args.baseline)
    print(json.dumps(data, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

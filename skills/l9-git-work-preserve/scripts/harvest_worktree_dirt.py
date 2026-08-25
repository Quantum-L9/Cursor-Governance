#!/usr/bin/env python3
"""Classify dirty/untracked paths across sibling worktrees for harvest.

Report-only. Never copies files, never stages, never deletes a source ref.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any

SCHEMA = "l9.git_work_preserve.harvest/v1"

NOISE_PARTS = {".venv", "node_modules", ".pytest_cache", "__pycache__", ".l9"}
DEFAULT_EXTRA_ROOTS = (
    Path.home() / ".l9" / "gov-worktrees",
    Path.home() / ".l9" / "program-worktrees",
    Path.home() / "Cursor-Governance-worktrees",
)


def _run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def _is_worktree(path: Path) -> bool:
    return path.is_dir() and ((path / ".git").exists() or (path / ".git").is_file())


def porcelain_path(line: str) -> str:
    raw = line[3:] if len(line) >= 3 else line
    raw = raw.strip().strip('"')
    if " -> " in raw:
        raw = raw.split(" -> ", 1)[1]
    return raw.replace("\\", "/")


def is_skip_noise(rel: str) -> bool:
    parts = rel.replace("\\", "/").split("/")
    if any(part in NOISE_PARTS for part in parts):
        return True
    return rel.endswith(".pyc")


def is_wiring_noise(rel: str) -> bool:
    rel = rel.replace("\\", "/")
    if rel == ".claude/skills" or rel.startswith(".claude/skills/"):
        return True
    if rel == ".claude/rules" or rel.startswith(".claude/rules"):
        return True
    return False


def remote_url(repo: Path) -> str:
    proc = _run(repo, "remote", "get-url", "origin")
    return proc.stdout.strip() if proc.returncode == 0 else ""


def discover_worktrees(repo: Path, extra_roots: list[Path]) -> list[Path]:
    found: list[Path] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        if not _is_worktree(path):
            return
        key = str(path.resolve())
        if key in seen:
            return
        seen.add(key)
        found.append(path.resolve())

    add(repo)
    proc = _run(repo, "worktree", "list", "--porcelain")
    for line in proc.stdout.splitlines():
        if line.startswith("worktree "):
            add(Path(line.split(" ", 1)[1]))

    for root in extra_roots:
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir()):
            add(child)
    return found


def path_on_baseline(repo: Path, baseline: str, rel: str) -> bool:
    proc = _run(repo, "cat-file", "-e", f"{baseline}:{rel}")
    return proc.returncode == 0


def classify_path(
    rel: str,
    *,
    repo: Path,
    baseline: str,
    include_wip: bool,
    refuse_shared: bool,
) -> str:
    if is_skip_noise(rel):
        return "skip_noise"
    if is_wiring_noise(rel):
        return "wiring_noise"
    if refuse_shared:
        return "refuse_foreign_shared"
    if path_on_baseline(repo, baseline, rel):
        return "already_on_baseline"
    if rel == "WIP" or rel.startswith("WIP/"):
        return "unique_wip" if include_wip else "skip_wip"
    if rel.startswith("docs/plans/"):
        return "unique_plans"
    return "unique_product"


def inspect_worktree(
    wt: Path,
    *,
    baseline: str,
    include_wip: bool,
    extra_root_resolved: set[str],
) -> dict[str, Any]:
    branch = _run(wt, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    sha = _run(wt, "rev-parse", "--short", "HEAD").stdout.strip()
    behind_proc = _run(wt, "rev-list", "--count", f"HEAD..{baseline}")
    behind = int(behind_proc.stdout.strip() or "0") if behind_proc.returncode == 0 else -1
    porcelain = [
        ln
        for ln in _run(wt, "status", "--porcelain=v1", "--untracked-files=all").stdout.splitlines()
        if ln
    ]

    resolved = str(wt.resolve())
    under_extra = any(
        resolved == root or resolved.startswith(root + os.sep) for root in extra_root_resolved
    )
    refuse_shared = (not under_extra) and branch in {"main", "master"} and bool(porcelain)

    paths: list[dict[str, str]] = []
    dirty_tracked = False
    for line in porcelain:
        rel = porcelain_path(line)
        if not rel:
            continue
        status = line[:2]
        if status.strip() and "?" not in status:
            dirty_tracked = True
        klass = classify_path(
            rel,
            repo=wt,
            baseline=baseline,
            include_wip=include_wip,
            refuse_shared=refuse_shared,
        )
        paths.append({"status": status, "path": rel, "class": klass})

    return {
        "worktree": resolved,
        "branch": branch or None,
        "sha": sha or None,
        "behind_baseline": behind,
        "stale_apply_risk": behind > 0 and dirty_tracked,
        "refuse_foreign_shared": refuse_shared,
        "dirty_count": len(paths),
        "paths": paths,
    }


def harvest_plan(
    repo: Path,
    *,
    baseline: str,
    extra_roots: list[Path],
    include_wip: bool,
    same_remote_only: bool,
) -> dict[str, Any]:
    origin = remote_url(repo)
    extra_resolved = {str(p.resolve()) for p in extra_roots if p.exists()}
    worktrees: list[dict[str, Any]] = []
    for wt in discover_worktrees(repo, extra_roots):
        if same_remote_only and origin:
            other = remote_url(wt)
            if other and other != origin:
                continue
        worktrees.append(
            inspect_worktree(
                wt,
                baseline=baseline,
                include_wip=include_wip,
                extra_root_resolved=extra_resolved,
            )
        )

    harvestable: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    for wt in worktrees:
        for item in wt["paths"]:
            row = {
                "worktree": wt["worktree"],
                "branch": wt.get("branch") or "",
                "path": item["path"],
                "class": item["class"],
            }
            if item["class"].startswith("unique_"):
                harvestable.append(row)
            elif item["class"] != "skip_noise":
                skipped.append(row)

    return {
        "schema": SCHEMA,
        "mode": "harvest",
        "repo": str(repo.resolve()),
        "baseline": baseline,
        "include_wip": include_wip,
        "worktrees": worktrees,
        "harvestable": harvestable,
        "skipped": skipped,
        "counts": {
            "worktrees": len(worktrees),
            "harvestable": len(harvestable),
            "skipped": len(skipped),
        },
    }


def default_extra_roots() -> list[Path]:
    env = os.environ.get("L9_HARVEST_EXTRA_ROOTS", "").strip()
    if env:
        return [Path(p).expanduser() for p in env.split(os.pathsep) if p.strip()]
    return [p for p in DEFAULT_EXTRA_ROOTS]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="Anchor git work tree")
    parser.add_argument("--baseline", default="origin/main", help="Compare paths to this ref")
    parser.add_argument(
        "--extra-root",
        action="append",
        default=[],
        help="Directory of sibling worktrees (repeatable)",
    )
    parser.add_argument("--include-wip", action="store_true", default=True)
    parser.add_argument("--exclude-wip", action="store_true", help="Do not harvest WIP/")
    parser.add_argument(
        "--allow-other-remotes",
        action="store_true",
        help="Include worktrees whose origin URL differs",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON (default)")
    args = parser.parse_args()
    repo = Path(args.repo).expanduser().resolve()
    extras = (
        [Path(p).expanduser() for p in args.extra_root]
        if args.extra_root
        else default_extra_roots()
    )
    data = harvest_plan(
        repo,
        baseline=args.baseline,
        extra_roots=extras,
        include_wip=not args.exclude_wip,
        same_remote_only=not args.allow_other_remotes,
    )
    print(json.dumps(data, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

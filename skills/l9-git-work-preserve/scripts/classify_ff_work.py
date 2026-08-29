#!/usr/bin/env python3
"""Classify leftover /ff work: superseded vs valuable, and destination repo.

Does not commit, push, or reset. Used by /ff before any publish.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

SCHEMA = "l9.git_work_preserve.ff_classify/v1"


def _gov_root() -> Path:
    for key in ("FF_GOV_ROOT", "CURSOR_GOVERNANCE_DIR"):
        raw = os.environ.get(key, "").strip()
        if raw:
            return Path(raw).expanduser().resolve()
    return Path(__file__).resolve().parents[3]


def _load_workspace_clean():
    scripts = _gov_root() / "ops" / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import workspace_clean as wc  # noqa: PLC0415

    return wc


def _run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def _blob_at(repo: Path, spec: str) -> str:
    proc = _run(repo, "rev-parse", spec)
    return proc.stdout.strip() if proc.returncode == 0 else ""


def _wt_blob(repo: Path, rel: str) -> str:
    path = repo / rel
    if not path.exists() and not path.is_symlink():
        return ""
    proc = _run(repo, "hash-object", "--", rel)
    return proc.stdout.strip() if proc.returncode == 0 else ""


def _porcelain_paths(repo: Path) -> list[tuple[str, str]]:
    wc = _load_workspace_clean()
    rows: list[tuple[str, str]] = []
    for line in _run(repo, "status", "--porcelain").stdout.splitlines():
        if not line.strip():
            continue
        rel = wc.porcelain_path(line)
        rows.append((line[:2].strip(), rel))
    return rows


def _commit_paths(repo: Path, sha: str) -> list[str]:
    proc = _run(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", sha)
    return [ln for ln in proc.stdout.splitlines() if ln.strip()]


def _cherry_superseded(repo: Path, sha: str, baseline: str) -> bool:
    if _run(repo, "merge-base", "--is-ancestor", sha, baseline).returncode == 0:
        return True
    proc = _run(repo, "cherry", baseline, sha)
    for line in proc.stdout.splitlines():
        if not line.startswith("-"):
            continue
        listed = line[1:].strip()
        if sha.startswith(listed) or listed.startswith(sha):
            return True
    return False


def classify_ff_work(
    repo: Path,
    *,
    baseline: str = "origin/main",
    routing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    wc = _load_workspace_clean()
    routing = routing if routing is not None else wc.load_routing(_gov_root())
    current_dest = wc.current_destination(repo, routing)
    tracked = set(_run(repo, "ls-files").stdout.splitlines())

    dirt: list[dict[str, str]] = []
    for porcelain, rel in _porcelain_paths(repo):
        is_tracked = rel in tracked or porcelain not in {"??", "!!"}
        verdict = wc.classify_path(
            rel, routing=routing, current_dest=current_dest, tracked=is_tracked
        )
        origin_blob = _blob_at(repo, f"{baseline}:{rel}")
        wt_blob = _wt_blob(repo, rel)
        if verdict["action"] == "skip":
            status = "skip"
        elif origin_blob and wt_blob and origin_blob == wt_blob:
            status = "superseded"
        elif verdict["action"] == "ambiguous":
            status = "ambiguous"
        else:
            status = "valuable"
        dest = verdict.get("dest") or ""
        if status == "valuable" and dest and current_dest and dest != current_dest:
            owner = "other_repo"
        elif status == "valuable":
            owner = "current_repo"
        else:
            owner = dest or current_dest or ""
        dirt.append(
            {
                "path": rel,
                "porcelain": porcelain,
                "status": status,
                "dest": dest or (current_dest or ""),
                "owner": owner,
                "reason": verdict.get("reason") or status,
            }
        )

    novel: list[dict[str, Any]] = []
    listed = _run(repo, "rev-list", "--reverse", "HEAD", "--not", "--remotes=origin")
    for sha in [ln.strip() for ln in listed.stdout.splitlines() if ln.strip()]:
        paths = _commit_paths(repo, sha)
        dests: list[str] = []
        for rel in paths:
            is_tracked = True
            verdict = wc.classify_path(
                rel, routing=routing, current_dest=current_dest, tracked=is_tracked
            )
            dest = verdict.get("dest") or current_dest or ""
            if dest and dest not in dests:
                dests.append(dest)
        if _cherry_superseded(repo, sha, baseline):
            status = "superseded"
        elif len(dests) > 1 and current_dest and any(d != current_dest for d in dests):
            status = "mixed_dest"
        elif dests and current_dest and dests != [current_dest]:
            status = "other_repo"
        else:
            status = "valuable"
        subject = _run(repo, "log", "-1", "--format=%s", sha).stdout.strip()
        novel.append(
            {
                "sha": sha,
                "subject": subject,
                "paths": paths,
                "dests": dests,
                "status": status,
                "dest": dests[0] if len(dests) == 1 else (current_dest or ""),
            }
        )

    blocked = any(row["status"] == "ambiguous" for row in dirt) or any(
        row["status"] == "mixed_dest" for row in novel
    )
    return {
        "schema": SCHEMA,
        "repo": str(repo.resolve()),
        "baseline": baseline,
        "current_dest": current_dest,
        "dirt": dirt,
        "novel_commits": novel,
        "valuable_dirt": [row for row in dirt if row["status"] == "valuable"],
        "valuable_novel": [row for row in novel if row["status"] == "valuable"],
        "other_repo_dirt": [row for row in dirt if row["owner"] == "other_repo"],
        "other_repo_novel": [row for row in novel if row["status"] == "other_repo"],
        "blocked": blocked,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--baseline", default="origin/main")
    args = parser.parse_args()
    repo = Path(args.repo).expanduser().resolve()
    print(json.dumps(classify_ff_work(repo, baseline=args.baseline), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

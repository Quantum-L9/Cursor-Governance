#!/usr/bin/env python3
"""Diagnose unique value of a ref vs baseline (default origin/main)."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path


def _run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def diagnose(repo: Path, ref: str, baseline: str) -> dict:
    tip = _run(repo, "rev-parse", ref)
    if tip.returncode != 0:
        raise SystemExit(f"cannot resolve ref {ref}: {tip.stderr.strip()}")
    tip_sha = tip.stdout.strip()

    log = _run(repo, "log", "--oneline", f"{baseline}..{ref}")
    commits = [ln for ln in log.stdout.splitlines() if ln.strip()] if log.returncode == 0 else []
    diff = _run(repo, "diff", "--name-only", f"{baseline}...{ref}")
    paths = [ln for ln in diff.stdout.splitlines() if ln.strip()] if diff.returncode == 0 else []

    unique_commits = len(commits)
    if unique_commits == 0 and not paths:
        classification, confidence = "prune_candidate", "high"
    elif unique_commits == 0 and paths:
        classification, confidence = "extract", "medium"
    elif unique_commits > 0:
        classification, confidence = "keep_push", "high"
    else:
        classification, confidence = "unknown", "unknown"

    body = {
        "receipt_id": hashlib.sha256(f"{repo}|{ref}|{tip_sha}".encode()).hexdigest()[:16],
        "mode": "diagnose-value",
        "repo": str(repo.resolve()),
        "created_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "baseline_ref": baseline,
        "ref": ref,
        "tip_sha": tip_sha,
        "classification": classification,
        "confidence": confidence,
        "unique_commits": unique_commits,
        "unique_paths": paths,
        "commit_subjects": commits[:50],
        "rollback": f"git checkout {tip_sha}  # or reflog",
    }
    return body


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="Git work tree")
    parser.add_argument("--ref", required=True, help="Branch or commit to diagnose")
    parser.add_argument("--baseline", default="origin/main")
    args = parser.parse_args()
    repo = Path(args.repo).expanduser().resolve()
    print(json.dumps(diagnose(repo, args.ref, args.baseline), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

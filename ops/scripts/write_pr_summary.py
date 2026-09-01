#!/usr/bin/env python3
"""Record what a publish actually shipped, as a receipt.

`make pr` already knows every fact a reader needs — PR number, base, head, the
changed files and their line deltas — and then prints only `Opened: <url>`. The
rest lived in the agent's head, so whether a session reported it was a matter of
whether the agent remembered to. This receipt makes the facts durable at the one
place that knows a PR was opened, so a consumer can render them without
re-deriving anything, and so "the publish reported nothing" becomes a missing
file rather than a silent omission.

Written by ops/scripts/open_pr_after_gate.sh after the PR number is resolved —
both the freshly-opened and already-open paths converge there. Read by
environment/agents/adapters/claude-code/hooks/pr_summary_posttool.py.

Degradation is explicit, never silent: when the GitHub API cannot be reached the
file list falls back to the local three-dot diff and `source` records which one
produced it. A summary that quietly described a different set of files than the
PR carries would be worse than none.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

SCHEMA = "l9.pr_summary.v1"
RECEIPT_REL = Path(".l9/pr/pr-summary.json")
#: GitHub caps a page at 100; a publish larger than this is truncated rather
#: than paginated forever, and `files_truncated` says so.
MAX_FILE_PAGES = 10
PAGE_SIZE = 100


def _run(args: list[str], cwd: Path | None = None) -> tuple[int, str]:
    proc = subprocess.run(  # noqa: S603
        args,
        capture_output=True,
        text=True,
        check=False,
        cwd=str(cwd) if cwd else None,
    )
    return proc.returncode, proc.stdout


def _gh_json(endpoint: str) -> Any | None:
    rc, out = _run(["gh", "api", endpoint])
    if rc != 0 or not out.strip():
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return None


def _api_files(repo: str, number: int) -> tuple[list[dict[str, Any]], bool]:
    """Changed files from the API, with the PR's own status and line deltas."""
    files: list[dict[str, Any]] = []
    for page in range(1, MAX_FILE_PAGES + 1):
        rows = _gh_json(f"repos/{repo}/pulls/{number}/files?per_page={PAGE_SIZE}&page={page}")
        if not isinstance(rows, list) or not rows:
            break
        for row in rows:
            if not isinstance(row, dict):
                continue
            files.append(
                {
                    "path": row.get("filename"),
                    "status": row.get("status"),
                    "additions": row.get("additions"),
                    "deletions": row.get("deletions"),
                    "previous_path": row.get("previous_filename"),
                }
            )
        if len(rows) < PAGE_SIZE:
            return files, False
    return files, True


def _git_files(workspace: Path, base: str) -> list[dict[str, Any]]:
    """Local fallback: three-dot diff, so it matches what the PR would show."""
    rc, out = _run(["git", "diff", "--name-status", "-M", f"{base}...HEAD"], cwd=workspace)
    if rc != 0:
        return []
    files: list[dict[str, Any]] = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        code = parts[0].strip()
        previous = parts[1] if len(parts) > 2 else None
        path = parts[2] if len(parts) > 2 else parts[1]
        files.append(
            {
                "path": path,
                "status": code[:1].lower(),
                "additions": None,
                "deletions": None,
                "previous_path": previous if len(parts) > 2 else None,
            }
        )
    return files


def build_summary(
    *,
    workspace: Path,
    repo: str,
    number: int,
    base: str,
    branch: str,
    url: str,
    head_sha: str,
) -> dict[str, Any]:
    meta = _gh_json(f"repos/{repo}/pulls/{number}")
    files, truncated = ([], False) if meta is None else _api_files(repo, number)
    source = "github_api"
    if not files:
        files = _git_files(workspace, base)
        source = "local_diff" if files else "unavailable"

    additions = sum(f["additions"] or 0 for f in files)
    deletions = sum(f["deletions"] or 0 for f in files)
    return {
        "schema": SCHEMA,
        "repo": repo,
        "number": number,
        "url": url or (meta or {}).get("html_url", ""),
        "title": (meta or {}).get("title", ""),
        "state": (meta or {}).get("state", ""),
        "base": (meta or {}).get("base", {}).get("ref") or base,
        "head": (meta or {}).get("head", {}).get("ref") or branch,
        "head_sha": head_sha,
        "commits": (meta or {}).get("commits"),
        "changed_files": (meta or {}).get("changed_files", len(files)),
        "additions": (meta or {}).get("additions", additions),
        "deletions": (meta or {}).get("deletions", deletions),
        "files": files,
        "files_truncated": truncated,
        "source": source,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--repo", required=True, help="owner/name")
    parser.add_argument("--number", type=int, required=True)
    parser.add_argument("--base", default="")
    parser.add_argument("--branch", default="")
    parser.add_argument("--url", default="")
    parser.add_argument("--head-sha", default="")
    args = parser.parse_args()

    summary = build_summary(
        workspace=args.workspace,
        repo=args.repo,
        number=args.number,
        base=args.base,
        branch=args.branch,
        url=args.url,
        head_sha=args.head_sha,
    )
    target = args.workspace / RECEIPT_REL
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"pr summary receipt written: {target} ({summary['source']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

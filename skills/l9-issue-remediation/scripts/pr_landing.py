#!/usr/bin/env python3
"""Decide where an issue fix lands: matching open PR, else stacked on newest.

make_pr:true means the fix is on a GitHub PR — not always a fresh `make pr`.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime

FIXES_RE = re.compile(r"(?i)\b(?:fixes|closes|resolves)\s+#(\d+)\b")
REPO_FIXES_RE = re.compile(
    r"(?i)\b(?:fixes|closes|resolves)\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)#(\d+)\b"
)


def _issue_number(issue_id: str) -> str:
    if "#" not in issue_id:
        return ""
    return issue_id.rsplit("#", 1)[-1]


def _repo(issue_id: str) -> str:
    if "#" not in issue_id:
        return ""
    return issue_id.rsplit("#", 1)[0]


def pr_matches_issue(pr: dict, issue_id: str, changed_paths: list[str] | None) -> bool:
    body = str(pr.get("body") or "")
    number = _issue_number(issue_id)
    repo = _repo(issue_id).lower()
    if number and f"#{number}" in body:
        if FIXES_RE.search(body) or issue_id.lower() in body.lower():
            return True
    for match in REPO_FIXES_RE.finditer(body):
        if match.group(1).lower() == repo and match.group(2) == number:
            return True
    paths = {str(p) for p in (pr.get("files") or []) if p}
    changed = {str(p) for p in (changed_paths or []) if p}
    if paths and changed and paths & changed:
        return True
    return False


def decide_landing(
    issue_id: str,
    open_prs: list[dict],
    changed_paths: list[str] | None = None,
) -> dict:
    """Return landing action for one issue in one owning repo."""
    matches = [pr for pr in open_prs if pr_matches_issue(pr, issue_id, changed_paths)]
    if matches:
        chosen = matches[0]
        return {
            "action": "push_existing",
            "pr": chosen.get("number"),
            "url": chosen.get("url") or chosen.get("html_url"),
            "head": chosen.get("headRefName") or chosen.get("head"),
            "make_pr": False,
            "reason": "fix belongs on existing open PR",
        }
    if open_prs:
        newest = max(
            open_prs,
            key=lambda pr: str(pr.get("createdAt") or pr.get("created_at") or ""),
        )
        return {
            "action": "stack_new",
            "base_pr": newest.get("number"),
            "base": newest.get("headRefName") or newest.get("head"),
            "pr_stack": "auto",
            "make_pr": True,
            "reason": "new stacked PR on newest open PR",
        }
    return {
        "action": "first_pr",
        "base": "origin/main",
        "pr_stack": "",
        "make_pr": True,
        "reason": "no open PRs; first PR against origin/main",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issue", required=True, help="owner/repo#number")
    parser.add_argument(
        "--open-prs-json",
        help="JSON list of open PRs (number, body, files, createdAt, url, headRefName)",
    )
    parser.add_argument("--changed-path", action="append", default=[])
    args = parser.parse_args()
    open_prs: list[dict] = []
    if args.open_prs_json:
        raw = json.loads(args.open_prs_json)
        if not isinstance(raw, list):
            raise SystemExit("BLOCKED: --open-prs-json must be a JSON list")
        open_prs = [row for row in raw if isinstance(row, dict)]
    decision = decide_landing(args.issue, open_prs, args.changed_path)
    decision["generated_at"] = datetime.now(UTC).isoformat()
    decision["issue"] = args.issue
    print(json.dumps(decision))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

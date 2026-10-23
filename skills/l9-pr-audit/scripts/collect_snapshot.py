#!/usr/bin/env python3
"""Collect read-only census snapshots for build_change_ledger.py from GitHub + a local clone.

Freezes the PR set at collection time and writes, per PR, the snapshot shape documented in
build_change_ledger.py plus the binding facts the audit needs (base/head refs, check runs,
review threads, approvals, PR body). It also writes ``frozen-pr-set.json`` with stack edges
(a PR whose base branch is another open PR's head branch) so semantic lanes can be grouped.

GitHub is read over REST only (``gh api --method GET``); review threads use the
``ccr/review_threads`` route, which works where GraphQL is refused. The only local write is
fetching ``refs/pull/<n>/head`` into ``refs/remotes/origin/pr/<n>`` of the given clone.

Usage:
  collect_snapshot.py --repo OWNER/NAME --clone PATH --out DIR [--pr N ...]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

MAX_CONTENT_BYTES = 400_000
MAX_ISSUE_BODY = 8_000
# GitHub's closing keywords, same-repository references only ("Closes #12").
CLOSING_REF = re.compile(
    r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s*:?\s+#(\d+)\b", re.IGNORECASE
)
FAILED_CONCLUSIONS = {"failure", "timed_out", "cancelled", "action_required", "startup_failure"}


def gh(path: str) -> Any:
    out = subprocess.run(
        ["gh", "api", "--method", "GET", "--paginate", "--slurp", path],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    pages = json.loads(out)
    if pages and isinstance(pages[0], list):
        return [item for page in pages for item in page]
    if len(pages) == 1:
        return pages[0]
    merged: dict[str, Any] = {}
    for page in pages:
        for key, value in page.items():
            if isinstance(value, list):
                merged.setdefault(key, []).extend(value)
            else:
                merged[key] = value
    return merged


def effective_approvals(reviews: list[dict[str, Any]], head: str) -> list[dict[str, Any]]:
    """Distinct reviewers whose latest state-changing review is an approval of ``head``.

    GitHub counts each reviewer once, by their most recent APPROVED / CHANGES_REQUESTED /
    DISMISSED review; COMMENTED reviews do not change approval state.
    """
    latest: dict[str, dict[str, Any]] = {}
    for review in sorted(reviews, key=lambda r: r.get("submitted_at") or ""):
        if review["state"] in {"APPROVED", "CHANGES_REQUESTED", "DISMISSED"} and review.get("user"):
            latest[review["user"]["login"]] = review
    return [
        {
            "login": login,
            "user_type": r["user"]["type"],
            "commit_id": r["commit_id"],
            "on_head": r["commit_id"] == head,
        }
        for login, r in sorted(latest.items())
        if r["state"] == "APPROVED"
    ]


def linked_issues(repo: str, body: str) -> list[dict[str, Any]]:
    """Issues the PR body closes: the requester's ask, when one was recorded."""
    out = []
    for number in sorted({int(n) for n in CLOSING_REF.findall(body or "")}):
        try:
            issue = gh(f"repos/{repo}/issues/{number}")
        except subprocess.CalledProcessError:
            out.append({"number": number, "state": "UNAVAILABLE", "title": "", "body": ""})
            continue
        if issue.get("pull_request"):
            continue  # a PR reference, not an issue
        out.append(
            {
                "number": number,
                "state": issue["state"],
                "title": issue["title"],
                "body": (issue.get("body") or "")[:MAX_ISSUE_BODY],
            }
        )
    return out


def touched_paths(snap: dict[str, Any]) -> set[str]:
    """Every path a PR changes, including the old side of a rename."""
    out = set()
    for f in snap["files"]:
        out.add(f["path"])
        if f.get("previous_path"):
            out.add(f["previous_path"])
    return out


def git(clone: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", "-C", str(clone), *args], capture_output=True)


def blob(clone: Path, rev: str, path: str) -> str | None:
    result = git(clone, "show", f"{rev}:{path}")
    if result.returncode != 0 or len(result.stdout) > MAX_CONTENT_BYTES:
        return None
    try:
        return result.stdout.decode("utf-8")
    except UnicodeDecodeError:
        return None


def snapshot(repo: str, clone: Path, pr: dict[str, Any]) -> dict[str, Any]:
    n = pr["number"]
    head, base_tip = pr["head"]["sha"], pr["base"]["sha"]
    merge_base = git(clone, "merge-base", base_tip, head).stdout.decode().strip() or base_tip
    files = []
    for f in gh(f"repos/{repo}/pulls/{n}/files?per_page=100"):
        path = f["filename"]
        previous = f.get("previous_filename") or path
        status = "deleted" if f["status"] == "removed" else f["status"]
        files.append(
            {
                "path": path,
                "previous_path": f.get("previous_filename"),
                "status": status,
                "additions": f["additions"],
                "deletions": f["deletions"],
                "patch": f.get("patch", ""),
                "base_content": None if status == "added" else blob(clone, merge_base, previous),
                "head_content": None if status == "deleted" else blob(clone, head, path),
            }
        )
    runs = gh(f"repos/{repo}/commits/{head}/check-runs?per_page=100").get("check_runs", [])
    threads = gh(f"repos/{repo}/pulls/{n}/ccr/review_threads")
    reviews = gh(f"repos/{repo}/pulls/{n}/reviews?per_page=100")
    issues = linked_issues(repo, pr.get("body") or "")
    workflow_runs = gh(f"repos/{repo}/actions/runs?head_sha={head}&per_page=100").get(
        "workflow_runs", []
    )
    return {
        "repository": repo,
        "pr_number": n,
        "base_sha": merge_base,
        "head_sha": head,
        "base_ref": pr["base"]["ref"],
        "base_ref_sha": base_tip,
        "head_ref": pr["head"]["ref"],
        "title": pr["title"],
        "draft": pr["draft"],
        "author": pr["user"]["login"],
        "intent": {
            "source_kind": "ISSUE" if issues else "PR_BODY",
            "original_pr_prompt_available": False,
            "pr_body": pr.get("body") or "",
            "linked_issues": issues,
        },
        "files": files,
        "check_runs": [
            {"id": r["id"], "name": r["name"], "status": r["status"], "conclusion": r["conclusion"]}
            for r in runs
        ],
        "ci_failures": [
            {
                "name": r["name"],
                "conclusion": r["conclusion"],
                "required": None,
                "check_run_id": r["id"],
            }
            for r in runs
            if r.get("conclusion") in FAILED_CONCLUSIONS
        ],
        "review_threads": [
            {
                "thread_id": f"RT-{n}-{t['comment_ids'][0]}",
                "is_resolved": t["resolved"],
                "outdated": t.get("outdated"),
                "path": t.get("path"),
                "line": t.get("line"),
                "comment_ids": t["comment_ids"],
            }
            for t in threads
            if t.get("comment_ids")
        ],
        "workflow_runs": [
            {
                "path": w["path"],
                "name": w["name"],
                "status": w["status"],
                "conclusion": w["conclusion"],
            }
            for w in workflow_runs
        ],
        "approvals": effective_approvals(reviews, head),
        "merge_rules": merge_rules(repo, pr["base"]["ref"]),
    }


_RULES_CACHE: dict[tuple[str, str], dict[str, Any]] = {}


def merge_rules(repo: str, branch: str) -> dict[str, Any]:
    """Effective ruleset merge gates for ``branch`` (cached per branch).

    Only repository rulesets are read. Classic branch protection is not probed: its endpoint
    needs admin scope and is refused on the tokens this audit runs with.
    """
    key = (repo, branch)
    if key not in _RULES_CACHE:
        _RULES_CACHE[key] = _merge_rules(repo, branch)
    return _RULES_CACHE[key]


def _merge_rules(repo: str, branch: str) -> dict[str, Any]:
    rules = {
        "branch": branch,
        "source": f"repos/{repo}/rules/branches/{branch}",
        "required_status_checks": [],
        "required_workflows": [],
        "required_approving_review_count": 0,
        "required_review_thread_resolution": False,
    }
    try:
        active = gh(rules["source"])
    except subprocess.CalledProcessError:
        rules["source"] = "UNAVAILABLE"
        return rules
    for rule in active:
        params = rule.get("parameters") or {}
        if rule["type"] == "required_status_checks":
            rules["required_status_checks"] += [
                c["context"] for c in params.get("required_status_checks", [])
            ]
        elif rule["type"] == "workflows":
            rules["required_workflows"] += [w["path"] for w in params.get("workflows", [])]
        elif rule["type"] == "pull_request":
            rules["required_approving_review_count"] = max(
                rules["required_approving_review_count"],
                params.get("required_approving_review_count", 0),
            )
            rules["required_review_thread_resolution"] |= bool(
                params.get("required_review_thread_resolution")
            )
    rules["required_status_checks"] = sorted(set(rules["required_status_checks"]))
    rules["required_workflows"] = sorted(set(rules["required_workflows"]))
    return rules


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--clone", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--pr", type=int, action="append", default=[])
    args = ap.parse_args()

    open_prs = {p["number"]: p for p in gh(f"repos/{args.repo}/pulls?state=open&per_page=100")}
    selected = sorted(args.pr or open_prs)
    missing = [n for n in selected if n not in open_prs]
    if missing:
        print(f"FAIL: not open: {missing}", file=sys.stderr)
        return 2
    default = gh(f"repos/{args.repo}")["default_branch"]
    refspecs = [f"refs/pull/{n}/head:refs/remotes/origin/pr/{n}" for n in selected]
    fetch = git(args.clone, "fetch", "-q", "origin", default, *refspecs)
    if fetch.returncode != 0:
        print(f"FAIL: git fetch: {fetch.stderr.decode()[-500:]}", file=sys.stderr)
        return 2

    snap_dir = args.out / "snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)
    heads_by_ref = {open_prs[n]["head"]["ref"]: n for n in selected}
    frozen = []
    snaps = {}
    for n in selected:
        snap = snaps[n] = snapshot(args.repo, args.clone, open_prs[n])
        (snap_dir / f"pr-{n}.json").write_text(json.dumps(snap, indent=1))
    paths = {n: touched_paths(snaps[n]) for n in selected}
    for n in selected:
        snap = snaps[n]
        frozen.append(
            {
                "pr": n,
                "head_sha": snap["head_sha"],
                "base_ref": snap["base_ref"],
                "stacked_on": heads_by_ref.get(snap["base_ref"]),
                # PRs changing at least one of the same paths: their combined tree must be tested.
                "overlaps_with": sorted(m for m in selected if m != n and paths[m] & paths[n]),
                "linked_issues": [i["number"] for i in snap["intent"]["linked_issues"]],
                "files": len(snap["files"]),
                "ci_failures": [c["name"] for c in snap["ci_failures"]],
                "unresolved_threads": sum(not t["is_resolved"] for t in snap["review_threads"]),
                "approvals_on_head": sum(a["on_head"] for a in snap["approvals"]),
            }
        )
    default_sha = git(args.clone, "rev-parse", f"origin/{default}").stdout.decode().strip()
    (args.out / "frozen-pr-set.json").write_text(
        json.dumps(
            {
                "repository": args.repo,
                "default_branch": default,
                "default_branch_sha": default_sha,
                "prs": frozen,
            },
            indent=1,
        )
    )
    print(json.dumps(frozen, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

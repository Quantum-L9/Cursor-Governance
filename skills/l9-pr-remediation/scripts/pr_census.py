#!/usr/bin/env python3
"""One GraphQL census of open PRs, files, stack edges, and unresolved threads.

Stdlib only. Does not print tokens. Does not download patches. Caps: 50 open
PRs, 100 files/PR, 100 threads/page. REST comment/review fetches are not this
script — they stay fallback in signal-ingestion.md when threads_incomplete.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

MAX_PRS = 50
FILES_PER_PR = 100
THREADS_PAGE = 100
CRA_LOGINS = frozenset(
    {
        "github-code-quality",
        "github-code-quality[bot]",
        "copilot",
        "copilot[bot]",
        "copilot-pull-request-reviewer",
        "copilot-pull-request-reviewer[bot]",
    }
)

OPEN_PRS_QUERY = """
query($owner: String!, $repo: String!, $cursor: String) {
  repository(owner: $owner, name: $repo) {
    pullRequests(
      first: 50
      states: OPEN
      orderBy: {field: CREATED_AT, direction: ASC}
      after: $cursor
    ) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number
        title
        createdAt
        mergeable
        reviewDecision
        url
        additions
        deletions
        baseRefName
        headRefName
        headRefOid
        author { login }
        files(first: 100) {
          pageInfo { hasNextPage }
          nodes { path }
        }
        reviewThreads(first: 100) {
          pageInfo { hasNextPage endCursor }
          nodes {
            id
            isResolved
            comments(first: 5) {
              nodes { body author { login } path line }
            }
          }
        }
      }
    }
  }
}
"""

THREADS_QUERY = """
query($owner: String!, $repo: String!, $pr: Int!, $cursor: String) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $pr) {
      reviewThreads(first: 100, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          isResolved
          comments(first: 5) {
            nodes { body author { login } path line }
          }
        }
      }
    }
  }
}
"""

_TOKEN_RE = re.compile(
    r"(gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|Bearer\s+\S+)",
    re.IGNORECASE,
)


def redact(text: str) -> str:
    return _TOKEN_RE.sub("<redacted>", text or "")


def _login(author: dict[str, Any] | None) -> str:
    if not isinstance(author, dict):
        return ""
    return str(author.get("login") or "")


def classify_author(login: str) -> str:
    key = login.lower().removesuffix("[bot]")
    full = login.lower()
    if (
        full in CRA_LOGINS
        or f"{key}[bot]" in CRA_LOGINS
        or key
        in {
            "github-code-quality",
            "copilot",
            "copilot-pull-request-reviewer",
        }
    ):
        return "code_review_agent"
    if key in {"gemini-code-assist", "coderabbitai"}:
        return "bot"
    if key in {"github-actions", "github-advanced-security"}:
        return "ci"
    return "human"


def thread_to_finding(node: dict[str, Any]) -> dict[str, Any] | None:
    comments = ((node.get("comments") or {}).get("nodes")) or []
    if not comments:
        return {
            "id": node.get("id"),
            "isResolved": bool(node.get("isResolved")),
            "author": "",
            "reviewer_class": "human",
            "path": None,
            "line": None,
            "body": "",
        }
    first = comments[0] if isinstance(comments[0], dict) else {}
    login = _login(first.get("author") if isinstance(first.get("author"), dict) else None)
    return {
        "id": node.get("id"),
        "isResolved": bool(node.get("isResolved")),
        "author": login,
        "reviewer_class": classify_author(login),
        "path": first.get("path"),
        "line": first.get("line"),
        "body": first.get("body") or "",
    }


def parse_pr_node(node: dict[str, Any]) -> dict[str, Any]:
    files_conn = node.get("files") or {}
    thread_conn = node.get("reviewThreads") or {}
    files = [n.get("path") for n in (files_conn.get("nodes") or []) if n.get("path")]
    threads = [thread_to_finding(t) for t in (thread_conn.get("nodes") or [])]
    unresolved = [t for t in threads if t and not t["isResolved"]]
    files_page = files_conn.get("pageInfo") or {}
    thread_page = thread_conn.get("pageInfo") or {}
    return {
        "number": node.get("number"),
        "title": node.get("title") or "",
        "createdAt": node.get("createdAt"),
        "mergeable": node.get("mergeable"),
        "reviewDecision": node.get("reviewDecision"),
        "url": node.get("url"),
        "additions": node.get("additions"),
        "deletions": node.get("deletions"),
        "base": node.get("baseRefName"),
        "head": node.get("headRefName"),
        "headOid": node.get("headRefOid"),
        "author": _login(node.get("author") if isinstance(node.get("author"), dict) else None),
        "files": files,
        "files_truncated": bool(files_page.get("hasNextPage")),
        "unresolved_threads": unresolved,
        "threads_incomplete": bool(thread_page.get("hasNextPage")),
        "thread_cursor": thread_page.get("endCursor"),
    }


def overlap_and_stack(
    prs: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_head: dict[str, int] = {}
    for pr in prs:
        head = pr.get("head")
        num = pr.get("number")
        if isinstance(head, str) and isinstance(num, int):
            by_head[head] = num
    stacks: list[dict[str, Any]] = []
    for pr in prs:
        parent = by_head.get(pr.get("base") or "")
        child_nums = [
            other["number"]
            for other in prs
            if other.get("base") == pr.get("head") and other.get("number") != pr.get("number")
        ]
        pr["stack_children"] = child_nums
        pr["stack_parent"] = parent if parent != pr.get("number") else None
        if child_nums:
            stacks.append({"parent": pr["number"], "children": child_nums})

    overlaps: list[dict[str, Any]] = []
    for i, a in enumerate(prs):
        a_files = set(a.get("files") or [])
        for b in prs[i + 1 :]:
            shared = sorted(a_files.intersection(b.get("files") or []))
            if shared:
                overlaps.append({"files": shared, "prs": [a.get("number"), b.get("number")]})
    return overlaps, stacks


def parse_repository_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Turn one GraphQL `data` object (or a full {data:...} envelope) into census JSON."""
    repo = data.get("data", data)
    if "repository" in repo:
        repo = repo["repository"]
    conn = (repo or {}).get("pullRequests") or {}
    nodes = conn.get("nodes") or []
    prs = [parse_pr_node(n) for n in nodes if isinstance(n, dict)]
    page = conn.get("pageInfo") or {}
    truncated = bool(page.get("hasNextPage")) or len(prs) > MAX_PRS
    prs = prs[:MAX_PRS]
    overlaps, stacks = overlap_and_stack(prs)
    threads_incomplete = any(p.get("threads_incomplete") for p in prs)
    return {
        "schema": "l9.pr-census.v1",
        "prs": prs,
        "overlap": overlaps,
        "stack": stacks,
        "prs_truncated": truncated,
        "threads_incomplete": threads_incomplete,
        "caps": {"max_prs": MAX_PRS, "files_per_pr": FILES_PER_PR, "threads_page": THREADS_PAGE},
    }


def append_thread_page(pr: dict[str, Any], thread_conn: dict[str, Any]) -> None:
    extra = [thread_to_finding(t) for t in (thread_conn.get("nodes") or [])]
    for item in extra:
        if item and not item["isResolved"]:
            pr["unresolved_threads"].append(item)
    page = thread_conn.get("pageInfo") or {}
    pr["threads_incomplete"] = bool(page.get("hasNextPage"))
    pr["thread_cursor"] = page.get("endCursor")


def _gh_graphql(query: str, variables: dict[str, Any]) -> dict[str, Any]:
    cmd = ["gh", "api", "graphql", "--input", "-"]
    payload = json.dumps({"query": query, "variables": variables})
    proc = subprocess.run(
        cmd,
        input=payload,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(f"BLOCKED: gh api graphql failed: {redact(proc.stderr)[:400]}")
    try:
        body = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"BLOCKED: gh api graphql returned non-JSON: {exc}") from exc
    errors = body.get("errors")
    if errors:
        raise SystemExit(f"BLOCKED: GraphQL errors: {redact(json.dumps(errors))[:400]}")
    return body


def census_live(owner: str, repo: str) -> dict[str, Any]:
    all_nodes: list[dict[str, Any]] = []
    cursor: str | None = None
    pages = 0
    while True:
        pages += 1
        if pages > 4:
            break
        variables: dict[str, Any] = {"owner": owner, "repo": repo, "cursor": cursor}
        body = _gh_graphql(OPEN_PRS_QUERY, variables)
        conn = (((body.get("data") or {}).get("repository") or {}).get("pullRequests")) or {}
        all_nodes.extend(n for n in (conn.get("nodes") or []) if isinstance(n, dict))
        page = conn.get("pageInfo") or {}
        if not page.get("hasNextPage") or len(all_nodes) >= MAX_PRS:
            break
        cursor = page.get("endCursor")
        if not cursor:
            break
    envelope = {
        "repository": {
            "pullRequests": {
                "pageInfo": {"hasNextPage": len(all_nodes) > MAX_PRS},
                "nodes": all_nodes[:MAX_PRS],
            }
        }
    }
    census = parse_repository_payload(envelope)
    for pr in census["prs"]:
        while pr.get("threads_incomplete") and pr.get("thread_cursor"):
            body = _gh_graphql(
                THREADS_QUERY,
                {
                    "owner": owner,
                    "repo": repo,
                    "pr": pr["number"],
                    "cursor": pr["thread_cursor"],
                },
            )
            conn = (
                ((body.get("data") or {}).get("repository") or {}).get("pullRequest") or {}
            ).get("reviewThreads") or {}
            append_thread_page(pr, conn)
            if not pr.get("threads_incomplete"):
                break
    census["threads_incomplete"] = any(p.get("threads_incomplete") for p in census["prs"])
    return census


def parse_repo_arg(value: str) -> tuple[str, str]:
    if "/" not in value or value.count("/") != 1:
        raise SystemExit("BLOCKED: --repo must be owner/name")
    owner, name = value.split("/")
    if not owner or not name:
        raise SystemExit("BLOCKED: --repo must be owner/name")
    return owner, name


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Census open PRs via one GraphQL path")
    parser.add_argument("--repo", required=True, help="owner/name")
    parser.add_argument("--output", required=True, help="write census JSON (under $PWD)")
    parser.add_argument(
        "--from-json",
        default="",
        help="parse a saved GraphQL envelope instead of calling gh (tests)",
    )
    args = parser.parse_args(argv)
    out = Path(args.output)
    if out.is_absolute() and "/tmp" in str(out):
        raise SystemExit("BLOCKED: --output must not be under /tmp")
    owner, name = parse_repo_arg(args.repo)
    if args.from_json:
        payload = json.loads(Path(args.from_json).read_text(encoding="utf-8"))
        census = parse_repository_payload(payload)
    else:
        census = census_live(owner, name)
    census["repo"] = f"{owner}/{name}"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(census, indent=2) + "\n", encoding="utf-8")
    print(
        f"census: prs={len(census['prs'])} overlap={len(census['overlap'])} "
        f"stack={len(census['stack'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

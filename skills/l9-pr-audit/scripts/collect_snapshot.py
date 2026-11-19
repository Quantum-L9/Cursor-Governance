#!/usr/bin/env python3
"""Collect read-only census snapshots for build_change_ledger.py from GitHub + a local clone.

Freezes the PR set at collection time and writes, per PR, the snapshot shape documented in
build_change_ledger.py plus the binding facts the audit needs (base/head refs, check runs,
review threads, approvals, PR body). It also writes ``frozen-pr-set.json`` with stack edges
(a PR whose base branch is another open PR's head branch) so semantic lanes can be grouped.

GitHub is read over the transport ``protocol.rest_only`` selects: review threads come
from the GraphQL ``reviewThreads`` query unless the surface is REST-only, in which case the
``ccr/review_threads`` route is used (with one fallback to the other transport, then a
non-zero exit). Classic branch protection is probed and recorded only on evidence: ABSENT
requires the exact 404 body ``Branch not protected``; a 200 merges its required checks; every
other result is UNKNOWN. The only local write is fetching ``refs/pull/<n>/head`` into
``refs/remotes/origin/pr/<n>`` of the given clone.

Usage:
  collect_snapshot.py --repo OWNER/NAME --clone PATH --out DIR [--pr N ...]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

# protocol.rest_only is the transport selector for review threads. It lives in the
# remediation skill and is imported, never copied: one definition, one surface contract.
_PROTOCOL_DIR = Path(__file__).resolve().parents[2] / "l9-pr-remediation" / "scripts"
if str(_PROTOCOL_DIR) not in sys.path:
    sys.path.insert(0, str(_PROTOCOL_DIR))
from protocol import rest_only  # noqa: E402

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


class ThreadsUnavailable(RuntimeError):
    """Both review-thread transports failed; the run must exit non-zero."""


def _threads_rest(repo: str, n: int) -> list[dict[str, Any]]:
    return gh(f"repos/{repo}/pulls/{n}/ccr/review_threads")


_THREADS_QUERY = (
    "query($owner:String!,$name:String!,$number:Int!,$cursor:String)"
    "{repository(owner:$owner,name:$name)"
    "{pullRequest(number:$number){reviewThreads(first:100,after:$cursor)"
    "{pageInfo{hasNextPage endCursor}nodes{isResolved isOutdated path line"
    " comments(first:100){nodes{databaseId body}}}}}}}"
)


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ThreadsUnavailable(f"reviewThreads {label} missing")
    return value


def _comment_record(comment: Any) -> tuple[str, str]:
    """REST database id plus body. The GraphQL node id is not a pulls/comments id."""
    if not isinstance(comment, dict):
        raise ThreadsUnavailable("review comment is not an object")
    database_id = comment.get("databaseId")
    body = comment.get("body")
    if type(database_id) is not int:
        raise ThreadsUnavailable("review comment databaseId is not a REST id")
    if not isinstance(body, str):
        raise ThreadsUnavailable("review comment body missing")
    return str(database_id), body


def _threads_graphql(repo: str, n: int) -> list[dict[str, Any]]:
    owner, _, name = repo.partition("/")
    threads: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        argv = [
            "gh",
            "api",
            "graphql",
            "-F",
            f"owner={owner}",
            "-F",
            f"name={name}",
            "-F",
            f"number={n}",
            "-f",
            f"query={_THREADS_QUERY}",
        ]
        if cursor:
            argv += ["-F", f"cursor={cursor}"]
        proc = subprocess.run(argv, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise ThreadsUnavailable(f"reviewThreads query failed: {proc.stderr.strip()[-300:]}")
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise ThreadsUnavailable(f"reviewThreads query returned no JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise ThreadsUnavailable("reviewThreads envelope is not an object")
        if payload.get("errors"):
            raise ThreadsUnavailable("reviewThreads query returned errors")
        data = _require_dict(payload.get("data"), "data")
        repository = _require_dict(data.get("repository"), "repository")
        pull_request = _require_dict(repository.get("pullRequest"), "pullRequest")
        window = _require_dict(pull_request.get("reviewThreads"), "connection")
        nodes = window.get("nodes")
        if not isinstance(nodes, list):
            raise ThreadsUnavailable("reviewThreads nodes missing")
        page_info = _require_dict(window.get("pageInfo"), "pageInfo")
        if type(page_info.get("hasNextPage")) is not bool:
            raise ThreadsUnavailable("reviewThreads pageInfo.hasNextPage missing")
        for node in nodes:
            if not isinstance(node, dict):
                raise ThreadsUnavailable("reviewThreads node is not an object")
            comments = node.get("comments")
            if not isinstance(comments, dict) or not isinstance(comments.get("nodes"), list):
                raise ThreadsUnavailable("reviewThreads comments missing")
            records = [_comment_record(comment) for comment in comments["nodes"]]
            if records:
                comment_ids, bodies = zip(*records, strict=True)
                threads.append(
                    {
                        "resolved": bool(node.get("isResolved")),
                        "outdated": node.get("isOutdated"),
                        "path": node.get("path"),
                        "line": node.get("line"),
                        "comment_ids": list(comment_ids),
                        "comment_bodies": list(bodies),
                    }
                )
        if page_info["hasNextPage"]:
            end = page_info.get("endCursor")
            if not isinstance(end, str) or not end:
                raise ThreadsUnavailable("reviewThreads pagination cursor missing")
            cursor = end
            continue
        return threads


def comment_body(repo: str, comment_id: str) -> str:
    """Body of a review comment through the numeric REST pulls/comments route."""
    doc = gh(f"repos/{repo}/pulls/comments/{comment_id}")
    if not isinstance(doc, dict) or not isinstance(doc.get("body"), str):
        raise ThreadsUnavailable(f"pulls/comments/{comment_id} returned no body")
    return doc["body"]


def review_threads(
    repo: str,
    n: int,
    *,
    rest: Callable[[str, int], list[dict[str, Any]]] = _threads_rest,
    graphql: Callable[[str, int], list[dict[str, Any]]] = _threads_graphql,
    selector: Callable[[], bool] = rest_only,
) -> list[dict[str, Any]]:
    """Review threads over the transport ``protocol.rest_only`` selects.

    The ``reviewThreads`` GraphQL query runs unless ``rest_only`` is true, which
    selects ``ccr/review_threads``. If the selected transport fails the other is
    tried once; when both fail the run exits non-zero.
    """
    first, second = (rest, graphql) if selector() else (graphql, rest)
    last_error = ""
    for fetch in (first, second):
        try:
            return fetch(repo, n)
        except (subprocess.CalledProcessError, ThreadsUnavailable) as exc:
            last_error = str(exc)
    raise ThreadsUnavailable(f"review threads unavailable on both transports: {last_error}")


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
    threads = review_threads(repo, n)
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


def _classic_protection_result(
    returncode: int, stdout: str, stderr: str, source: str
) -> dict[str, Any]:
    """Classic branch protection verdict from a probe's raw result, evidence-bound.

    ABSENT only for the exact 404 body ``Branch not protected``. A 200 merges its
    required checks into the effective rules. Every other result (403, another 404,
    a malformed 200 body) is UNKNOWN and withholds complete READY downstream.
    """
    if returncode == 0:
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            return {"status": "UNKNOWN", "source": source, "required_status_checks": []}
        if not isinstance(payload, dict):
            return {"status": "UNKNOWN", "source": source, "required_status_checks": []}
        required = payload.get("required_status_checks") or {}
        contexts = list(required.get("contexts") or [])
        contexts += [c.get("context") for c in required.get("checks") or [] if c.get("context")]
        return {
            "status": "PRESENT",
            "source": source,
            "required_status_checks": sorted({str(c) for c in contexts if c}),
        }
    lowered = (stderr or "").lower()
    if "404" in lowered and "branch not protected" in lowered:
        return {"status": "ABSENT", "source": source, "required_status_checks": []}
    return {"status": "UNKNOWN", "source": source, "required_status_checks": []}


def classic_protection(repo: str, branch: str) -> dict[str, Any]:
    """Probe classic branch protection for ``branch`` and classify the raw result."""
    source = f"repos/{repo}/branches/{branch}/protection"
    proc = subprocess.run(
        ["gh", "api", "--method", "GET", source], capture_output=True, text=True, check=False
    )
    return _classic_protection_result(proc.returncode, proc.stdout, proc.stderr, source)


def merge_rules(repo: str, branch: str) -> dict[str, Any]:
    """Effective merge gates for ``branch`` (cached per branch).

    Repository rulesets and classic branch protection both contribute required checks.
    Classic protection is recorded on evidence: ABSENT only for the exact 404 body
    ``Branch not protected``; a 200 merges its required checks; every other result is
    UNKNOWN (and withholds complete READY downstream).
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
        "classic_protection": {"status": "UNKNOWN", "source": "", "required_status_checks": []},
    }
    try:
        active = gh(rules["source"])
    except subprocess.CalledProcessError:
        rules["source"] = "UNAVAILABLE"
    else:
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
    rules["classic_protection"] = classic_protection(repo, branch)
    rules["required_status_checks"] += rules["classic_protection"]["required_status_checks"]
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
    try:
        for n in selected:
            snap = snaps[n] = snapshot(args.repo, args.clone, open_prs[n])
            (snap_dir / f"pr-{n}.json").write_text(json.dumps(snap, indent=1))
    except ThreadsUnavailable as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
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

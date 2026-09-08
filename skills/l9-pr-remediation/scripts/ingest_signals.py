#!/usr/bin/env python3
"""Unified PR signal snapshot. Stdlib only.

Replaces the gh-cookbook half of signal-ingestion.md. Fetches CI, reviews,
inline comments, issue comments, and unresolved review threads, then
normalizes optional scanner snapshots. Does not invent disposition, board,
HUMAN, or FALSE_POSITIVE.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from protocol import (
    VERIFY_COMMAND,
    discover_gate_registry,
    edit_axis,
    is_code_review_agent,
    ledger_source,
    merge_findings,
    normalize_scanner_findings,
    reviewer_class,
    severity_hint,
)
from protocol import validated_output as _validated_output

GH_TIMEOUT_SEC = 30
THREADS_QUERY = """
query($owner: String!, $repo: String!, $pr: Int!, $cursor: String) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $pr) {
      reviewThreads(first: 100, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          isResolved
          comments(first: 20) {
            nodes {
              id
              body
              path
              line
              author { login }
            }
          }
        }
      }
    }
  }
}
"""


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr, flush=True)
    raise SystemExit(1)


def _run_gh(argv: list[str], *, input_text: str | None = None) -> str:
    try:
        proc = subprocess.run(  # noqa: S603
            argv,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=GH_TIMEOUT_SEC,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        _fail(f"gh timed out after {GH_TIMEOUT_SEC}s: {' '.join(argv[:6])}: {exc}")
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()[-800:]
        _fail(f"gh exit {proc.returncode}: {' '.join(argv[:6])}: {err}")
    return proc.stdout


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail(f"unreadable {path}: {exc}")


def _fixture(root: Path | None, name: str, default: Any) -> Any:
    if root is None:
        return default
    path = root / name
    if not path.is_file():
        return default
    return _load_json(path)


def _login(obj: dict[str, Any] | None) -> str:
    if not isinstance(obj, dict):
        return ""
    user = obj.get("user") or obj.get("author") or {}
    if isinstance(user, dict):
        return str(user.get("login") or "")
    return str(user or "")


def _annotate(finding: dict[str, Any], required: set[str]) -> dict[str, Any]:
    finding["reviewer_class"] = reviewer_class(str(finding.get("author") or ""))
    finding["ownership_hint"] = edit_axis(finding.get("file"))
    finding["severity_hint"] = severity_hint(finding, required)
    finding.setdefault("local_verify_command", VERIFY_COMMAND)
    return finding


def _from_review(item: dict[str, Any], index: int) -> dict[str, Any]:
    login = _login(item)
    body = str(item.get("body") or "")
    return {
        "id": f"review-{index}",
        "source": ledger_source(author=login, kind="review"),
        "surface": "general",
        "author": login,
        "file": None,
        "line": None,
        "message": body.splitlines()[0][:240] if body else login,
        "gate": None,
        "raw": body,
        "thread_id": item.get("id"),
        "severity_label": None,
    }


def _from_inline(item: dict[str, Any], index: int) -> dict[str, Any]:
    login = _login(item)
    body = str(item.get("body") or "")
    return {
        "id": f"inline-{index}",
        "source": ledger_source(author=login, kind="review"),
        "surface": "inline",
        "author": login,
        "file": item.get("path"),
        "line": item.get("line") or item.get("original_line"),
        "message": body.splitlines()[0][:240] if body else login,
        "gate": None,
        "raw": body,
        "thread_id": item.get("id"),
        "severity_label": _severity_label(body),
    }


def _severity_label(body: str) -> str | None:
    lowered = body.lower()
    for label in ("error", "warning", "note"):
        if f"**{label}**" in lowered or f"`{label}`" in lowered or f"{label}:" in lowered:
            return label
    return None


def _from_check(item: dict[str, Any], index: int) -> dict[str, Any] | None:
    conclusion = str(item.get("conclusion") or item.get("state") or "").lower()
    if conclusion in {"success", "skipped", "neutral", "stale"}:
        return None
    name = str(item.get("name") or item.get("context") or f"check-{index}")
    message = str(item.get("output") or item.get("description") or conclusion or name)
    return {
        "id": f"ci-{index}",
        "source": "ci",
        "surface": "check",
        "author": "github-actions",
        "file": item.get("path") or item.get("file"),
        "line": item.get("line"),
        "message": message.splitlines()[0][:240],
        "gate": name,
        "raw": message,
        "thread_id": None,
    }


def _from_thread(node: dict[str, Any], index: int) -> dict[str, Any] | None:
    if node.get("isResolved") is True:
        return None
    comments = ((node.get("comments") or {}).get("nodes")) or []
    first = comments[0] if comments else {}
    login = _login(first) if first else ""
    body = str(first.get("body") or "")
    return {
        "id": f"thread-{index}",
        "source": ledger_source(author=login, kind="review"),
        "surface": "inline" if first.get("path") else "general",
        "author": login,
        "file": first.get("path"),
        "line": first.get("line"),
        "message": body.splitlines()[0][:240] if body else login,
        "gate": None,
        "raw": body,
        "thread_id": node.get("id"),
        "severity_label": _severity_label(body),
    }


def _paginate_threads(owner: str, repo: str, pr: int) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        payload = {
            "query": THREADS_QUERY,
            "variables": {"owner": owner, "repo": repo, "pr": pr, "cursor": cursor},
        }
        data = json.loads(
            _run_gh(["gh", "api", "graphql", "--input", "-"], input_text=json.dumps(payload))
        )
        errors = data.get("errors")
        if errors:
            _fail(f"graphql errors: {json.dumps(errors)[:800]}")
        block = (((data.get("data") or {}).get("repository") or {}).get("pullRequest") or {}).get(
            "reviewThreads"
        ) or {}
        nodes.extend(block.get("nodes") or [])
        page = block.get("pageInfo") or {}
        if not page.get("hasNextPage"):
            break
        cursor = page.get("endCursor")
        if not cursor:
            _fail("reviewThreads pagination stalled (hasNextPage without cursor)")
    return nodes


def _gh_json(path: str) -> Any:
    """Parse every --paginate page. gh concatenates documents; --slurp arrays them."""
    raw = _run_gh(["gh", "api", "--paginate", "--slurp", path])
    pages = json.loads(raw or "[]")
    if not isinstance(pages, list):
        return pages
    if not pages:
        return []
    if all(isinstance(page, list) for page in pages):
        out: list[Any] = []
        for page in pages:
            out.extend(page)
        return out
    if len(pages) == 1:
        return pages[0]
    return pages


def _already_ingested(findings: list[dict[str, Any]], candidate: dict[str, Any]) -> bool:
    author = candidate.get("author")
    file_name = candidate.get("file")
    line = candidate.get("line")
    message = str(candidate.get("message") or "")[:80]
    for item in findings:
        if file_name and line not in {None, ""}:
            if item.get("file") == file_name and item.get("line") == line:
                return True
        elif (
            author
            and item.get("author") == author
            and str(item.get("message") or "")[:80] == message
        ):
            return True
    return False


def collect(
    *,
    owner: str,
    repo: str,
    pr: int,
    required_checks: set[str],
    fixture_dir: Path | None,
    cwd: Path,
    scanners: dict[str, Path],
) -> dict[str, Any]:
    if fixture_dir is None:
        pr_doc = _gh_json(f"repos/{owner}/{repo}/pulls/{pr}")
        reviews = _gh_json(f"repos/{owner}/{repo}/pulls/{pr}/reviews")
        comments = _gh_json(f"repos/{owner}/{repo}/pulls/{pr}/comments")
        issue_comments = _gh_json(f"repos/{owner}/{repo}/issues/{pr}/comments")
        head_sha = str((pr_doc.get("head") or {}).get("sha") or "")
        if not head_sha:
            _fail("PR head SHA missing")
        checks = _gh_json(f"repos/{owner}/{repo}/commits/{head_sha}/check-runs")
        if isinstance(checks, dict):
            checks = checks.get("check_runs") or []
        threads = _paginate_threads(owner, repo, pr)
    else:
        pr_doc = _fixture(fixture_dir, "pr.json", {})
        reviews = _fixture(fixture_dir, "reviews.json", [])
        comments = _fixture(fixture_dir, "comments.json", [])
        issue_comments = _fixture(fixture_dir, "issue_comments.json", [])
        checks = _fixture(fixture_dir, "checks.json", [])
        threads_doc = _fixture(fixture_dir, "threads.json", {"nodes": []})
        threads = threads_doc.get("nodes") if isinstance(threads_doc, dict) else threads_doc
        head_sha = str(
            pr_doc.get("head_sha")
            or pr_doc.get("headRefOid")
            or (pr_doc.get("head") or {}).get("sha")
            or ""
        )

    findings: list[dict[str, Any]] = []
    for index, item in enumerate(checks or [], start=1):
        if isinstance(item, dict):
            built = _from_check(item, index)
            if built:
                findings.append(_annotate(built, required_checks))
    for index, node in enumerate(threads or [], start=1):
        if isinstance(node, dict):
            built = _from_thread(node, index)
            if built:
                findings.append(_annotate(built, required_checks))
    for index, item in enumerate(reviews or [], start=1):
        if not isinstance(item, dict):
            continue
        state = str(item.get("state") or "").upper()
        login = _login(item)
        body = str(item.get("body") or "").strip()
        keep = state == "CHANGES_REQUESTED" or is_code_review_agent(login) or bool(body)
        if not keep:
            continue
        built = _annotate(_from_review(item, index), required_checks)
        if not _already_ingested(findings, built):
            findings.append(built)
    for index, item in enumerate(comments or [], start=1):
        if not isinstance(item, dict):
            continue
        built = _annotate(_from_inline(item, index), required_checks)
        if not _already_ingested(findings, built):
            findings.append(built)
    for index, item in enumerate(issue_comments or [], start=1):
        if not isinstance(item, dict):
            continue
        built = _annotate(_from_review(item, 1000 + index), required_checks)
        if not _already_ingested(findings, built):
            findings.append(built)

    for source, path in scanners.items():
        snapshot = _load_json(path)
        if not isinstance(snapshot, dict):
            _fail(f"{source} snapshot is not an object")
        if str(snapshot.get("status") or "").upper() == "BLOCKED":
            _fail(f"{source} snapshot status=BLOCKED (incomplete pagination)")
        findings.extend(normalize_scanner_findings(source, snapshot))

    cra_before_merge = [
        item for item in findings if item.get("reviewer_class") == "code_review_agent"
    ]
    pre_merge = list(findings)
    findings = merge_findings(findings)
    cra_seen = {
        _login(item)
        for bucket in (reviews, comments, issue_comments)
        for item in (bucket or [])
        if isinstance(item, dict) and is_code_review_agent(_login(item))
    }
    cra_findings = [item for item in findings if item.get("reviewer_class") == "code_review_agent"]
    unresolved = [
        node
        for node in (threads or [])
        if isinstance(node, dict) and node.get("isResolved") is not True
    ]
    completeness = {
        "makefile_verbs": True,
        "cra_logins_present": sorted(cra_seen),
        "cra_comment_logins": len(cra_seen),
        "cra_findings": len(cra_findings),
        "cra_comments_ingested": (not cra_seen) or bool(cra_before_merge),
        "unresolved_threads": len(unresolved),
        "unresolved_threads_captured": all(
            any(item.get("thread_id") == node.get("id") for item in pre_merge)
            for node in unresolved
            if node.get("id")
        ),
    }
    return {
        "schema_version": "pr-signals-1.0",
        "pr": f"{owner}/{repo}#{pr}",
        "head_sha": head_sha,
        "ingested_at": datetime.now(tz=UTC).isoformat(),
        "gate_registry": discover_gate_registry(cwd),
        "required_checks": sorted(required_checks),
        "findings": findings,
        "completeness": completeness,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest a unified PR finding snapshot.")
    parser.add_argument("--repo", required=True, help="owner/name")
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--required-checks",
        default="",
        help="comma-separated required check names",
    )
    parser.add_argument("--fixture-dir", help="offline GitHub payloads; skips gh")
    parser.add_argument("--sonar")
    parser.add_argument("--semgrep")
    parser.add_argument("--codeql")
    parser.add_argument("--debt")
    args = parser.parse_args(argv)

    if "/" not in args.repo:
        _fail("--repo must be owner/name")
    owner, name = args.repo.split("/", 1)
    required = {item.strip() for item in args.required_checks.split(",") if item.strip()}
    fixture_dir = Path(args.fixture_dir) if args.fixture_dir else None
    if fixture_dir and not fixture_dir.is_dir():
        _fail(f"fixture-dir missing: {fixture_dir}")
    scanners = {
        key: Path(value)
        for key, value in (
            ("sonar", args.sonar),
            ("semgrep", args.semgrep),
            ("codeql", args.codeql),
            ("debt", args.debt),
        )
        if value
    }
    for path in scanners.values():
        if not path.is_file():
            _fail(f"scanner snapshot missing: {path}")

    output = _validated_output(args.output)
    snapshot = collect(
        owner=owner,
        repo=name,
        pr=args.pr,
        required_checks=required,
        fixture_dir=fixture_dir,
        cwd=Path.cwd(),
        scanners=scanners,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    complete = snapshot["completeness"]
    if not complete["cra_comments_ingested"]:
        _fail("CRA comments present on the PR were not ingested")
    if not complete["unresolved_threads_captured"]:
        _fail("unresolved review threads were collapsed before thread_id capture")
    print(
        f"snapshot: {output} findings={len(snapshot['findings'])} "
        f"cra={complete['cra_findings']} threads={complete['unresolved_threads']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

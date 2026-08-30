#!/usr/bin/env python3
"""Batch reply + resolve PR review threads. Stdlib only.

Replaces the 36-cold-`gh` serial loop that looked hung: unflushed stdout,
no timeout, one REST reply + one GraphQL resolve per thread.

Run with `python3 -u` (or this file's prints flush). Inspect cited files
before setting inspected=true — this script refuses unverified dispositions.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

GH_TIMEOUT_SEC = 30
CHUNK_SIZE = 6
VALID_DISPOSITIONS = frozenset(
    {"fixed", "deferred", "acknowledged", "disagreed"}
)


def _log(msg: str) -> None:
    print(msg, flush=True)


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


def _graphql(payload: dict[str, Any]) -> dict[str, Any]:
    raw = _run_gh(
        ["gh", "api", "graphql", "--input", "-"],
        input_text=json.dumps(payload),
    )
    data = json.loads(raw)
    errors = data.get("errors")
    if errors:
        _fail(f"graphql errors: {json.dumps(errors)[:800]}")
    return data


def _chunks(items: list[Any], size: int) -> list[list[Any]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _require_inspected(
    prs: list[dict[str, Any]], *, summary_only: bool = False
) -> None:
    for pr in prs:
        for th in pr.get("threads") or []:
            if th.get("inspected") is not True:
                _fail(
                    f"PR #{pr.get('number')} thread {th.get('thread_id')} "
                    "missing inspected=true — read the cited file before reply"
                )
            disp = str(th.get("disposition") or "").lower()
            if disp not in VALID_DISPOSITIONS:
                _fail(
                    f"PR #{pr.get('number')} thread {th.get('thread_id')} "
                    f"invalid disposition {disp!r}"
                )
            if not summary_only and not str(th.get("body") or "").strip():
                _fail(f"PR #{pr.get('number')} thread {th.get('thread_id')} empty body")
            if not str(th.get("thread_id") or "").strip():
                _fail(f"PR #{pr.get('number')} missing thread_id")


def _reply_chunk(threads: list[dict[str, Any]]) -> None:
    selections: list[str] = []
    variables: dict[str, Any] = {}
    var_decls: list[str] = []
    for i, th in enumerate(threads):
        tid_k, body_k = f"t{i}", f"b{i}"
        var_decls.append(f"${tid_k}: ID!")
        var_decls.append(f"${body_k}: String!")
        variables[tid_k] = th["thread_id"]
        variables[body_k] = th["body"]
        selections.append(
            f"r{i}: addPullRequestReviewThreadReply(input: {{"
            f"pullRequestReviewThreadId: ${tid_k}, body: ${body_k}}}) "
            "{ comment { id } }"
        )
    _graphql(
        {
            "query": f"mutation({', '.join(var_decls)}) {{ {' '.join(selections)} }}",
            "variables": variables,
        }
    )


def _resolve_chunk(threads: list[dict[str, Any]]) -> None:
    selections: list[str] = []
    variables: dict[str, Any] = {}
    var_decls: list[str] = []
    for i, th in enumerate(threads):
        tid_k = f"t{i}"
        var_decls.append(f"${tid_k}: ID!")
        variables[tid_k] = th["thread_id"]
        selections.append(
            f"s{i}: resolveReviewThread(input: {{threadId: ${tid_k}}}) "
            "{ thread { isResolved } }"
        )
    _graphql(
        {
            "query": f"mutation({', '.join(var_decls)}) {{ {' '.join(selections)} }}",
            "variables": variables,
        }
    )


def _summary_markdown(pr: dict[str, Any], *, cycle: int, commit: str, verify: str) -> str:
    threads = list(pr.get("threads") or [])
    buckets: dict[str, list[dict[str, Any]]] = {
        "fixed": [],
        "deferred": [],
        "acknowledged": [],
        "disagreed": [],
    }
    for th in threads:
        buckets[str(th["disposition"]).lower()].append(th)

    def _rows(items: list[dict[str, Any]], cols: tuple[str, ...]) -> str:
        if not items:
            return "_none_"
        header = "| " + " | ".join(cols) + " |"
        sep = "|" + "|".join(["---"] * len(cols)) + "|"
        lines = [header, sep]
        for th in items:
            finding = str(th.get("finding") or th.get("path") or th["thread_id"][-8:])
            path = str(th.get("path") or "")
            note = str(th.get("note") or th.get("disposition"))
            issue = str(th.get("issue") or "")
            if cols == ("Finding", "File", "Change"):
                lines.append(f"| {finding} | `{path}` | {note} |")
            elif cols == ("Finding", "Reason", "Issue"):
                lines.append(f"| {finding} | {note} | {issue} |")
            elif cols == ("Finding", "Response"):
                lines.append(f"| {finding} | {note} |")
            else:
                lines.append(f"| {finding} | {note} |")
        return "\n".join(lines)

    total = len(threads)
    resolved = total
    return (
        f"## PR Remediation — Cycle {cycle} Summary\n\n"
        f"**Commit:** `{commit}` | **Findings processed:** {total} | "
        f"**CI gates:** {verify}\n\n"
        f"### Fixed ({len(buckets['fixed'])})\n"
        f"{_rows(buckets['fixed'], ('Finding', 'File', 'Change'))}\n\n"
        f"### Deferred ({len(buckets['deferred'])})\n"
        f"{_rows(buckets['deferred'], ('Finding', 'Reason', 'Issue'))}\n\n"
        f"### Acknowledged ({len(buckets['acknowledged'])})\n"
        f"{_rows(buckets['acknowledged'], ('Finding', 'Response'))}\n\n"
        f"### Disagreed ({len(buckets['disagreed'])})\n"
        f"{_rows(buckets['disagreed'], ('Finding', 'Reason'))}\n\n"
        f"---\n"
        f"*Local verify: {verify} | Threads resolved: {resolved}/{total}*\n"
    )


def _post_summary(repo: str, number: int, body: str) -> None:
    _run_gh(
        ["gh", "pr", "comment", str(number), "--repo", repo, "--body", body],
    )


def _load_input(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail(f"invalid --input {path}: {exc}")
    if not isinstance(data, dict) or not isinstance(data.get("prs"), list):
        _fail("--input must be a JSON object with a prs array")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="owner/name")
    parser.add_argument("--input", required=True, type=Path, help="JSON thread ledger")
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="post batch summaries only (threads already replied)",
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="reply + resolve without the per-PR batch summary",
    )
    args = parser.parse_args(argv)

    data = _load_input(args.input)
    prs: list[dict[str, Any]] = data["prs"]
    _require_inspected(prs, summary_only=args.summary_only)
    cycle = int(data.get("cycle") or 1)
    commit = str(data.get("commit") or "none")
    verify = str(data.get("local_verify") or "Unknown")

    gh_calls = 0
    replied = 0
    resolved = 0
    summaries = 0

    for pr in prs:
        number = int(pr["number"])
        threads = list(pr.get("threads") or [])
        _log(f"PR #{number}: {len(threads)} thread(s)")

        if not args.summary_only and threads:
            for i, chunk in enumerate(_chunks(threads, CHUNK_SIZE), start=1):
                _log(f"PR #{number}: reply chunk {i} ({len(chunk)})")
                _reply_chunk(chunk)
                gh_calls += 1
                replied += len(chunk)
            for i, chunk in enumerate(_chunks(threads, CHUNK_SIZE), start=1):
                _log(f"PR #{number}: resolve chunk {i} ({len(chunk)})")
                _resolve_chunk(chunk)
                gh_calls += 1
                resolved += len(chunk)

        if not args.no_summary:
            _log(f"PR #{number}: posting batch summary")
            _post_summary(
                args.repo,
                number,
                _summary_markdown(pr, cycle=cycle, commit=commit, verify=verify),
            )
            gh_calls += 1
            summaries += 1

    _log(
        f"done replied={replied} resolved={resolved} summaries={summaries} "
        f"gh_calls={gh_calls} timeout={GH_TIMEOUT_SEC}s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

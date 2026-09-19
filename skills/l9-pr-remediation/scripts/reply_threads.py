#!/usr/bin/env python3
"""Batch reply + resolve PR review threads. Stdlib only.

Replaces the 36-cold-`gh` serial loop that looked hung: unflushed stdout,
no timeout, one `gh` call per thread.

Two transports, selected by `_rest_only()`:

GraphQL (local CLI/Desktop): batched `addPullRequestReviewThreadReply` +
`resolveReviewThread`, CHUNK_SIZE threads per call, keyed on `thread_id`.

REST (Claude Code Web/Mobile): the session gateway answers `gh api graphql`
with 403 and names its replacements, so reply/resolve/summary each take a
REST route, keyed on `comment_id`, one call per thread (no batch form):

    reply    POST /repos/{o}/{r}/pulls/{n}/comments/{cid}/replies   (native)
    resolve  POST /repos/{o}/{r}/pulls/{n}/ccr/comments/{cid}/resolve
    list     GET  /repos/{o}/{r}/pulls/{n}/ccr/review_threads
    summary  POST /repos/{o}/{r}/issues/{n}/comments                (native)

`ccr/review_threads` never emits a GraphQL node id, so `thread_id` is
unobtainable on that surface and the ledger must carry `comment_id`
instead — see `_require_inspected`.

Run with `python3 -u` (or this file's prints flush). Inspect cited files
before setting inspected=true — this script refuses unverified dispositions.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, NoReturn

from protocol import rest_only as _rest_only

GH_TIMEOUT_SEC = 30
CHUNK_SIZE = 6
VALID_DISPOSITIONS = frozenset({"fixed", "deferred", "acknowledged", "disagreed"})


def _log(msg: str) -> None:
    print(msg, flush=True)


def _fail(msg: str) -> NoReturn:
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


def _rest(method: str, path: str, payload: dict[str, Any] | None = None) -> str:
    argv = ["gh", "api", "--method", method, path]
    if payload is None:
        return _run_gh(argv)
    return _run_gh([*argv, "--input", "-"], input_text=json.dumps(payload))


def _ccr_threads(repo: str, number: int) -> list[dict[str, Any]]:
    """Live review-thread state. The only listing available on a REST surface."""
    raw = _rest("GET", f"repos/{repo}/pulls/{number}/ccr/review_threads")
    data = json.loads(raw)
    if not isinstance(data, list):
        _fail(f"ccr/review_threads returned {type(data).__name__}, expected list")
    return data


def _comment_id(th: dict[str, Any]) -> int:
    raw = th.get("comment_id")
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        _fail(
            f"thread {th.get('thread_id') or '<no thread_id>'} has no usable "
            f"comment_id ({raw!r}) — REST surfaces key on comment_id, which "
            "ingest_signals.py sources from ccr/review_threads"
        )


def _reply_rest(repo: str, number: int, threads: list[dict[str, Any]]) -> int:
    calls = 0
    for th in threads:
        _rest(
            "POST",
            f"repos/{repo}/pulls/{number}/comments/{_comment_id(th)}/replies",
            {"body": th["body"]},
        )
        calls += 1
    return calls


def _resolve_rest(repo: str, number: int, threads: list[dict[str, Any]]) -> int:
    calls = 0
    for th in threads:
        cid = _comment_id(th)
        raw = _rest("POST", f"repos/{repo}/pulls/{number}/ccr/comments/{cid}/resolve")
        calls += 1
        try:
            if json.loads(raw).get("resolved") is not True:
                _fail(f"comment {cid}: resolve returned resolved!=true: {raw[:200]}")
        except json.JSONDecodeError:
            _fail(f"comment {cid}: resolve returned non-JSON: {raw[:200]}")
    return calls


def _chunks(items: list[Any], size: int) -> list[list[Any]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _th_label(th: dict[str, Any]) -> str:
    return str(th.get("thread_id") or th.get("comment_id") or "<unkeyed>")


def _require_inspected(prs: list[dict[str, Any]], *, summary_only: bool = False) -> None:
    # Key requirement is transport-dependent: GraphQL addresses a thread by its
    # node id, REST by a comment id, and ccr/review_threads cannot supply a node
    # id at all. Demand the key this surface can actually use.
    rest = _rest_only()
    key, other = ("comment_id", "thread_id") if rest else ("thread_id", "comment_id")
    for pr in prs:
        for th in pr.get("threads") or []:
            label = _th_label(th)
            if th.get("inspected") is not True:
                _fail(
                    f"PR #{pr.get('number')} thread {label} "
                    "missing inspected=true — read the cited file before reply"
                )
            disp = str(th.get("disposition") or "").lower()
            if disp not in VALID_DISPOSITIONS:
                _fail(f"PR #{pr.get('number')} thread {label} invalid disposition {disp!r}")
            if not summary_only and not str(th.get("body") or "").strip():
                _fail(f"PR #{pr.get('number')} thread {label} empty body")
            if not str(th.get(key) or "").strip():
                _fail(
                    f"PR #{pr.get('number')} thread {label} missing {key} "
                    f"({'REST' if rest else 'GraphQL'} surface). Ledgers carrying "
                    f"only {other} must be regenerated by ingest_signals.py"
                )


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


def _summary_markdown(
    pr: dict[str, Any],
    *,
    cycle: int,
    commit: str,
    verify: str,
    threads_resolved: int | None = None,
) -> str:
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
            finding = str(th.get("finding") or th.get("path") or _th_label(th)[-8:])
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
    if threads_resolved is None:
        footer = f"*Local verify: {verify} | Threads: replied (resolve not run this pass)*"
    else:
        footer = f"*Local verify: {verify} | Threads resolved: {threads_resolved}/{total}*"
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
        f"{footer}\n"
    )


def _post_summary(repo: str, number: int, body: str) -> None:
    # Native REST on every surface, not `gh pr comment`. That subcommand is one
    # of the GraphQL-backed `gh pr` forms a REST-only gateway refuses, and it is
    # absent from the guard list in ops/scripts/lib/gh_graphql.sh — so it failed
    # here while looking allowed. A PR comment is an issue comment; this route
    # is unconditional because it is correct on local CLI too.
    _rest("POST", f"repos/{repo}/issues/{number}/comments", {"body": body})


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

    rest = _rest_only()
    _log(f"transport: {'REST (ccr routes)' if rest else 'GraphQL (batched)'}")

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
            if rest:
                # No batch form on the REST routes: one call per thread, and
                # reply before resolve so a resolve failure never strands a
                # thread silently closed with no reply on it.
                _log(f"PR #{number}: reply via REST ({len(threads)})")
                gh_calls += _reply_rest(args.repo, number, threads)
                replied += len(threads)
                _log(f"PR #{number}: resolve via REST ({len(threads)})")
                gh_calls += _resolve_rest(args.repo, number, threads)
                resolved += len(threads)
            else:
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
            resolved_for_summary: int | None = None if args.summary_only else len(threads)
            _post_summary(
                args.repo,
                number,
                _summary_markdown(
                    pr,
                    cycle=cycle,
                    commit=commit,
                    verify=verify,
                    threads_resolved=resolved_for_summary,
                ),
            )
            gh_calls += 1
            summaries += 1

    _log(
        f"done transport={'rest' if rest else 'graphql'} replied={replied} "
        f"resolved={resolved} summaries={summaries} gh_calls={gh_calls} "
        f"timeout={GH_TIMEOUT_SEC}s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

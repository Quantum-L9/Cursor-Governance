#!/usr/bin/env python3
"""Last-step ``make pr`` memory handoff (operator CLI write).

``open_pr_after_gate.sh`` already knows the PR number, URL, and changed files
(``.l9/pr/pr-summary.json``). Downstream agents resume from the canonical
control plane, not from that local receipt. This hook writes one
``pickup_context`` fact so hydrate/search can answer "what just published,
and what is the next owned action?"

Caller taxonomy (ADR-0030): this is the operator / deterministic-adapter
form — ``python -m ops.memory.cli write``. It is not the model's
``write_governed`` path and it is never a reason to import a provider client.

Fail-open: a missing runtime, a refused write, or ``L9_PR_PUBLISH_MEMORY=0``
must not fail a PR that already opened. Exit 0 always.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = "l9.pr_publish_memory.v1"
SUMMARY_REL = Path(".l9/pr/pr-summary.json")
RECEIPT_REL = Path(".l9/pr/pr-publish-memory.json")
MAX_PATHS = 24
KIND = "pickup_context"

#: An unavailable memory plane must not hang the publish tail. The PR is
#: already open by the time this runs; the write is a handoff, not a gate.
WRITE_TIMEOUT_SECONDS = 20.0
TIMEOUT_RETURNCODE = 124

#: Strong keys that bind a cached summary to THIS publication. `.l9/pr/
#: pr-summary.json` survives in the workspace, so a summary left by an earlier
#: PR (or by the same PR at an earlier head) would otherwise be preferred over
#: the identity the caller just supplied, and the handoff would be written
#: under the previous PR's idempotency key.
IDENTITY_KEYS = ("repo", "number", "head_sha", "head")


def _enabled() -> bool:
    if os.environ.get("L9_PR_PUBLISH_MEMORY", "1").strip() == "0":
        return False
    memory = os.environ.get("L9_MEMORY_ENABLED") or os.environ.get("GRAPHITI_MEMORY_ENABLED")
    return (memory or "1").strip() != "0"


def _summary(workspace: Path, explicit: Path | None) -> dict[str, Any]:
    path = explicit if explicit is not None else workspace / SUMMARY_REL
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _identity(value: Any) -> str:
    return str(value).strip().casefold()


def _int_or(value: Any, default: int) -> int:
    """Coerce an externally supplied count, never raising."""
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def summary_identity_check(
    summary: dict[str, Any], current: dict[str, Any]
) -> tuple[bool, list[str], list[str]]:
    """Bind a cached summary to the current publication before trusting it.

    Returns ``(usable, mismatched, compared)``. A key is only compared when
    BOTH sides assert it: the current invocation supplies the live identity
    (``open_pr_after_gate.sh`` passes repo/number/head/head_sha), and a key the
    caller left empty cannot disprove anything. ``compared`` is empty when
    nothing could be checked, which is recorded rather than assumed correct.
    """
    mismatched: list[str] = []
    compared: list[str] = []
    for key in IDENTITY_KEYS:
        want, got = current.get(key), summary.get(key)
        if want in (None, "") or got in (None, ""):
            continue
        compared.append(key)
        if _identity(got) != _identity(want):
            mismatched.append(key)
    return (not mismatched), mismatched, compared


def _paths(summary: dict[str, Any]) -> list[str]:
    files = [row for row in (summary.get("files") or []) if isinstance(row, dict)]
    names: list[str] = []
    for row in files[:MAX_PATHS]:
        path = str(row.get("path") or "").strip()
        if not path:
            continue
        previous = str(row.get("previous_path") or "").strip()
        names.append(f"{previous}->{path}" if previous else path)
    return names


def format_fact(
    summary: dict[str, Any],
    *,
    remediates: bool,
    fallback: dict[str, Any] | None = None,
) -> str | None:
    """One terse resume fact. Empty only when there is no PR identity."""
    src = fallback or {}
    repo = str(summary.get("repo") or src.get("repo") or "").strip()
    number = summary.get("number") or src.get("number")
    if not repo or not number:
        return None
    url = str(summary.get("url") or src.get("url") or "").strip()
    title = str(summary.get("title") or src.get("title") or "").strip()
    base = str(summary.get("base") or src.get("base") or "").strip()
    head = str(summary.get("head") or src.get("head") or "").strip()
    sha = str(summary.get("head_sha") or src.get("head_sha") or "").strip()
    files_n = summary.get("changed_files")
    adds = summary.get("additions")
    dels = summary.get("deletions")
    paths = _paths(summary)
    # PR_REMEDIATE=0 is an authority boundary, not a cosmetic flag. A
    # publish-only run may record THAT a PR opened; it may not leave a durable
    # instruction telling the next agent to run the remediator, own every open
    # PR, or launch merge_now — that would convert an intentionally
    # publication-only operation into a repository-wide merge campaign the
    # operator declined. Merge stays separately authorized (CANONICAL_LAW;
    # rules/48, rules/88): the remediator is invoked by the user, not by a
    # fact this hook wrote.
    next_action = (
        "next=/l9-pr-remediation Converge (own until open_prs=0; launch merge_now). "
        "ceremony already requested a remediator spawn."
        if remediates
        else (
            "state=published-only. ceremony published with PR_REMEDIATE=0: "
            "no remediation scheduled and no merge authority conveyed."
        )
    )
    parts = [
        f"PICKUP: PR {repo}#{number} published.",
        f"url={url}" if url else "",
        f'title="{title}"' if title else "",
        f"base={base}" if base else "",
        f"head={head}" if head else "",
        f"sha={sha[:12]}" if sha else "",
        f"files={files_n} +{adds}/-{dels}" if files_n is not None else "",
        next_action,
    ]
    if paths:
        # `changed_files` comes from an external JSON receipt: a non-numeric or
        # malformed value must not raise out of a hook whose whole contract is
        # "exit 0 always". Fall back to what we can actually count.
        extra = _int_or(files_n, len(paths)) - len(paths)
        suffix = f" (+{extra} more)" if extra > 0 else ""
        parts.append("paths: " + " ".join(paths) + suffix)
    return " ".join(p for p in parts if p)


def idempotency_key(summary: dict[str, Any], fallback: dict[str, Any]) -> str:
    repo = str(summary.get("repo") or fallback.get("repo") or "unknown")
    number = summary.get("number") or fallback.get("number") or "0"
    sha = str(summary.get("head_sha") or fallback.get("head_sha") or "unknown")
    return f"pr-publish:{repo}#{number}@{sha}"


def _interpreter(gov_root: Path) -> Path:
    locked = gov_root / ".venv" / "bin" / "python"
    return locked if locked.is_file() else Path(sys.executable)


def write_argv(
    *,
    interpreter: Path,
    workspace: Path,
    content: str,
    key: str,
    agent_id: str,
    dry_run: bool,
) -> list[str]:
    argv = [
        str(interpreter),
        "-m",
        "ops.memory.cli",
        "write",
        content,
        "--kind",
        KIND,
        "--workspace",
        str(workspace),
        "--agent-id",
        agent_id,
        "--tag",
        "pr-publish",
        "--idempotency-key",
        key,
        "--source",
        "make-pr",
        "--source-id",
        key,
    ]
    if dry_run:
        argv.append("--dry-run")
    return argv


def run_write(
    argv: list[str], *, cwd: Path, timeout: float = WRITE_TIMEOUT_SECONDS
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(  # noqa: S603 — locked interpreter + fixed module
            argv,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        # Fail-open with a bound: the PR is already open, so a memory plane
        # that never answers becomes a WARN receipt, not a hung publish tail.
        return subprocess.CompletedProcess(
            argv, TIMEOUT_RETURNCODE, stdout="", stderr="memory CLI timed out"
        )


def _write_receipt(workspace: Path, body: dict[str, Any]) -> None:
    target = workspace / RECEIPT_REL
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError:
        # Fail-open: the receipt is evidence about a PR that already opened.
        # An unwritable workspace must not fail the publish.
        pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--gov-root", type=Path, required=True)
    parser.add_argument("--summary", type=Path, default=None)
    parser.add_argument("--pr-remediate", default="0")
    parser.add_argument("--repo", default="")
    parser.add_argument("--number", default="")
    parser.add_argument("--url", default="")
    parser.add_argument("--title", default="")
    parser.add_argument("--base", default="")
    parser.add_argument("--head", default="")
    parser.add_argument("--head-sha", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--agent-id", default="")
    args = parser.parse_args(argv)

    workspace = args.workspace.expanduser().resolve()
    gov_root = args.gov_root.expanduser().resolve()
    fallback = {
        "repo": args.repo,
        "number": int(args.number) if str(args.number).isdigit() else args.number,
        "url": args.url,
        "title": args.title,
        "base": args.base,
        "head": args.head,
        "head_sha": args.head_sha,
    }
    remediates = str(args.pr_remediate).strip() == "1"
    agent_id = args.agent_id or os.environ.get("L9_MEMORY_AGENT_ID") or "cursor"

    if not _enabled():
        print("pr publish memory: SKIP (disabled)")
        _write_receipt(
            workspace,
            {
                "schema": SCHEMA,
                "status": "SKIP",
                "reason": "disabled",
                "written_at": datetime.now(UTC).isoformat(),
            },
        )
        return 0

    summary = _summary(workspace, args.summary)
    usable, mismatched, compared = summary_identity_check(summary, fallback)
    if not usable:
        # A summary describing a DIFFERENT publication is not evidence about
        # this one. Discard it wholesale — its file list and counts belong to
        # that PR too — and fall back to the identity this invocation supplied.
        summary = {}
    fact = format_fact(summary, remediates=remediates, fallback=fallback)
    if not fact:
        print("pr publish memory: SKIP (no PR identity)")
        _write_receipt(
            workspace,
            {
                "schema": SCHEMA,
                "status": "SKIP",
                "reason": "no PR identity",
                "written_at": datetime.now(UTC).isoformat(),
            },
        )
        return 0

    key = idempotency_key(summary, fallback)
    argv_write = write_argv(
        interpreter=_interpreter(gov_root),
        workspace=workspace,
        content=fact,
        key=key,
        agent_id=agent_id,
        dry_run=args.dry_run,
    )
    proc = run_write(argv_write, cwd=gov_root)
    status = "OK" if proc.returncode == 0 else "WARN"
    preview = (proc.stdout or proc.stderr or "").strip().splitlines()
    tail = preview[-1] if preview else f"exit {proc.returncode}"
    print(f"pr publish memory: {status} ({tail[:200]})")
    _write_receipt(
        workspace,
        {
            "schema": SCHEMA,
            "status": status,
            "idempotency_key": key,
            "kind": KIND,
            "returncode": proc.returncode,
            "timed_out": proc.returncode == TIMEOUT_RETURNCODE,
            "remediates": remediates,
            "summary_identity": {
                "usable": usable,
                "mismatched": mismatched,
                "compared": compared,
                # Nothing comparable means the cached summary was accepted
                # without proof, which is recorded rather than presumed sound.
                "verified": bool(compared) and usable,
            },
            "written_at": datetime.now(UTC).isoformat(),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

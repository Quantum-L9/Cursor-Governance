#!/usr/bin/env python3
"""Above-paygrade issue body + optional create. Stdlib only.

Renders the handoff template from issue-handoff.md. --create calls
`gh issue create`. Does not merge, does not ask a human, and does not
launch the issue skill (that stays an agent Task).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

from protocol import HANDOFF_CLASSES, render_issue_body
from protocol import validated_output as _validated_output

GH_TIMEOUT_SEC = 30


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr, flush=True)
    raise SystemExit(1)


def _run_gh(argv: list[str]) -> str:
    try:
        proc = subprocess.run(  # noqa: S603
            argv,
            capture_output=True,
            text=True,
            timeout=GH_TIMEOUT_SEC,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        _fail(f"gh timed out after {GH_TIMEOUT_SEC}s: {exc}")
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()[-800:]
        _fail(f"gh exit {proc.returncode}: {err}")
    return proc.stdout.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render or create an above-paygrade issue.")
    parser.add_argument("--repo", required=True, help="owner/name")
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--class", dest="klass", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--best-effort", required=True)
    parser.add_argument("--why", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--create",
        action="store_true",
        help="call gh issue create (default is dry-run body only)",
    )
    args = parser.parse_args(argv)

    if args.klass not in HANDOFF_CLASSES:
        _fail(f"--class must be one of {sorted(HANDOFF_CLASSES)}")
    if "/" not in args.repo:
        _fail("--repo must be owner/name")

    body = render_issue_body(
        klass=args.klass,
        repo=args.repo,
        pr=args.pr,
        head=args.head,
        best_effort=args.best_effort,
        why=args.why,
    )
    title = f"{args.klass}: {args.title}"
    receipt = {
        "schema_version": "issue-handoff-1.0",
        "class": args.klass,
        "repo": args.repo,
        "pr": args.pr,
        "head": args.head,
        "title": title,
        "body": body,
        "downstream": "l9-issue-remediation",
        "launch_as": "generalPurpose",
        "created": False,
        "issue_url": None,
        "issue_number": None,
    }
    if args.create:
        url = _run_gh(
            [
                "gh",
                "issue",
                "create",
                "--repo",
                args.repo,
                "--title",
                title,
                "--body",
                body,
            ]
        )
        receipt["created"] = True
        receipt["issue_url"] = url
        if url.rstrip("/").split("/")[-1].isdigit():
            receipt["issue_number"] = int(url.rstrip("/").split("/")[-1])

    output = _validated_output(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"handoff: {output} class={args.klass} created={receipt['created']}", flush=True)
    if args.create and receipt["issue_url"]:
        print(receipt["issue_url"], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

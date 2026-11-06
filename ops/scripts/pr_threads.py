#!/usr/bin/env python3
"""Reply, resolve, or status-comment on the PR this checkout published.

Standing Claude Code allow is this command, not raw ``gh api --method POST``.
The body footer is appended here. Merge, approve, and force-push are not
subcommands.

    python3 ops/scripts/pr_threads.py reply --pr N --comment-id C
    python3 ops/scripts/pr_threads.py resolve --pr N --comment-id C
    python3 ops/scripts/pr_threads.py comment --pr N

``reply`` and ``comment`` read the body on stdin. The PR must be the open PR
named by ``.l9/pr/pr-summary.json``, and that receipt's repo must match origin.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from lib.pr_thread_routes import (  # noqa: E402
    comment,
    fail,
    origin_repo,
    reply,
    require_own_pr,
    resolve,
    run_gh,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("reply", "resolve", "comment"))
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--comment-id", type=int)
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="checkout that holds .l9/pr/pr-summary.json (default: cwd)",
    )
    return parser


def execute(
    argv: list[str] | None = None,
    *,
    workspace: Path | None = None,
    origin: str | None = None,
    run=run_gh,
    stdin: str | None = None,
) -> int:
    args = _parser().parse_args(argv)
    root = (workspace or args.workspace or Path.cwd()).resolve()
    if args.pr < 1:
        fail(f"--pr must be a positive integer, got {args.pr}")
    if args.action in {"reply", "resolve"}:
        if args.comment_id is None or args.comment_id < 1:
            fail(f"{args.action} requires --comment-id")
    elif args.comment_id is not None:
        fail("comment does not take --comment-id")
    slug = origin if origin is not None else origin_repo(root)
    if not slug:
        fail(f"origin repo is unresolved in {root}")
    require_own_pr(root, args.pr, slug)
    if args.action == "resolve":
        resolve(slug, args.pr, int(args.comment_id), run=run)
        return 0
    body = sys.stdin.read() if stdin is None else stdin
    if args.action == "reply":
        reply(slug, args.pr, int(args.comment_id), body, run=run)
        return 0
    comment(slug, args.pr, body, run=run)
    return 0


def main(argv: list[str] | None = None) -> int:
    return execute(argv)


if __name__ == "__main__":
    raise SystemExit(main())

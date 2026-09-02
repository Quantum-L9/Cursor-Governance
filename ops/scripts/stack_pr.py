#!/usr/bin/env python3
"""Stacked-PR helper: base selection and bottom-up merge order (operator policy).

Policy SSOT: ops/autonomy/surface_profile.yaml → pr_stacking +
environment/program-execution/campaigns/CAMPAIGN_EXECUTION_POLICY.yaml → pr_stacking.

Usage:
  stack_pr.py base --stack /path/to/STACK.json
      Print the next PR base from STACK.json. Never prints main.
  stack_pr.py base --repo org/repo [--prefix <branch-prefix>]
      Print the base ref for the next PR from STACK.json ($L9_ROOT +
      $CAMPAIGN_ID) or the newest open stacked PR. Fallback to main is exit 2.

  stack_pr.py order --repo org/repo [--prefix <branch-prefix>]
      Print open PRs in bottom-up merge order: base-first, then PRs whose base
      chains onto the previous PR head. Never rebase; never resolve conflicts.

Requires: gh CLI authenticated (sole-PAT rule: openclaw-igorbot/github#token).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def _gh(*args: str) -> Any:
    proc = subprocess.run(
        ["gh", "api", *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        print(f"stack_pr: gh api failed: {proc.stderr.strip()}", file=sys.stderr)
        raise SystemExit(1)
    text = proc.stdout.strip()
    if not text:
        return []
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text  # --jq string fields (e.g. default_branch) are not JSON


#: One page is 100 PRs. This repo runs ~17 open; a repo that exceeds the page
#: would silently order a truncated set, so a full page is reported rather than
#: assumed complete.
_PULLS_PAGE = 100


def open_prs(repo: str, prefix: str) -> list[dict[str, Any]]:
    """Open PRs for one repo as {number, title, head, base}, head/base as labels.

    Repo-scoped deliberately. This used ``search/issues?q=repo:...``, which is a
    CROSS-REPO endpoint: a session gateway bound to its configured repositories
    answers it 403 ("sessions are bound to their configured repositories"), so
    ``stack_pr.py order`` could not run at all there — at exactly the moment
    stack order matters, since rules 48/53 make bottom-up merge order a
    correctness requirement and PR_STACK=auto is the ``make pr`` default. The
    repo is known at call time, so nothing here ever needed org-wide reach.

    The 403 was also masking two defects that would have produced wrong answers
    rather than no answer:

    * search/issues returns ISSUE objects. The issues representation of a pull
      request carries no ``head`` and no ``base`` (only ``pull_request``), so
      the old projection yielded null for both fields on every hit. Ordering
      reads exactly those two fields.
    * ``--jq '.items[] | {...}'`` emits newline-delimited objects. ``_gh`` does a
      single ``json.loads``, which raises on two or more results and falls back
      to returning the raw STRING — after which ``cmd_order`` iterates characters
      and ``pr["base"]`` raises TypeError. It happened to work for exactly one
      open PR.

    Both are gone here: repos/{repo}/pulls returns real pull objects, and the
    ``[...]`` jq wrapper makes the payload a single JSON array.
    """
    prs = _gh(
        f"repos/{repo}/pulls?state=open&per_page={_PULLS_PAGE}",
        "--jq",
        "[.[] | {number, title, head: .head.label, base: .base.label, ref: .head.ref}]",
    )
    if not isinstance(prs, list):  # defensive: _gh degrades to str on bad JSON
        print(f"stack_pr: unexpected pulls payload for {repo}", file=sys.stderr)
        raise SystemExit(1)
    if len(prs) == _PULLS_PAGE:
        print(
            f"stack_pr: {repo} returned a full page of {_PULLS_PAGE} open PRs; "
            "ordering may be computed over a truncated set",
            file=sys.stderr,
        )
    if prefix:
        # search used `head:{prefix}`; the pulls endpoint's `head` filter wants an
        # exact user:ref, so the prefix match is applied here instead.
        prs = [pr for pr in prs if str(pr.get("ref") or "").startswith(prefix)]
    return [{k: v for k, v in pr.items() if k != "ref"} for pr in prs]


def refuse_unstacked_base(base: str) -> None:
    name = str(base).rsplit("/", 1)[-1]
    if name in {"main", "master"}:
        print(f"stack_pr: refuse unstacked PR_BASE={base}", file=sys.stderr)
        raise SystemExit(2)


def stack_path_from_env() -> Path | None:
    if os.environ.get("STACK_JSON"):
        path = Path(os.environ["STACK_JSON"])
        return path if path.is_file() else None
    l9 = os.environ.get("L9_ROOT")
    campaign_id = os.environ.get("CAMPAIGN_ID")
    if not l9 or not campaign_id:
        return None
    path = Path(l9) / "programs" / campaign_id / "runtime" / "STACK.json"
    return path if path.is_file() else None


def base_from_stack(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    stack = [item for item in (data.get("stack") or []) if isinstance(item, dict)]
    if not stack:
        print(f"stack_pr: {path} has an empty stack", file=sys.stderr)
        raise SystemExit(2)
    last_opened = None
    for item in stack:
        if item.get("pr_number"):
            last_opened = item
    if last_opened and last_opened.get("branch"):
        return str(last_opened["branch"])
    return str(stack[0].get("pr_base") or "")


def cmd_base(args: argparse.Namespace) -> int:
    stack_file = Path(args.stack) if args.stack else stack_path_from_env()
    if stack_file is not None:
        if not stack_file.is_file():
            print(f"stack_pr: STACK.json missing: {stack_file}", file=sys.stderr)
            return 2
        base = base_from_stack(stack_file)
        if not base:
            print("stack_pr: STACK.json has no pr_base", file=sys.stderr)
            return 2
        refuse_unstacked_base(base)
        print(base)
        return 0
    if not args.repo:
        print("stack_pr: STACK.json required; refuse default_branch fallback", file=sys.stderr)
        return 2
    prs = open_prs(args.repo, args.prefix)
    if not prs:
        print("stack_pr: STACK.json required; refuse default_branch fallback", file=sys.stderr)
        return 2
    newest = sorted(prs, key=lambda p: int(p["number"]))[-1]
    refuse_unstacked_base(str(newest["head"]))
    print(newest["head"])
    return 0


def cmd_order(args: argparse.Namespace) -> int:
    prs = open_prs(args.repo, args.prefix)
    if not prs:
        print("no open PRs")
        return 0
    by_base: dict[str, list[dict[str, Any]]] = {}
    for pr in prs:
        by_base.setdefault(pr["base"], []).append(pr)
    # Bottom-up: start from PRs based on main/default, then chain heads.
    repo_meta = _gh(f"repos/{args.repo}", "--jq", ".default_branch")
    default_branch = repo_meta
    queue = [default_branch]
    ordered: list[dict[str, Any]] = []
    seen: set[int] = set()
    while queue:
        base = queue.pop(0)
        chained = sorted(by_base.get(base, []), key=lambda p: int(p["number"]))
        for pr in chained:
            if pr["number"] in seen:
                continue
            seen.add(pr["number"])
            ordered.append(pr)
            queue.append(pr["head"])
    for pr in ordered:
        print(f"#{pr['number']}  {pr['head']}  (base: {pr['base']})  {pr['title']}")
    remaining = [p for p in prs if p["number"] not in seen]
    for pr in remaining:
        print(
            f"#{pr['number']}  {pr['head']}  (base: {pr['base']}, off-chain — policy review)  "
            f"{pr['title']}"
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_base = sub.add_parser("base")
    p_base.add_argument("--repo", default="")
    p_base.add_argument("--prefix", default="")
    p_base.add_argument("--stack", default="", help="Path to pec runtime STACK.json")
    p_order = sub.add_parser("order")
    p_order.add_argument("--repo", required=True)
    p_order.add_argument("--prefix", default="")
    args = parser.parse_args()
    if args.cmd == "base":
        return cmd_base(args)
    return cmd_order(args)


if __name__ == "__main__":
    raise SystemExit(main())

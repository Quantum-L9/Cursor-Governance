#!/usr/bin/env python3
"""Stacked-PR helper: base selection and bottom-up merge order (operator policy).

Policy SSOT: ops/autonomy/surface_profile.yaml → pr_stacking +
environment/program-execution/campaigns/CAMPAIGN_EXECUTION_POLICY.yaml → pr_stacking.

Usage:
  stack_pr.py base --repo org/repo [--prefix <branch-prefix>]
      Print the base ref for the next PR: the head ref of the newest open PR
      whose head branch matches the prefix, else "main" (or the repo default
      branch).

  stack_pr.py order --repo org/repo [--prefix <branch-prefix>]
      Print open PRs in bottom-up merge order: base-first, then PRs whose base
      chains onto the previous PR head. Never rebase; never resolve conflicts.

Requires: gh CLI authenticated (sole-PAT rule: openclaw-igorbot/github#token).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
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
    return json.loads(proc.stdout)


def open_prs(repo: str, prefix: str) -> list[dict[str, Any]]:
    query = f"repo:{repo} is:pr is:open"
    if prefix:
        query += f" head:{prefix}"
    return _gh(
        "search/issues",
        "-f",
        f"q={query}",
        "--jq",
        ".items[] | {number, title, head: .head.label, base: .base.label}",
    )


def cmd_base(args: argparse.Namespace) -> int:
    prs = open_prs(args.repo, args.prefix)
    if not prs:
        repo_meta = _gh(f"repos/{args.repo}", "--jq", ".default_branch")
        print(repo_meta)
        return 0
    newest = sorted(prs, key=lambda p: int(p["number"]))[-1]
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
    p_base.add_argument("--repo", required=True)
    p_base.add_argument("--prefix", default="")
    p_order = sub.add_parser("order")
    p_order.add_argument("--repo", required=True)
    p_order.add_argument("--prefix", default="")
    args = parser.parse_args()
    if args.cmd == "base":
        return cmd_base(args)
    return cmd_order(args)


if __name__ == "__main__":
    raise SystemExit(main())

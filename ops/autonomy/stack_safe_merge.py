#!/usr/bin/env python3
"""Select a stack-safe `gh pr merge` method. Never guess --squash.

Squash/rebase of a head that is the base of another open PR orphans the child
and can delete-wins the child's unique files with no conflict. This helper is
the only sanctioned way for l9-pr-remediation to choose a merge method.

    select --json     machine record (method, children, argv)
    select --print    argv only (default)
    --run             exec that argv (does not merge when children exist
                      unless method is merge)

Probe: L9_STACK_PROBE_FILE (tests) or live `gh pr view` / `gh pr list`.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from merge_gate import _stacked_children  # noqa: E402

ANCESTRY_SAFE = "merge"
UNSTACKED = "squash"


def select_merge_method(repo: str, pr: str) -> dict[str, Any]:
    """Return method, head, children. Raises RuntimeError if the probe fails."""
    head, children = _stacked_children(repo, str(pr))
    method = ANCESTRY_SAFE if children else UNSTACKED
    return {
        "repo": repo,
        "pr": int(pr) if str(pr).isdigit() else pr,
        "head": head,
        "children": children,
        "method": method,
        "reason": (
            f"head '{head}' is the base of open PR(s) "
            + ", ".join(f"#{c}" for c in children)
            + "; --merge preserves ancestry"
            if children
            else "no open PR bases on this head; --squash is safe"
        ),
    }


def merge_argv(
    repo: str,
    pr: str,
    *,
    delete_branch: bool = True,
    selection: dict[str, Any] | None = None,
) -> list[str]:
    chosen = selection or select_merge_method(repo, str(pr))
    argv = [
        "gh",
        "pr",
        "merge",
        str(pr),
        "--repo",
        repo,
        f"--{chosen['method']}",
    ]
    if delete_branch:
        argv.append("--delete-branch")
    return argv


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="owner/name")
    parser.add_argument("--pr", required=True, help="pull request number")
    parser.add_argument(
        "--keep-branch",
        action="store_true",
        help="omit --delete-branch",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--print", action="store_true", dest="print_argv", help="print argv")
    mode.add_argument("--json", action="store_true", help="print selection JSON")
    mode.add_argument("--run", action="store_true", help="exec the selected gh pr merge")
    args = parser.parse_args(argv)

    try:
        selection = select_merge_method(args.repo, args.pr)
    except RuntimeError as exc:
        print(f"FAIL: stack probe: {exc}", file=sys.stderr)
        return 2

    command = merge_argv(
        args.repo,
        args.pr,
        delete_branch=not args.keep_branch,
        selection=selection,
    )
    selection["argv"] = command

    if args.json:
        print(json.dumps(selection, indent=2, sort_keys=True))
        return 0
    if args.run:
        if os.environ.get("L9_STACK_SAFE_MERGE_DRY_RUN", "").strip():
            print(" ".join(command))
            return 0
        completed = subprocess.run(command, check=False)  # noqa: S603
        return int(completed.returncode)
    print(" ".join(command))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

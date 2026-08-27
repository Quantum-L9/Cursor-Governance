#!/usr/bin/env python3
"""Select a stack-safe merge method and execute it. Never guess --squash.

Squash/rebase of a head that is the base of another open PR orphans the child
and can delete-wins the child's unique files with no conflict. This helper is
the only sanctioned way for l9-pr-remediation to choose a merge method.

    select --json     machine record (method, children, argv, rest_argv)
    select --print    argv only (default)
    --run             execute the merge (does not merge when children exist
                      unless method is merge)

Two execution transports, same order as the probe above it:

  1. REST -- PUT /repos/{owner}/{repo}/pulls/{n}/merge, plus an explicit ref
     delete when the branch is meant to go. This leads because it is the
     transport that survives a session gateway serving only a pinned set of
     GraphQL operations, where the CLI subcommand returns 403.
  2. The `gh pr merge` subcommand -- kept so a surface where the reverse holds
     still gets an answer, and because it deletes the branch in one call.

Widening how a merge can be *executed* does not widen who may execute one.
merge_gate recognises both spellings, so a REST merge is gated exactly like the
CLI one; that recognition shipped with this transport, not after it.

Probe: L9_STACK_PROBE_FILE (tests) or live REST / `gh pr view` / `gh pr list`.
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


def merge_rest_argv(repo: str, pr: str, method: str) -> list[str]:
    """The REST merge call. Method travels as a field, not a flag."""
    return [
        "gh",
        "api",
        "--method",
        "PUT",
        f"repos/{repo}/pulls/{pr}/merge",
        "-f",
        f"merge_method={method}",
    ]


def delete_ref_argv(repo: str, head: str) -> list[str]:
    """Delete the merged head branch.

    The REST merge endpoint does not delete the branch, while `gh pr merge
    --delete-branch` does. Without this the REST transport would quietly stop
    honouring --delete-branch -- a behaviour difference between transports is
    exactly the kind of thing that gets discovered months later.
    """
    return ["gh", "api", "--method", "DELETE", f"repos/{repo}/git/refs/heads/{head}"]


def _run(argv: list[str]) -> int:
    return int(subprocess.run(argv, check=False).returncode)  # noqa: S603


def _execute(selection: dict[str, Any], *, delete_branch: bool) -> int:
    """Merge over REST, falling back to the CLI subcommand. Report honestly.

    A non-zero REST result is not assumed to be a transport problem: an
    unmergeable PR fails here too. The CLI attempt follows regardless, and its
    status is the one returned, so a genuinely refused merge stays refused
    rather than being reported as a transport quirk.
    """
    repo = str(selection["repo"])
    pr = str(selection["pr"])
    method = str(selection["method"])
    head = str(selection.get("head") or "")

    rc = _run(merge_rest_argv(repo, pr, method))
    transport = "rest"
    if rc != 0:
        print(
            f"NOTE: REST merge returned {rc}; retrying over the gh pr merge subcommand",
            file=sys.stderr,
        )
        rc = _run(merge_argv(repo, pr, delete_branch=delete_branch, selection=selection))
        transport = "cli"
        if rc == 0:
            return 0
        print(f"FAIL: merge failed on both transports (last exit {rc})", file=sys.stderr)
        return rc

    if delete_branch and transport == "rest":
        if not head:
            print(
                "WARN: merged, but the head branch name is unknown so it was not deleted",
                file=sys.stderr,
            )
        elif _run(delete_ref_argv(repo, head)) != 0:
            # The merge landed. Say the branch survived; do not fail the merge.
            print(
                f"WARN: merged, but deleting branch '{head}' failed — delete it manually",
                file=sys.stderr,
            )
    return 0


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
    selection["rest_argv"] = merge_rest_argv(args.repo, args.pr, selection["method"])

    if args.json:
        print(json.dumps(selection, indent=2, sort_keys=True))
        return 0
    if args.run:
        if os.environ.get("L9_STACK_SAFE_MERGE_DRY_RUN", "").strip():
            # Print what would actually run, in attempt order, so a dry run is
            # evidence about the live path rather than about one transport.
            print(" ".join(selection["rest_argv"]))
            print(" ".join(command))
            return 0
        return _execute(selection, delete_branch=not args.keep_branch)
    print(" ".join(command))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

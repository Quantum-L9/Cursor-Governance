#!/usr/bin/env python3
"""Select a stack-safe merge method and execute it. Never guess --squash.

Squash/rebase of a head that is the base of another open PR orphans the child
and can delete-wins the child's unique files with no conflict. This helper is
the only sanctioned way for l9-pr-remediation to choose a merge method.

    select --json     machine record (method, children, argv, rest_argv, and
                      the live head plus its authorization status)
    select --print    argv only (default)
    --run --head-sha  execute the merge (does not merge when children exist
                      unless method is merge)

Authorization (CANONICAL_LAW §6.2.12). ``--run`` merges only under a live human
merge grant for exactly this repository, PR and head. Before merging it rechecks
the PR's current head on GitHub: a head that differs from ``--head-sha``, or no
grant for that head, prints a MERGE_PENDING record and exits MERGE_PENDING_EXIT
without merging. The SHA then travels with the merge (REST ``sha``, CLI
``--match-head-commit``) so GitHub itself refuses a head that moves in between.
The grant is read from the invoking account's home as recorded in the password
database, not from ``$HOME`` or ``L9_MERGE_AUTHORIZATION_FILE``: this process's
environment belongs to whoever runs it, and an agent controls that. The human
session breakglass L9_MERGE_AUTHORIZED is honoured by merge_gate's hook, not
here, for the same reason.

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
import pwd
import subprocess
import sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from merge_gate import (  # noqa: E402
    GRANT_COMMAND,
    GRANT_FILE_NAME,
    _stacked_children,
    find_grant,
    live_head_sha,
)

ANCESTRY_SAFE = "merge"
UNSTACKED = "squash"
#: Exit status for "remediated, not merged: a human grant is required".
MERGE_PENDING_EXIT = 3


def _account_grant_path() -> Path:
    """The grant file under the account's home from the password database."""
    home = Path(pwd.getpwuid(os.getuid()).pw_dir)
    return home / ".l9" / "autonomy" / GRANT_FILE_NAME


def authorization_status(
    repo: str, pr: str, requested_sha: str, *, path: Path | None = None
) -> dict[str, Any]:
    """AUTHORIZED only for a live human grant on the PR's current head.

    Rechecks GitHub first, so a grant for an older head, or a caller naming a
    head that is no longer current, returns MERGE_PENDING rather than merging.
    """
    requested = requested_sha.strip().lower()
    record: dict[str, Any] = {
        "repo": repo,
        "pr": int(pr) if str(pr).isdigit() else pr,
        "requested_head_sha": requested or None,
    }
    try:
        live = live_head_sha(repo, str(pr))
    except RuntimeError as exc:
        return {
            **record,
            "status": "MERGE_PENDING",
            "head_sha": None,
            "reason": f"cannot recheck the live head ({exc})",
        }
    record["head_sha"] = live
    if not requested:
        reason = "no --head-sha named; a grant binds an exact head"
    elif requested != live:
        reason = f"head moved: requested {requested}, live {live}"
    elif find_grant(repo, str(pr), live, path=path or _account_grant_path()) is None:
        reason = "no live human merge grant for this repository, PR and head"
    else:
        return {**record, "status": "AUTHORIZED", "reason": "human grant matches live head"}
    return {
        **record,
        "status": "MERGE_PENDING",
        "reason": reason,
        "grant_command": (f"{GRANT_COMMAND} --repo {repo} --pr {pr} --head-sha {live}"),
    }


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
    head_sha: str = "",
) -> list[str]:
    chosen = selection or select_merge_method(repo, str(pr))
    if chosen.get("children"):
        delete_branch = False
    argv = [
        "gh",
        "pr",
        "merge",
        str(pr),
        "--repo",
        repo,
        f"--{chosen['method']}",
    ]
    if head_sha:
        argv += ["--match-head-commit", head_sha]
    if delete_branch:
        argv.append("--delete-branch")
    return argv


def merge_rest_argv(repo: str, pr: str, method: str, head_sha: str = "") -> list[str]:
    """The REST merge call. Method travels as a field, not a flag.

    ``sha`` makes GitHub refuse the merge if the head moved after the grant.
    """
    argv = [
        "gh",
        "api",
        "--method",
        "PUT",
        f"repos/{repo}/pulls/{pr}/merge",
        "-f",
        f"merge_method={method}",
    ]
    if head_sha:
        argv += ["-f", f"sha={head_sha}"]
    return argv


def delete_ref_argv(repo: str, head: str) -> list[str]:
    """Delete the merged head branch.

    The REST merge endpoint does not delete the branch, while `gh pr merge
    --delete-branch` does. Without this the REST transport would quietly stop
    honouring --delete-branch -- a behaviour difference between transports is
    exactly the kind of thing that gets discovered months later.
    """
    return ["gh", "api", "--method", "DELETE", f"repos/{repo}/git/refs/heads/{head}"]


def ref_exists_argv(repo: str, head: str) -> list[str]:
    """GET the head ref after a failed DELETE.

    A proxy 403 on DELETE is not proof the branch survived. Ask the API
    whether the ref still exists before telling an operator to delete it.
    """
    return ["gh", "api", f"repos/{repo}/git/refs/heads/{head}"]


def _run(argv: list[str]) -> int:
    return int(subprocess.run(argv, check=False).returncode)  # noqa: S603


def _execute(selection: dict[str, Any], *, delete_branch: bool, head_sha: str = "") -> int:
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
    if selection.get("children"):
        delete_branch = False

    rc = _run(merge_rest_argv(repo, pr, method, head_sha))
    if rc != 0:
        print(
            f"NOTE: REST merge returned {rc}; retrying over the gh pr merge subcommand",
            file=sys.stderr,
        )
        # The CLI carries --delete-branch itself, so this path needs no explicit
        # ref delete and returns either way -- which is why the block below runs
        # only after a REST merge.
        rc = _run(
            merge_argv(
                repo, pr, delete_branch=delete_branch, selection=selection, head_sha=head_sha
            )
        )
        if rc == 0:
            return 0
        print(f"FAIL: merge failed on both transports (last exit {rc})", file=sys.stderr)
        return rc

    if delete_branch:
        if not head:
            print(
                "WARN: merged, but the head branch name is unknown so it was not deleted",
                file=sys.stderr,
            )
        elif _run(delete_ref_argv(repo, head)) != 0:
            # DELETE failed. A 403 from a session proxy is not leftover proof.
            if _run(ref_exists_argv(repo, head)) != 0:
                print(
                    f"NOTE: merged, and branch '{head}' is already absent "
                    "(delete returned non-zero)",
                    file=sys.stderr,
                )
            else:
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
    parser.add_argument(
        "--head-sha",
        default="",
        help="exact head the human grant covers; required by --run",
    )
    args = parser.parse_args(argv)

    try:
        selection = select_merge_method(args.repo, args.pr)
    except RuntimeError as exc:
        print(f"FAIL: stack probe: {exc}", file=sys.stderr)
        return 2

    if args.json or args.run:
        selection["authorization"] = authorization_status(args.repo, args.pr, args.head_sha)
    bound_sha = ""
    if args.run:
        auth = selection["authorization"]
        if auth["status"] != "AUTHORIZED":
            print(json.dumps({**auth, "method": selection["method"]}, indent=2, sort_keys=True))
            print(
                f"MERGE_PENDING: {args.repo}#{args.pr} not merged — {auth['reason']}",
                file=sys.stderr,
            )
            return MERGE_PENDING_EXIT
        bound_sha = str(auth["head_sha"])

    command = merge_argv(
        args.repo,
        args.pr,
        delete_branch=not args.keep_branch,
        selection=selection,
        head_sha=bound_sha,
    )
    selection["argv"] = command
    selection["rest_argv"] = merge_rest_argv(args.repo, args.pr, selection["method"], bound_sha)

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
        return _execute(selection, delete_branch=not args.keep_branch, head_sha=bound_sha)
    print(" ".join(command))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

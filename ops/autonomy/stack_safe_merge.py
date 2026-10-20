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

Authorization (CANONICAL_LAW §6.2.13). ``--run`` merges only when a human
authorization covers exactly this repository, PR and current head: a GitHub
record (approval or authorization line), or a grant in the account's grant
file -- written by ``authorize_merge.py`` from a controlling terminal or, as
``--operator-instruction``, from the operator's own recorded prompt. Before
merging it rechecks the PR's current head on GitHub: a head that differs from
``--head-sha``, or no authorization for that head, prints a MERGE_PENDING
record and exits MERGE_PENDING_EXIT without merging. An operator cancellation
("do not merge #n", "cancel the merge of #n") recorded by the host prompt hook
after a grant was issued, or while a GitHub record stands, is MERGE_PENDING
too: the latest instruction wins, and the cancellation is read from the same
account-home receipt store on every run, so it survives a restart. The SHA then travels with
the merge (REST ``sha``, CLI ``--match-head-commit``) so GitHub itself refuses
a head that moves in between. After a merge returns success the helper reads
the pull request back and reports ``MERGED`` with GitHub's merge commit; a
merge GitHub does not confirm exits MERGE_UNVERIFIED_EXIT rather than being
reported as done. GitHub evidence is read from GitHub, not from
``L9_MERGE_REVIEW_FILE``. The grant is read from the invoking account's home as
recorded in the password database, not from ``$HOME`` or
``L9_MERGE_AUTHORIZATION_FILE``: this process's environment belongs to whoever
runs it, and an agent controls that. The human session breakglass
L9_MERGE_AUTHORIZED is honoured by merge_gate's hook, not here, for the same
reason. Failing required checks stay GitHub's refusal: a non-zero merge API
result is returned, not overridden.

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

import merge_authority_switch  # noqa: E402
import operator_merge_instruction as omi  # noqa: E402
from github_merge_authorization import authorization_line, authorize_for_merge  # noqa: E402
from merge_gate import (  # noqa: E402
    _FULL_SHA,
    GRANT_FILE_NAME,
    _gh_rest_json,
    _probe_file_entry,
    _stacked_children,
    find_grant,
    live_head_sha,
)

ANCESTRY_SAFE = "merge"
UNSTACKED = "squash"
#: Exit status for "remediated, not merged: a human grant is required".
MERGE_PENDING_EXIT = 3
#: Exit status for "the merge call returned success but GitHub does not show it merged".
MERGE_UNVERIFIED_EXIT = 4


def _account_grant_path() -> Path:
    """The grant file under the account's home from the password database."""
    home = Path(pwd.getpwuid(os.getuid()).pw_dir)
    return home / ".l9" / "autonomy" / GRANT_FILE_NAME


def _instruction_store_path() -> Path:
    """The host-recorded operator instructions under the account's home (as the grant is)."""
    return omi.account_store_path()


def _github_authorization(repo: str, pr: str, head_sha: str) -> dict[str, Any]:
    """Live GitHub verdict. Tests replace this; production does not read a fixture."""
    return authorize_for_merge(repo, pr, head_sha)


def _revocation(repo: str, pr: str, *, since: float | None = None) -> dict[str, Any] | None:
    """The operator's live cancellation of ``repo#pr`` recorded at or after ``since``.

    "Do not merge #n" / "cancel the merge of #n", recorded by the same host
    prompt hook as the instruction it withdraws, outranks every authority
    issued before it -- a grant (``since`` is its ``issued_at``) and, lacking a
    comparable issue time, a GitHub record -- until the operator authorizes
    again.
    """
    return omi.revocation_for(repo, str(pr), path=_instruction_store_path(), since=since)


def authorization_status(
    repo: str, pr: str, requested_sha: str, *, path: Path | None = None
) -> dict[str, Any]:
    """AUTHORIZED only for human authorization on the PR's current head.

    Rechecks GitHub first, so an approval or grant for an older head, or a
    caller naming a head that is no longer current, returns MERGE_PENDING
    rather than merging. A legacy grant file still counts; it is not required
    when GitHub already records the human authorization.
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
    line = authorization_line(repo, pr, live) if live else ""
    grant = find_grant(repo, str(pr), live, path=path or _account_grant_path()) if live else None
    issued = grant.get("issued_at") if grant else None
    since = (
        float(issued) if isinstance(issued, (int, float)) and not isinstance(issued, bool) else None
    )
    if not requested:
        reason = "no --head-sha named; authorization binds an exact head"
    elif requested != live:
        reason = f"head moved: requested {requested}, live {live}"
    elif merge_authority_switch.disabled():
        return {
            **record,
            "status": "AUTHORIZED",
            "reason": "merge-authority enforcement disabled (CANONICAL_LAW §6.2.16)",
            "channel": "enforcement_disabled",
            "authorizer": "operator",
        }
    elif grant is not None and (revoked := _revocation(repo, pr, since=since)) is not None:
        reason = omi.revocation_reason(revoked)
    elif grant is not None:
        provenance = grant.get("provenance") if isinstance(grant.get("provenance"), dict) else {}
        channel = str(provenance.get("channel") or "human_grant")
        return {
            **record,
            "status": "AUTHORIZED",
            "reason": f"human grant ({channel}) matches live head",
            "channel": channel,
            "authorizer": "operator" if channel == "operator_prompt" else "human",
            "grant_provenance": provenance or None,
        }
    else:
        github = _github_authorization(repo, str(pr), live)
        revoked = _revocation(repo, pr) if github.get("authorized") else None
        if github.get("authorized") and revoked is None:
            return {
                **record,
                "status": "AUTHORIZED",
                "reason": str(
                    github.get("reason") or "human GitHub authorization matches live head"
                ),
                "channel": github.get("channel"),
                "authorizer": github.get("authorizer"),
            }
        if revoked is not None:
            reason = omi.revocation_reason(revoked)
        else:
            reason = str(
                github.get("reason")
                or "no human GitHub merge authorization for this repository, PR and head"
            )
    return {
        **record,
        "status": "MERGE_PENDING",
        "reason": reason,
        "grant_command": line,
        "missing_prerequisite": (
            f"A human with write access posts this exact line on the pull request, "
            f"or submits an APPROVED review on {live}: {line}"
        ),
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


def merged_state(repo: str, pr: str) -> dict[str, Any]:
    """GitHub's view of whether ``repo#pr`` is merged, and by which commit.

    ``L9_STACK_PROBE_FILE`` entries may carry ``merged`` / ``merge_commit_sha``
    so tests stay offline. Raises RuntimeError when the state cannot be read:
    an unobserved merge is never reported as a merge.
    """
    entry = _probe_file_entry(repo, str(pr))
    if entry is not None:
        merged = bool(entry.get("merged"))
        sha = str(entry.get("merge_commit_sha") or "").strip().lower()
        return {"merged": merged, "merge_commit_sha": sha or None}
    view = _gh_rest_json(f"repos/{repo}/pulls/{pr}")
    if not isinstance(view, dict):
        raise RuntimeError("pull request payload was not an object")
    sha = str(view.get("merge_commit_sha") or "").strip().lower()
    return {
        "merged": bool(view.get("merged")),
        "merge_commit_sha": sha if _FULL_SHA.match(sha) else None,
        "state": view.get("state"),
    }


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
        rc = _execute(selection, delete_branch=not args.keep_branch, head_sha=bound_sha)
        if rc != 0:
            return rc
        # "The merge command returned 0" is not "the pull request merged". Read
        # the result back from GitHub before reporting it.
        try:
            observed = merged_state(args.repo, args.pr)
        except RuntimeError as exc:
            print(
                f"UNVERIFIED: merge call succeeded but GitHub state could not be read ({exc})",
                file=sys.stderr,
            )
            return MERGE_UNVERIFIED_EXIT
        if not observed.get("merged"):
            print(
                f"UNVERIFIED: merge call succeeded but GitHub does not show {args.repo}#{args.pr} "
                "as merged",
                file=sys.stderr,
            )
            return MERGE_UNVERIFIED_EXIT
        print(
            json.dumps(
                {
                    "status": "MERGED",
                    "repo": args.repo,
                    "pr": int(args.pr) if str(args.pr).isdigit() else args.pr,
                    "head_sha": bound_sha,
                    "merge_commit_sha": observed.get("merge_commit_sha"),
                    "method": selection["method"],
                    "authorization": selection["authorization"],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    print(" ".join(command))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

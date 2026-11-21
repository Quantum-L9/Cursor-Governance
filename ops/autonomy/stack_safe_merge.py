#!/usr/bin/env python3
"""Select a stack-safe merge method and execute it. Never guess --squash.

Squash/rebase of a head that is the base of another open PR orphans the child
and can delete-wins the child's unique files with no conflict. This helper is
the only sanctioned way for l9-pr-remediation to choose a merge method.

A long-lived head -- the default branch, a protected branch, a branch whose
rules forbid deletion, force-push or update, or a long-lived name such as
``Staging`` promoted into ``Production`` -- also merges with a merge commit and
is never deleted, on either transport and whatever ``--keep-branch`` says.
Squashing a promotion splits the two branches' histories (the next promotion
re-lists shipped commits and conflicts on every line touched twice), and
deleting its head removes a branch that is meant to last. When those signals
cannot be read the head is treated as long-lived.

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

Merge queue (``--queue ITEM...``, ITEM = ``<pr>@<head-sha>``)
--------------------------------------------------------------
When the base branch's rules (``GET repos/{o}/{r}/rules/branches/{base}``) carry
a ``merge_queue`` rule, a direct merge is refused by GitHub, so the set is handed
to the queue instead. Every item must be on that queue-protected base, have
``board=merge`` (pr_board) and authorization for the granted head
(``authorization_status``, the same check ``--run`` uses, so it holds with the
merge-authority switch disabled or strict). Items are enqueued in the order
given -- the caller passes ``merge_order``, bottom-up -- and then ONE watcher
polls the set until each PR is merged, ejected or stopped. A base without the
rule is refused here; ``--run`` keeps today's direct merge unchanged.

Head binding is enforced in this code, not assumed from GitHub:

* An enqueue counts only when the PR is observed in the queue at the granted
  head right after the call. Anything else -- armed auto-merge waiting for
  requirements, an unobservable state -- is disarmed and reported
  MERGE_PENDING. Auto-merge is never left armed.
* While queued, the watcher re-reads the head and re-checks authorization on
  every poll, so a moved head or a cancelled instruction withdraws the entry.
* Every withdrawal -- an enqueue not proven at the granted head, a moved head, a
  revoked authorization, a watcher timeout -- runs ``withdraw``: dequeue
  (GraphQL ``dequeuePullRequest``; on the REST-only gateway
  ``DELETE pulls/{n}/ccr/auto_merge``) and disarm, then re-read. Only an entry
  observably neither queued nor armed is reported MERGE_PENDING. Anything else is
  UNBOUND_QUEUE_ENTRY (exit 5): it is recorded in the account's unbound-entry
  ledger, the rest of the set is not enqueued, and no further enqueue runs for
  that repository until the entry has left the queue.

UNKNOWN, settled empirically by the operator-run check in the X8 pull request:
(i) whether GitHub removes a queued PR when its head is pushed -- the
documented removal reasons (failing merge-group CI, timeout, removal by API or
UI, unresolvable branch protection) do not name a push, and the auto-merge
page says a push by someone with write access leaves auto-merge enabled;
(ii) whether ``DELETE ccr/auto_merge`` dequeues a queued PR; (iii) whether the
REST issue timeline reports ``added_to_merge_queue`` / ``removed_from_merge_queue``
(GitHub documents queue membership only over GraphQL: ``isInMergeQueue``,
``mergeQueueEntry.headCommit``). Until (iii) is proven, a REST-only enqueue
whose membership cannot be observed is disarmed, never assumed queued.
"""

from __future__ import annotations

import argparse
import json
import os
import pwd
import subprocess
import sys
import urllib.parse
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
#: Branch names that are long-lived by convention, compared case-insensitively.
LONG_LIVED_NAMES = frozenset({"main", "master", "staging", "production", "develop", "development"})
LONG_LIVED_PREFIXES = ("release/",)
#: Branch rule types that only make sense on a branch meant to last. An org
#: ruleset can put `workflows` or `required_status_checks` on every branch, so
#: those are deliberately not on this list: they would make every feature PR
#: look long-lived and stop squash everywhere.
LONG_LIVED_RULE_TYPES = frozenset({"deletion", "non_fast_forward", "update"})
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


def _long_lived_name(head: str) -> bool:
    name = head.strip().lower()
    return name in LONG_LIVED_NAMES or name.startswith(LONG_LIVED_PREFIXES)


def long_lived_head(repo: str, pr: str, head: str) -> dict[str, Any]:
    """Whether the PR's head branch is meant to outlive this merge.

    A promotion (``Staging`` -> ``Production``) has no stacked children, yet
    squashing it splits the two branches' histories and deleting its head
    removes a long-lived branch. A head is long-lived when it is the
    repository's default branch, GitHub reports it protected, its branch rules
    forbid deletion, force-push or update, or its name is a long-lived
    convention.

    Fails safe: when the signals cannot be read the head counts as long-lived,
    so the merge keeps ancestry and the branch survives. A merge commit is
    never wrong; a deleted long-lived branch cannot be taken back.

    ``L9_STACK_PROBE_FILE`` entries may carry ``default_branch``, ``protected``
    and ``rules`` (rule type names) so tests stay offline; an entry without
    them is read as an ordinary feature branch.
    """
    reasons: list[str] = []
    if not head:
        return {"long_lived": True, "reasons": ["head branch name is unknown"]}
    if _long_lived_name(head):
        reasons.append(f"'{head}' is a long-lived branch name")
    entry = _probe_file_entry(repo, str(pr))
    if entry is not None:
        default = str(entry.get("default_branch") or "")
        protected = bool(entry.get("protected"))
        rules = {str(r) for r in entry.get("rules") or []}
    else:
        branch = urllib.parse.quote(head, safe="")
        try:
            meta = _gh_rest_json(f"repos/{repo}")
            default = str((meta or {}).get("default_branch") or "")
            info = _gh_rest_json(f"repos/{repo}/branches/{branch}")
            protected = bool((info or {}).get("protected"))
            listing = _gh_rest_json(f"repos/{repo}/rules/branches/{branch}")
            rules = {
                str(item.get("type"))
                for item in (listing or [])
                if isinstance(item, dict) and item.get("type")
            }
        except RuntimeError as exc:
            reasons.append(f"long-lived probe unavailable ({exc}); treated as long-lived")
            return {"long_lived": True, "reasons": reasons}
    if default and head == default:
        reasons.append(f"'{head}' is the repository default branch")
    if protected:
        reasons.append(f"GitHub reports '{head}' as protected")
    guarded = sorted(rules & LONG_LIVED_RULE_TYPES)
    if guarded:
        reasons.append(f"'{head}' branch rules forbid {', '.join(guarded)}")
    return {"long_lived": bool(reasons), "reasons": reasons}


def select_merge_method(repo: str, pr: str) -> dict[str, Any]:
    """Return method, head, children and head retention. Raises RuntimeError if the probe fails."""
    head, children = _stacked_children(repo, str(pr))
    lived = long_lived_head(repo, str(pr), head)
    long_lived = bool(lived["long_lived"])
    method = ANCESTRY_SAFE if children or long_lived else UNSTACKED
    if long_lived:
        reason = (
            f"head '{head}' is long-lived ({'; '.join(lived['reasons'])}); "
            "--merge keeps both branches' history joined and the head is never deleted"
        )
    elif children:
        reason = (
            f"head '{head}' is the base of open PR(s) "
            + ", ".join(f"#{c}" for c in children)
            + "; --merge preserves ancestry"
        )
    else:
        reason = "no open PR bases on this head and it is not long-lived; --squash is safe"
    keep_head_reason = None
    if long_lived:
        keep_head_reason = "long-lived head: " + "; ".join(lived["reasons"])
    elif children:
        keep_head_reason = "head is the base of open PR(s)"
    return {
        "repo": repo,
        "pr": int(pr) if str(pr).isdigit() else pr,
        "head": head,
        "children": children,
        "head_long_lived": long_lived,
        "keep_head_reason": keep_head_reason,
        "method": method,
        "reason": reason,
    }


def _keep_head(selection: dict[str, Any]) -> str | None:
    """Why the head must survive this merge, or None when it may be deleted.

    Checked at each delete site, not only at selection: a hand-built selection
    without ``head_long_lived`` still never deletes a long-lived name.
    """
    if selection.get("keep_head_reason"):
        return str(selection["keep_head_reason"])
    if selection.get("head_long_lived"):
        return "long-lived head"
    if selection.get("children"):
        return "head is the base of open PR(s)"
    head = str(selection.get("head") or "")
    if head and _long_lived_name(head):
        return f"'{head}' is a long-lived branch name"
    return None


def merge_argv(
    repo: str,
    pr: str,
    *,
    delete_branch: bool = True,
    selection: dict[str, Any] | None = None,
    head_sha: str = "",
) -> list[str]:
    chosen = selection or select_merge_method(repo, str(pr))
    if _keep_head(chosen):
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
    keep = _keep_head(selection)
    if keep and delete_branch:
        print(f"NOTE: head branch '{head}' is kept ({keep})", file=sys.stderr)
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


# ---------------------------------------------------------------------------
# merge queue
# ---------------------------------------------------------------------------

#: Exit status for "a queued entry is no longer bound to its granted head".
UNBOUND_QUEUE_EXIT = 5
UNBOUND_LEDGER_NAME = "merge-queue-unbound.json"
QUEUE_POLL_SECONDS = 30
QUEUE_TIMEOUT_SECONDS = 4 * 3600


def _rest_only() -> bool:
    """The skill's one definition of a REST-only surface (no duplicate copy here)."""
    scripts = _HERE.parent.parent / "skills" / "l9-pr-remediation" / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import protocol  # noqa: PLC0415

    return bool(protocol.rest_only())


def _gh_graphql(query: str, **variables: str) -> dict[str, Any]:
    argv = ["gh", "api", "graphql", "-f", f"query={query}"]
    for name, value in variables.items():
        argv += ["-f", f"{name}={value}"]
    proc = subprocess.run(argv, capture_output=True, text=True, check=False)  # noqa: S603
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"gh api graphql exited {proc.returncode}")
    payload = json.loads(proc.stdout or "{}")
    if payload.get("errors"):
        raise RuntimeError(json.dumps(payload["errors"])[:500])
    return payload.get("data") or {}


def _pull(repo: str, pr: str) -> dict[str, Any]:
    view = _gh_rest_json(f"repos/{repo}/pulls/{pr}")
    if not isinstance(view, dict):
        raise RuntimeError("pull request payload was not an object")
    return view


def pr_base(repo: str, pr: str) -> str:
    entry = _probe_file_entry(repo, str(pr))
    if entry is not None:
        return str(entry.get("base") or "")
    return str((_pull(repo, pr).get("base") or {}).get("ref") or "")


def queue_rule(repo: str, base: str, pr: str = "") -> dict[str, Any] | None:
    """The base branch's ``merge_queue`` rule, or None. Raises RuntimeError when unreadable.

    ``L9_STACK_PROBE_FILE`` entries may carry ``merge_queue`` (bool) so tests stay offline.
    """
    entry = _probe_file_entry(repo, str(pr)) if pr else None
    if entry is not None:
        return {"type": "merge_queue"} if entry.get("merge_queue") else None
    if not base:
        raise RuntimeError("base branch is unknown")
    branch = urllib.parse.quote(base, safe="")
    listing = _gh_rest_json(f"repos/{repo}/rules/branches/{branch}")
    for item in listing or []:
        if isinstance(item, dict) and item.get("type") == "merge_queue":
            return item
    return None


def queue_state(repo: str, pr: str) -> dict[str, Any]:
    """``{"queued": True|False|None, "head": sha, "merged": bool}``. ``None`` is unobservable.

    GraphQL reads the documented ``isInMergeQueue`` and the entry's head commit.
    REST has no documented membership signal; the issue timeline's last
    ``added_to_merge_queue`` / ``removed_from_merge_queue`` event is read and an
    absence of both stays None (UNKNOWN iii in the module docstring).
    """
    if not _rest_only():
        owner, name = repo.split("/", 1)
        data = _gh_graphql(
            "query($o:String!,$n:String!,$p:Int!){repository(owner:$o,name:$n){"
            "pullRequest(number:$p){merged headRefOid isInMergeQueue autoMergeRequest{enabledAt} "
            "mergeQueueEntry{state headCommit{oid}}}}}",
            o=owner,
            n=name,
            p=str(pr),
        )
        node = ((data.get("repository") or {}).get("pullRequest")) or {}
        entry = node.get("mergeQueueEntry") or {}
        return {
            "queued": bool(node.get("isInMergeQueue")),
            "head": str(node.get("headRefOid") or "").lower(),
            "entry_head": str(((entry.get("headCommit") or {}).get("oid")) or "").lower() or None,
            "merged": bool(node.get("merged")),
            "armed": node.get("autoMergeRequest") is not None,
        }
    view = _pull(repo, pr)
    queued: bool | None = None
    try:
        events = _gh_rest_json(f"repos/{repo}/issues/{pr}/timeline?per_page=100")
    except RuntimeError:
        events = None
    for event in events or []:
        kind = event.get("event") if isinstance(event, dict) else None
        if kind == "added_to_merge_queue":
            queued = True
        elif kind == "removed_from_merge_queue":
            queued = False
    return {
        "queued": queued,
        "head": str((view.get("head") or {}).get("sha") or "").lower(),
        "entry_head": None,
        "merged": bool(view.get("merged")),
        "armed": view.get("auto_merge") is not None,
    }


def _node_id(repo: str, pr: str) -> str:
    node = str(_pull(repo, pr).get("node_id") or "")
    if not node:
        raise RuntimeError("REST did not report the pull request node id")
    return node


def enqueue_call(repo: str, pr: str, head_sha: str) -> None:
    """Ask GitHub to queue ``repo#pr`` at ``head_sha``. Membership is proven by the caller."""
    if not _rest_only():
        _gh_graphql(
            "mutation($id:ID!,$h:GitObjectID!){enqueuePullRequest(input:"
            "{pullRequestId:$id,expectedHeadOid:$h}){mergeQueueEntry{id}}}",
            id=_node_id(repo, pr),
            h=head_sha,
        )
        return
    if _run(["gh", "api", "--method", "PUT", f"repos/{repo}/pulls/{pr}/ccr/auto_merge"]) != 0:
        raise RuntimeError("PUT ccr/auto_merge failed")


def disarm_call(repo: str, pr: str) -> None:
    """Remove an armed auto-merge (or a queue entry; UNKNOWN ii on REST)."""
    if not _rest_only():
        _gh_graphql(
            "mutation($id:ID!){disablePullRequestAutoMerge(input:{pullRequestId:$id})"
            "{clientMutationId}}",
            id=_node_id(repo, pr),
        )
        return
    if _run(["gh", "api", "--method", "DELETE", f"repos/{repo}/pulls/{pr}/ccr/auto_merge"]) != 0:
        raise RuntimeError("DELETE ccr/auto_merge failed")


def dequeue_call(repo: str, pr: str) -> None:
    if not _rest_only():
        _gh_graphql(
            "mutation($id:ID!){dequeuePullRequest(input:{id:$id}){clientMutationId}}",
            id=_node_id(repo, pr),
        )
        return
    disarm_call(repo, pr)


def board_verdict(repo: str, pr: str) -> dict[str, Any]:
    import pr_board  # noqa: PLC0415

    return pr_board.board_for(repo, str(pr))


def _unbound_ledger_path() -> Path:
    home = Path(pwd.getpwuid(os.getuid()).pw_dir)
    return home / ".l9" / "autonomy" / UNBOUND_LEDGER_NAME


def _read_ledger(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def record_unbound(entry: dict[str, Any], *, path: Path | None = None) -> None:
    target = path or _unbound_ledger_path()
    ledger = _read_ledger(target)
    ledger.setdefault(str(entry["repo"]), {})[str(entry["pr"])] = entry
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def unbound_blockers(repo: str, *, path: Path | None = None) -> list[dict[str, Any]]:
    """Unbound entries for ``repo`` still in the queue. Entries no longer queued are cleared.

    An entry whose state cannot be read stays a blocker: unknown is not resolved.
    """
    target = path or _unbound_ledger_path()
    ledger = _read_ledger(target)
    entries = ledger.get(repo) or {}
    remaining: dict[str, Any] = {}
    for pr, entry in entries.items():
        try:
            state = queue_state(repo, pr)
        except RuntimeError:
            remaining[pr] = entry
            continue
        if state.get("queued") is not False:
            remaining[pr] = entry
    if remaining != entries:
        if remaining:
            ledger[repo] = remaining
        else:
            ledger.pop(repo, None)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return list(remaining.values())


def parse_items(items: list[str]) -> list[tuple[str, str]]:
    parsed: list[tuple[str, str]] = []
    for item in items:
        pr, _, sha = item.partition("@")
        sha = sha.strip().lower()
        if not pr.strip().isdigit() or not _FULL_SHA.match(sha):
            raise ValueError(f"queue item {item!r} is not <pr>@<40-hex head sha>")
        parsed.append((pr.strip(), sha))
    return parsed


def _pending(repo: str, pr: str, head: str, reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "status": "MERGE_PENDING",
        "repo": repo,
        "pr": int(pr),
        "granted_head": head,
        "reason": reason,
        **extra,
    }


def admit_for_queue(repo: str, pr: str, head: str) -> dict[str, Any] | None:
    """None when ``repo#pr`` may be enqueued at ``head``; otherwise its MERGE_PENDING record."""
    try:
        base = pr_base(repo, pr)
        rule = queue_rule(repo, base, pr)
    except RuntimeError as exc:
        return _pending(repo, pr, head, f"merge-queue rule unreadable ({exc}); not enqueued")
    if rule is None:
        return _pending(
            repo,
            pr,
            head,
            f"base '{base}' has no merge_queue rule; auto-merge is never used outside a queue "
            "-- merge with --run instead",
        )
    auth = authorization_status(repo, pr, head)
    if auth.get("status") != "AUTHORIZED":
        return _pending(repo, pr, head, str(auth.get("reason")), authorization=auth)
    board = board_verdict(repo, pr)
    if board.get("board") != "merge":
        return _pending(repo, pr, head, f"board is {board.get('board')}: {board.get('reason')}")
    try:
        live = live_head_sha(repo, pr)
    except RuntimeError as exc:
        return _pending(repo, pr, head, f"cannot recheck the live head ({exc})")
    if live != head:
        return _pending(repo, pr, head, f"head moved: granted {head}, live {live}", live_head=live)
    return None


def enqueue_one(repo: str, pr: str, head: str) -> dict[str, Any]:
    """Enqueue at ``head`` and prove membership, or disarm and report MERGE_PENDING."""
    try:
        enqueue_call(repo, pr, head)
    except RuntimeError as exc:
        return _pending(repo, pr, head, f"enqueue refused ({exc})")
    try:
        state = queue_state(repo, pr)
    except RuntimeError as exc:
        state = {"queued": None, "head": "", "error": str(exc)}
    bound = state.get("head") == head and state.get("entry_head") in (None, head)
    if state.get("queued") is True and bound:
        return {"status": "QUEUED", "repo": repo, "pr": int(pr), "granted_head": head}
    if state.get("queued") is True:
        reason = f"queued at {state.get('entry_head') or state.get('head')}, not the granted head"
    elif state.get("queued") is None:
        reason = "queue membership could not be observed after the enqueue call"
    else:
        reason = "the pull request did not enter the queue at once (auto-merge would wait armed)"
    return withdraw(repo, pr, head, reason, observed_head=state.get("head") or "")


def _withdrawn(state: dict[str, Any]) -> bool:
    """True only when the PR is observably neither queued nor armed.

    REST has no documented membership signal (UNKNOWN iii), so there a null
    ``auto_merge`` with no queue event is the only evidence of removal.
    """
    queued = state.get("queued")
    armed = state.get("armed")
    if queued is False:
        return armed is not True
    return queued is None and armed is False


def withdraw(
    repo: str, pr: str, head: str, reason: str, *, observed_head: str = ""
) -> dict[str, Any]:
    """Dequeue and disarm ``repo#pr``, then prove it. MERGE_PENDING if proven, else UNBOUND.

    Every path that stops trusting a queue entry -- an enqueue not proven at the
    granted head, a head that moved, a revoked authorization, a watcher timeout --
    ends here, so no entry is ever abandoned while it might still merge.
    """
    errors: list[str] = []
    for call in (dequeue_call, disarm_call):
        try:
            call(repo, pr)
        except RuntimeError as exc:
            errors.append(f"{call.__name__}: {exc}")
    try:
        after = queue_state(repo, pr)
    except RuntimeError as exc:
        after = {"queued": None, "armed": None, "error": str(exc)}
    if after.get("merged") and (after.get("head") or "") == head:
        return {"status": "MERGED", "repo": repo, "pr": int(pr), "granted_head": head}
    if after.get("merged"):
        return _unbound(
            repo,
            pr,
            head,
            observed_head or after.get("head") or "unknown",
            reason=f"{reason}; it merged before it could be withdrawn",
            merged=True,
        )
    if _withdrawn(after):
        return _pending(
            repo,
            pr,
            head,
            f"{reason}; withdrawn from the queue",
            withdrawn=True,
            moved_head=observed_head or None,
        )
    return _unbound(
        repo,
        pr,
        head,
        observed_head or after.get("head") or "unknown",
        reason=reason,
        observed_queued=after.get("queued"),
        observed_armed=after.get("armed"),
        errors=errors,
    )


def _unbound(repo: str, pr: str, head: str, moved: str, **extra: Any) -> dict[str, Any]:
    entry = {
        "status": "UNBOUND_QUEUE_ENTRY",
        "repo": repo,
        "pr": int(pr),
        "granted_head": head,
        "moved_head": moved,
        **extra,
    }
    record_unbound(entry)
    print(
        f"UNBOUND_QUEUE_ENTRY MERGE_PENDING: {repo}#{pr} (grant covers {head}, observed "
        f"{moved}) could not be proven out of the queue: {extra.get('reason', '')}. "
        f"No further enqueue for {repo} until it has left the queue.",
        file=sys.stderr,
    )
    return entry


def watch_step(repo: str, pr: str, head: str) -> dict[str, Any] | None:
    """One poll of one queued PR. None while it is still queued at the granted head."""
    try:
        state = queue_state(repo, pr)
    except RuntimeError:
        return None
    if state.get("merged"):
        return {"status": "MERGED", "repo": repo, "pr": int(pr), "granted_head": head}
    moved = state.get("head") or ""
    if state.get("queued") is not False and moved and moved != head:
        return withdraw(repo, pr, head, f"head moved to {moved} while queued", observed_head=moved)
    if state.get("queued") is not False:
        # The latest instruction wins: a cancellation after the enqueue withdraws it.
        auth = authorization_status(repo, pr, head)
        if auth.get("status") != "AUTHORIZED":
            return withdraw(
                repo,
                pr,
                head,
                f"authorization withdrawn while queued ({auth.get('reason')})",
                observed_head=moved,
            )
    if state.get("queued") is False:
        return {
            "status": "EJECTED",
            "repo": repo,
            "pr": int(pr),
            "granted_head": head,
            "reason": "removed from the queue without merging; remediate, then re-enqueue",
        }
    return None


def run_queue(
    repo: str,
    items: list[tuple[str, str]],
    *,
    poll: float = QUEUE_POLL_SECONDS,
    timeout: float = QUEUE_TIMEOUT_SECONDS,
    sleep: Any = None,
    clock: Any = None,
) -> list[dict[str, Any]]:
    """Enqueue ``items`` in the given order, then watch them with one watcher."""
    import time  # noqa: PLC0415

    sleep = sleep or time.sleep
    clock = clock or time.monotonic
    blockers = unbound_blockers(repo)
    if blockers:
        return [
            _pending(
                repo,
                pr,
                head,
                "unbound queue entry outstanding for this repository: "
                + ", ".join(f"#{b['pr']}" for b in blockers),
                blockers=blockers,
            )
            for pr, head in items
        ]
    results: dict[str, dict[str, Any]] = {}
    watching: list[tuple[str, str]] = []
    stopped = False
    for pr, head in items:
        if stopped:
            results[pr] = _pending(repo, pr, head, "not enqueued: an earlier item is unbound")
            continue
        refusal = admit_for_queue(repo, pr, head)
        outcome = refusal or enqueue_one(repo, pr, head)
        results[pr] = outcome
        if outcome["status"] == "QUEUED":
            watching.append((pr, head))
        elif outcome["status"] == "UNBOUND_QUEUE_ENTRY":
            stopped = True
    deadline = clock() + timeout
    while watching:
        for pr, head in list(watching):
            outcome = watch_step(repo, pr, head)
            if outcome is not None:
                results[pr] = outcome
                watching.remove((pr, head))
        if not watching:
            break
        if clock() >= deadline:
            # No entry outlives its watcher: withdraw it, or record it unbound.
            for pr, head in watching:
                results[pr] = withdraw(repo, pr, head, "still queued when the watcher timed out")
            break
        sleep(poll)
    return [results[pr] for pr, _ in items]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="owner/name")
    parser.add_argument("--pr", help="pull request number (not with --queue)")
    parser.add_argument(
        "--keep-branch",
        action="store_true",
        help="omit --delete-branch",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--print", action="store_true", dest="print_argv", help="print argv")
    mode.add_argument("--json", action="store_true", help="print selection JSON")
    mode.add_argument("--run", action="store_true", help="exec the selected gh pr merge")
    mode.add_argument(
        "--queue",
        nargs="+",
        metavar="PR@SHA",
        help="enqueue these PRs in this order (merge_order, bottom-up) and watch them",
    )
    parser.add_argument(
        "--head-sha",
        default="",
        help="exact head the human grant covers; required by --run",
    )
    args = parser.parse_args(argv)

    if args.queue:
        try:
            items = parse_items(args.queue)
        except ValueError as exc:
            print(f"FAIL: {exc}", file=sys.stderr)
            return 2
        outcomes = run_queue(args.repo, items)
        print(json.dumps({"repo": args.repo, "queue": outcomes}, indent=2, sort_keys=True))
        statuses = {o["status"] for o in outcomes}
        if "UNBOUND_QUEUE_ENTRY" in statuses:
            return UNBOUND_QUEUE_EXIT
        return 0 if statuses == {"MERGED"} else MERGE_PENDING_EXIT
    if not args.pr:
        parser.error("--pr is required unless --queue is given")

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
        # A queue-protected base refuses a direct merge: hand the PR to the queue.
        # An unreadable rule keeps today's direct merge, which GitHub itself
        # refuses on a queue base, so nothing merges around the queue.
        try:
            on_queue = queue_rule(args.repo, pr_base(args.repo, args.pr), args.pr) is not None
        except RuntimeError:
            on_queue = False
        if on_queue:
            outcomes = run_queue(args.repo, [(str(args.pr), bound_sha)])
            print(json.dumps({"repo": args.repo, "queue": outcomes}, indent=2, sort_keys=True))
            status = outcomes[0]["status"]
            if status == "UNBOUND_QUEUE_ENTRY":
                return UNBOUND_QUEUE_EXIT
            return 0 if status == "MERGED" else MERGE_PENDING_EXIT

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

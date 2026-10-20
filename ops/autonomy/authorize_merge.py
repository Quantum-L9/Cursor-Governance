#!/usr/bin/env python3
"""Issue a human merge grant: one repository, one PR, one exact head, expiring.

A grant is one of the merge authorities ``merge_gate.py`` and
``stack_safe_merge.py`` accept (CANONICAL_LAW §6.2.12, §6.2.13). The human is
always the authorizer; this script only records that authority in a form the
gate can bind to an exact head. Two confirmations exist:

* **Operator prompt** (``--operator-instruction``, §6.2.13). The host's
  prompt-submission hook recorded an explicit merge instruction from the
  operator ("merge PR #735 after the checks pass", "fix and merge #735",
  "remediate and merge all currently open PRs in owner/name"). The agent may
  run this script in that mode, without a terminal, and it writes the grant
  only after rechecking, live on GitHub, that the pull request is open, that
  ``--head-sha`` is its current head, that a live receipt covers it (an
  explicit PR, a pull request resolved from the conversation when the operator
  spoke, or membership of the open-pull-request snapshot the recorder took
  then) and has not been cancelled by a later instruction, that the receipt
  carries the host hook's own provenance and is corroborated by a human turn
  of its session in the host-written transcript, and that the session's GitHub
  identity — the operator's own connected account — is a human holding
  ``admin``, ``maintain`` or ``write`` on the repository (§6.2.14). The grant
  carries the instruction's provenance and that authorizer. The operator may
  be the pull request's author and the change may touch L9-ORG-007 paths: an
  authorized owner's direct instruction is that invariant's authorization
  (as amended). A receipt from a host whose prompt channel cannot be verified
  this way (Cursor) is refused as BLOCKED_HOST_ORIGIN; the GitHub record
  remains that host's channel.

  A direct operator invocation of ``/l9-pr-remediation`` (§6.2.15) is such an
  instruction for its repository's open-pull-request snapshot, each member
  once the readiness board says merge. It also covers a stacked successor the
  remediation opened on a member's branch when GitHub shows that lineage and
  the successor's author is the authorizing principal
  (:func:`successor_lineage`). The invoking (parent) agent runs this mode; a
  subagent never does — ``merge_gate.py`` denies it — and merge workers only
  run ``stack_safe_merge.py --run`` against the grant the parent wrote.

* **Controlling terminal** (default). A human types the exact target back on
  ``/dev/tty``. An agent's tool shell has no controlling terminal, so this mode
  refuses there by construction, and ``merge_gate.py`` denies an agent tool
  call that runs it.

    "$HOME/.cursor-governance/.venv/bin/python" \\
        "$HOME/.cursor-governance/ops/autonomy/authorize_merge.py" \\
        --operator-instruction --repo owner/name --pr 53 --head-sha <40-hex>

Repository-wide authority (``--all-open`` / ``--pr '*'``) is not issuable, and a
receipt with no head binding, no ``issuer: human``, or a lifetime over
MAX_TTL_SECONDS authorizes nothing. Neither confirmation proves identity to a
cryptographic standard: on a host where the worker runs as the same OS account
both are defeatable by deliberate forgery, which is the host-enforcement gap
§6.2.12 names. Forgery is a violation of that section, not a loophole in it.

It does not merge. It does not authorize force-push, admin-merge, or hard-reset.

Metadata:
  layer: ops
  role: merge_authorization
  version: 6.0.0
"""

from __future__ import annotations

import argparse
import json
import os
import pwd
import re
import sys
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import merge_authority_switch  # noqa: E402
import operator_merge_instruction as omi  # noqa: E402
from github_merge_authorization import (  # noqa: E402
    fetch_pull_request,
    fetch_pulls_with_head,
    fetch_session_principal,
    principal_may_authorize,
)

#: How many stacked links a successor may sit above a fleet member.
MAX_LINEAGE_DEPTH = 3

DEFAULT_TTL_SECONDS = 60 * 60
#: merge_gate.py refuses any grant whose expiry lies further out than this.
MAX_TTL_SECONDS = 4 * 60 * 60
ISSUER = "human"
DEFAULT_REASON = "human merge grant"
OPERATOR_CHANNEL = "operator_prompt"
TERMINAL_CHANNEL = "controlling_terminal"
#: Exit status when no human confirmed the grant on a terminal.
NOT_CONFIRMED_EXIT = 3
#: Exit status when the operator-prompt path cannot bind this merge.
OPERATOR_REFUSED_EXIT = 4

_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")

REPO_WIDE_REFUSAL = (
    "Repository-wide merge authority is not issuable (CANONICAL_LAW §6.2.12). "
    "Issue one grant per PR and exact head SHA: "
    '"$HOME/.cursor-governance/.venv/bin/python" '
    '"$HOME/.cursor-governance/ops/autonomy/authorize_merge.py" '
    "--repo <owner/name> --pr <n> --head-sha <40-hex>."
)


def auth_path(explicit: str) -> Path:
    if explicit:
        return Path(explicit).expanduser()
    return Path.home() / ".l9" / "autonomy" / "merge-authorization.json"


def account_instruction_path() -> Path:
    """The receipt store under the account's home from the password database.

    Not ``$HOME`` and not an environment override: this process's environment
    belongs to whoever runs it, and in operator mode that is the agent.
    """
    try:
        home = Path(pwd.getpwuid(os.getuid()).pw_dir)
    except (KeyError, OSError):
        home = Path.home()
    return home / ".l9" / "autonomy" / omi.INSTRUCTION_FILE_NAME


def _normalize_pr(pr: str | int) -> int:
    text = str(pr).strip()
    if not text.isdigit() or int(text) <= 0:
        raise ValueError(f"pr must be a positive PR number; {REPO_WIDE_REFUSAL}")
    return int(text)


def confirmation_token(repo: str, pr: int, head_sha: str) -> str:
    """What the human types back: the exact target, so a grant cannot drift."""
    return f"{repo}#{pr}@{head_sha[:12]}"


def write_authorization(
    *,
    repo: str,
    pr: str | int,
    head_sha: str,
    reason: str,
    path: Path,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    now: float | None = None,
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not repo or "/" not in repo:
        raise ValueError("repo must be owner/name")
    if not reason.strip():
        raise ValueError("reason is required")
    if ttl_seconds <= 0:
        raise ValueError("ttl_seconds must be positive (merge grants must expire)")
    if ttl_seconds > MAX_TTL_SECONDS:
        raise ValueError(f"ttl_seconds may not exceed {MAX_TTL_SECONDS}")
    normalized_pr = _normalize_pr(pr)
    sha = head_sha.strip().lower()
    if not _FULL_SHA.match(sha):
        raise ValueError("head_sha must be the full 40-hex head commit id")
    current: dict[str, Any] = {"authorizations": []}
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict) and isinstance(loaded.get("authorizations"), list):
                current = loaded
        except json.JSONDecodeError:
            current = {"authorizations": []}
    stamp = int(now if now is not None else time.time())
    entry: dict[str, Any] = {
        "repo": repo,
        "pr": normalized_pr,
        "head_sha": sha,
        "issuer": ISSUER,
        "issued_at": stamp,
        "expires_at": stamp + ttl_seconds,
        "reason": reason.strip(),
    }
    if provenance:
        entry["provenance"] = dict(provenance)
    entries = [
        item
        for item in current.get("authorizations", [])
        if isinstance(item, dict)
        and not (
            str(item.get("repo")) == repo
            and str(item.get("pr") or item.get("number") or "") == str(normalized_pr)
        )
    ]
    entries.append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"authorizations": entries}, indent=2) + "\n", encoding="utf-8")
    return entry


def confirm_on_terminal(token: str) -> bool:
    """Ask on the controlling terminal; False when there is none.

    The prompt goes to /dev/tty rather than stdin, so piping an answer into the
    script does not satisfy it. An agent's tool shell has no controlling
    terminal, so this refuses there by construction.
    """
    try:
        with open("/dev/tty", "r+", encoding="utf-8") as tty:
            tty.write(f"Authorize merge of {token}? Type it back exactly to confirm: ")
            tty.flush()
            answer = tty.readline().strip()
    except OSError:
        return False
    return answer == token


# --- operator-prompt confirmation (§6.2.13) ---------------------------------


def _parse_github_time(value: Any) -> float | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def fetch_readiness(repo: str, pr: int) -> dict[str, Any]:
    """The existing readiness board's verdict for ``repo#pr`` (``pr_board.board_for``).

    ``board == "merge"`` means required checks are green, review threads are
    resolved, there is no conflict and the stack allows it, at the live head.
    """
    import pr_board  # noqa: PLC0415 - only a readiness-conditional instruction needs it

    return pr_board.board_for(repo, str(pr))


def _full_name(side: Any) -> str:
    repo = (side or {}).get("repo") if isinstance(side, dict) else None
    return str((repo or {}).get("full_name") or "") if isinstance(repo, dict) else ""


def _author(view: dict[str, Any]) -> str:
    user = view.get("user") if isinstance(view.get("user"), dict) else {}
    return str(user.get("login") or "")


def successor_lineage(
    repo: str,
    view: dict[str, Any],
    fleet: dict[str, Any],
    *,
    pull_request: Callable[[str, int], dict[str, Any]] = fetch_pull_request,
    pulls_with_head: Callable[[str, str], list[dict[str, Any]]] = fetch_pulls_with_head,
) -> tuple[dict[str, Any] | None, str]:
    """``(lineage, reason)``: whether ``view`` is a successor of the fleet ``fleet``.

    CANONICAL_LAW §6.2.15: a pull request the authorized remediation opened is
    covered when GitHub itself shows the lineage — opened after the invocation
    and before it expires, from a branch of this repository (never a fork), and
    stacked on a branch that is the head of exactly one fleet member (directly,
    or through at most ``MAX_LINEAGE_DEPTH`` successors that satisfy the same
    test). ``lineage["authors"]`` names the author of every non-member pull
    request in the chain — the candidate and each intermediate successor — and
    the caller requires every one of them to be the authorizing principal, so
    an operator-authored pull request stacked on someone else's is not covered.
    Anything else — a later pull request based on ``main``, one from a
    fork, one opened before the invocation that the snapshot did not hold —
    is not covered.
    """
    members = {int(n) for n in (fleet.get("members") or []) if str(n).isdigit()}
    since = float(fleet.get("recorded_at") or 0)
    until = float(fleet.get("expires_at") or 0)
    created = _parse_github_time(view.get("created_at"))
    if created is None or created <= since:
        return None, "it was not opened after the fleet invocation and is not in its snapshot"
    if created >= until:
        return None, "it was opened after the fleet invocation expired"
    chain: list[int] = []
    authors = [_author(view)]
    current = view
    for _ in range(MAX_LINEAGE_DEPTH):
        if _full_name(current.get("head")).casefold() != repo.casefold():
            return None, "its branch is not in this repository"
        base = current.get("base") if isinstance(current.get("base"), dict) else {}
        if _full_name(base).casefold() != repo.casefold():
            return None, "it does not target a branch of this repository"
        ref = str(base.get("ref") or "")
        try:
            parents = pulls_with_head(repo, ref) if ref else []
        except RuntimeError as exc:
            return None, f"cannot read which pull request owns branch {ref!r} ({exc})"
        if len(parents) != 1:
            return None, (
                f"its base branch {ref or '<none>'} is not the head of exactly one pull request "
                "of the fleet"
            )
        parent = int(parents[0].get("number") or 0)
        chain.append(parent)
        if parent in members:
            return {
                "fleet_instruction_id": fleet.get("id"),
                "member": parent,
                "chain": chain,
                "authors": authors,
            }, f"stacked on fleet member #{parent}"
        parent_created = _parse_github_time(parents[0].get("created_at"))
        if parent_created is None or parent_created <= since:
            return None, f"its base pull request #{parent} is not a fleet member"
        if parent_created >= until:
            return None, f"its base pull request #{parent} was opened after the invocation expired"
        try:
            current = pull_request(repo, parent)
        except RuntimeError as exc:
            return None, f"cannot read base pull request #{parent} ({exc})"
        authors.append(_author(current))
    return None, f"its stack is deeper than {MAX_LINEAGE_DEPTH} links above any fleet member"


def operator_verdict(
    repo: str,
    pr: int,
    head_sha: str,
    *,
    instruction_path: Path | None = None,
    now: float | None = None,
    pull_request: Callable[[str, int], dict[str, Any]] = fetch_pull_request,
    session_principal: Callable[[str], dict[str, Any]] = fetch_session_principal,
    readiness: Callable[[str, int], dict[str, Any]] = fetch_readiness,
    pulls_with_head: Callable[[str, str], list[dict[str, Any]]] = fetch_pulls_with_head,
) -> dict[str, Any]:
    """Whether a recorded operator instruction may become a grant for this head.

    A pull request outside every instruction may still be covered by a live
    fleet invocation (``/l9-pr-remediation``, §6.2.15) when GitHub shows it is
    that remediation's stacked successor (:func:`successor_lineage`) and its
    author is the authorizing principal.

    Every refusal names the missing prerequisite. The checks run in the order a
    reader can act on them: the live pull request first (an instruction for a
    closed or moved PR is moot), then the instruction, then the operator's
    authority over the repository, then the instruction's own readiness
    condition ("once CI is green"), proven by the readiness board at the live
    head. A condition that waits on a decision never reaches here: it is not a
    live authorizing instruction (``omi.pending_condition``).
    """
    stamp = time.time() if now is None else now
    sha = head_sha.strip().lower()
    refused: dict[str, Any] = {"authorized": False, "instruction": None, "pull_request": None}

    try:
        view = pull_request(repo, pr)
    except RuntimeError as exc:
        refused["reason"] = f"cannot verify the live pull request ({exc})"
        return refused
    live = str(((view or {}).get("head") or {}).get("sha") or "").strip().lower()
    state = str(view.get("state") or "")
    author = str(((view or {}).get("user") or {}).get("login") or "")
    created = _parse_github_time(view.get("created_at"))
    summary = {
        "state": state,
        "head_sha": live,
        "author": author,
        "created_at": view.get("created_at"),
    }
    refused["pull_request"] = summary
    if state != "open" or view.get("merged"):
        merged = " and merged" if view.get("merged") else ""
        refused["reason"] = f"pull request is {state or 'unknown'}{merged}"
        return refused
    if not _FULL_SHA.match(live):
        refused["reason"] = "GitHub did not report the pull request's head"
        return refused
    if live != sha:
        refused["reason"] = (
            f"head moved: requested {sha}, live {live}. Verify the live head's readiness, "
            "then re-run with it; the operator instruction still covers this pull request"
        )
        return refused
    if created is None:
        refused["reason"] = "GitHub did not report when the pull request was opened"
        return refused

    store = instruction_path or account_instruction_path()
    if merge_authority_switch.disabled():
        # §6.2.16: no receipt, host, transcript or principal check on any
        # surface. A recorded instruction, when there is one, still names the
        # grant's provenance; the open PR and the live head were proved above.
        found = omi.instruction_verdict(repo, pr, path=store, now=stamp)
        recorded = found.get("instruction") if found.get("authorized") else None
        return {
            "authorized": True,
            "reason": "merge-authority enforcement disabled (CANONICAL_LAW §6.2.16)",
            "instruction": recorded
            or {"id": "enforcement-disabled", "expires_at": stamp + MAX_TTL_SECONDS},
            "pull_request": summary,
            "authorizer": None,
            "lineage": None,
        }
    verdict = omi.instruction_verdict(repo, pr, path=store, now=stamp)
    lineage: dict[str, Any] | None = None
    if not verdict["authorized"]:
        fleet = omi.fleet_instruction(repo, pr, path=store, now=stamp)
        why = ""
        if fleet is not None:
            lineage, why = successor_lineage(
                repo, view, fleet, pull_request=pull_request, pulls_with_head=pulls_with_head
            )
        if lineage is None:
            successor = f"; not a successor of the fleet invocation: {why}" if why else ""
            refused["reason"] = (
                f"no live operator merge instruction covers {repo}#{pr}: {verdict['reason']}"
                f"{successor}. The operator authorizes by asking for the merge in their own "
                "words in this session's chat, by invoking /l9-pr-remediation, or on GitHub "
                "(CANONICAL_LAW §6.2.13–§6.2.15); no particular wording is required"
            )
            return refused
        verdict = {"authorized": True, "instruction": fleet}
    instruction = verdict["instruction"]
    receipt = omi.receipt_verdict(instruction, now=stamp)
    if not receipt["ok"]:
        refused["reason"] = (
            f"operator instruction {instruction.get('id')} for {repo}#{pr} cannot become a grant: "
            f"{receipt['reason']}. Only a receipt the host prompt hook wrote, corroborated by a "
            "human turn of its session in the host transcript, is the operator's authority "
            "(CANONICAL_LAW §6.2.13)"
        )
        refused["instruction"] = instruction
        return refused

    try:
        principal = session_principal(repo)
    except RuntimeError as exc:
        refused["reason"] = f"cannot verify the operator's authority over {repo} ({exc})"
        refused["instruction"] = instruction
        return refused
    if not principal_may_authorize(principal):
        refused["reason"] = (
            f"the session's GitHub identity {principal.get('login') or '<unknown>'} "
            f"({principal.get('type') or 'unknown type'}) holds "
            f"{principal.get('permission') or 'no'} permission on {repo}; only a human with "
            "admin, maintain or write authority over the repository can authorize its merge "
            "(CANONICAL_LAW §6.2.14). This pull request is outside the operator's authorized scope"
        )
        refused["instruction"] = instruction
        return refused
    login = str(principal.get("login") or "").casefold()
    foreign = [
        name for name in (lineage or {}).get("authors", [author]) if name.casefold() != login
    ]
    if lineage is not None and (not login or foreign):
        refused["reason"] = (
            f"{repo}#{pr} is stacked on fleet member #{lineage['member']}, but its chain was "
            f"opened by {', '.join(sorted(set(foreign))) or '<unknown>'}, not only by the "
            f"authorizing operator {principal.get('login') or '<unknown>'}; only the authorized "
            "remediation's own successors are covered (CANONICAL_LAW §6.2.15)"
        )
        refused["instruction"] = instruction
        return refused

    condition = instruction.get("condition")
    if isinstance(condition, dict) and condition.get("status") == omi.CONDITION_READINESS:
        text = condition.get("text") or "readiness"
        try:
            board = readiness(repo, pr)
        except Exception as exc:  # noqa: BLE001 - an unreadable condition is unmet, never met
            board = {"board": "wait", "reason": f"readiness unreadable ({exc})"}
        if str((board or {}).get("board") or "") != "merge":
            refused["reason"] = (
                f"operator instruction {instruction.get('id')} for {repo}#{pr} is conditional "
                f"({text}) and the condition is not yet met at head {sha}: the readiness board "
                f"says {(board or {}).get('board') or 'unknown'} "
                f"({(board or {}).get('reason') or 'no reason given'}). The instruction still "
                "covers this pull request; re-run once it is ready"
            )
            refused["instruction"] = instruction
            refused["readiness"] = board
            return refused

    return {
        "authorized": True,
        "reason": (
            "live operator instruction from a human with "
            f"{principal.get('permission')} authority covers an open PR at its live head"
            + (f" (fleet successor stacked on #{lineage['member']})" if lineage else "")
        ),
        "instruction": instruction,
        "pull_request": summary,
        "authorizer": principal,
        "lineage": lineage,
    }


def operator_provenance(
    instruction: dict[str, Any],
    pull_request: dict[str, Any],
    authorizer: dict[str, Any] | None = None,
    lineage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    raw_hook = instruction.get("provenance")
    hook = raw_hook if isinstance(raw_hook, dict) else {}
    return {
        "lineage": lineage,
        "command_name": hook.get("command_name"),
        "prompt_id": hook.get("prompt_id"),
        "channel": OPERATOR_CHANNEL,
        "recorded_by": "agent",
        "instruction_id": instruction.get("id"),
        "host": instruction.get("host"),
        "session_id": instruction.get("session_id"),
        "hook_event_name": hook.get("hook_event_name"),
        "transcript_path": hook.get("transcript_path"),
        "scope": instruction.get("scope"),
        "source": instruction.get("source"),
        "cohort_members": instruction.get("members")
        if instruction.get("scope") == "open_cohort"
        else None,
        "recorded_at": instruction.get("recorded_at"),
        "instruction_expires_at": instruction.get("expires_at"),
        "prompt_sha256": instruction.get("prompt_sha256"),
        "excerpt": instruction.get("excerpt"),
        "pull_request_author": pull_request.get("author"),
        "authorizer_login": (authorizer or {}).get("login"),
        "authorizer_permission": (authorizer or {}).get("permission"),
    }


def main(
    argv: list[str] | None = None,
    *,
    confirm: Callable[[str], bool] | None = None,
    instruction_path: Path | None = None,
    pull_request: Callable[[str, int], dict[str, Any]] = fetch_pull_request,
    session_principal: Callable[[str], dict[str, Any]] = fetch_session_principal,
    readiness: Callable[[str, int], dict[str, Any]] = fetch_readiness,
    pulls_with_head: Callable[[str, str], list[dict[str, Any]]] = fetch_pulls_with_head,
    now: float | None = None,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr", default="", help="the PR number this grant covers")
    parser.add_argument("--head-sha", default="", help="exact 40-hex head the human reviewed")
    parser.add_argument(
        "--all-open",
        action="store_true",
        help="refused: repository-wide merge authority is not issuable",
    )
    parser.add_argument(
        "--operator-instruction",
        action="store_true",
        help="confirm from the operator's recorded prompt instruction instead of a terminal",
    )
    parser.add_argument("--reason", default="")
    parser.add_argument("--auth-file", default="")
    parser.add_argument("--ttl-seconds", type=int, default=DEFAULT_TTL_SECONDS)
    args = parser.parse_args(argv)

    if args.all_open or args.pr.strip() in {"", "*", "all", "ALL"}:
        print(f"REFUSED: {REPO_WIDE_REFUSAL}", file=sys.stderr)
        return 2
    try:
        pr = _normalize_pr(args.pr)
    except ValueError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    sha = args.head_sha.strip().lower()
    if not _FULL_SHA.match(sha):
        print("REFUSED: --head-sha must be the full 40-hex head commit id", file=sys.stderr)
        return 2

    provenance: dict[str, Any] | None = None
    ttl = args.ttl_seconds
    reason = args.reason.strip()
    if args.operator_instruction:
        verdict = operator_verdict(
            args.repo,
            pr,
            sha,
            instruction_path=instruction_path,
            now=now,
            pull_request=pull_request,
            session_principal=session_principal,
            readiness=readiness,
            pulls_with_head=pulls_with_head,
        )
        if not verdict["authorized"]:
            print(json.dumps({**verdict, "status": "MERGE_PENDING"}, indent=2, sort_keys=True))
            print(f"REFUSED: {verdict['reason']}", file=sys.stderr)
            return OPERATOR_REFUSED_EXIT
        instruction = verdict["instruction"]
        provenance = operator_provenance(
            instruction,
            verdict["pull_request"],
            verdict.get("authorizer"),
            verdict.get("lineage"),
        )
        stamp = time.time() if now is None else now
        remaining = int(float(instruction.get("expires_at") or 0) - stamp)
        ttl = max(1, min(ttl, remaining))
        reason = reason or f"operator prompt instruction {instruction.get('id')}"
    else:
        token = confirmation_token(args.repo, pr, sha)
        if merge_authority_switch.disabled():
            # §6.2.16: no /dev/tty confirmation while enforcement is disabled.
            provenance = {"channel": "enforcement_disabled"}
        elif not (confirm or confirm_on_terminal)(token):
            print(
                "REFUSED: no human confirmed this grant on a controlling terminal, and no "
                "--operator-instruction was requested. Merge grants are issued by a human "
                "(CANONICAL_LAW §6.2.12, §6.2.13); an agent reports MERGE_PENDING instead "
                "of running this mode.",
                file=sys.stderr,
            )
            return NOT_CONFIRMED_EXIT
        else:
            provenance = {"channel": TERMINAL_CHANNEL}
        reason = reason or DEFAULT_REASON
    try:
        entry = write_authorization(
            repo=args.repo,
            pr=pr,
            head_sha=sha,
            reason=reason,
            path=auth_path(args.auth_file),
            ttl_seconds=ttl,
            now=now,
            provenance=provenance,
        )
    except ValueError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(entry, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

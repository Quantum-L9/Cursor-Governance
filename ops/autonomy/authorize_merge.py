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
  ``--head-sha`` is its current head, that the instruction covers it (an
  explicit PR, or membership of the cohort that was open when the operator
  spoke), and that the change touches no L9-ORG-007 protected path. The grant
  carries the instruction's provenance. A protected change is refused here:
  a prompt proves no GitHub identity, so it cannot be the independent human
  authorization that invariant requires.

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
  version: 4.0.0
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

import operator_merge_instruction as omi  # noqa: E402
from github_merge_authorization import (  # noqa: E402
    fetch_pull_request,
    fetch_pull_request_files,
    protected_paths_in,
)

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


def operator_verdict(
    repo: str,
    pr: int,
    head_sha: str,
    *,
    instruction_path: Path | None = None,
    now: float | None = None,
    pull_request: Callable[[str, int], dict[str, Any]] = fetch_pull_request,
    pull_request_files: Callable[[str, int], list[str] | None] = fetch_pull_request_files,
) -> dict[str, Any]:
    """Whether a recorded operator instruction may become a grant for this head.

    Every refusal names the missing prerequisite. The checks run in the order a
    reader can act on them: the live pull request first (an instruction for a
    closed or moved PR is moot), then the instruction, then L9-ORG-007.
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

    verdict = omi.instruction_verdict(
        repo,
        pr,
        path=instruction_path or account_instruction_path(),
        now=stamp,
        pr_created_at=created,
    )
    if not verdict["authorized"]:
        refused["reason"] = (
            f"no live operator merge instruction covers {repo}#{pr}: {verdict['reason']}. The "
            "operator authorizes by saying so in their own prompt (for example "
            f'"merge PR #{pr} after the checks pass"), or on GitHub (CANONICAL_LAW §6.2.13)'
        )
        return refused
    instruction = verdict["instruction"]

    try:
        files = pull_request_files(repo, pr)
    except RuntimeError as exc:
        refused["reason"] = f"cannot read the pull request's files ({exc})"
        refused["instruction"] = instruction
        return refused
    protected = protected_paths_in(files)
    if protected is None or protected:
        shown = ", ".join(sorted(protected)[:6]) if protected else "<file list unknown>"
        refused["reason"] = (
            "L9-ORG-007: this change touches governance-protected paths "
            f"({shown}). An operator prompt establishes no GitHub identity, so it cannot be "
            "the independent human authorization that invariant requires. Required instead: "
            f"an APPROVED review on {live} by a human with write access who is not the author "
            f"({author or 'unknown'}), or that human's exact line "
            f"`authorize merge {repo}#{pr}@{live}` on the pull request"
        )
        refused["instruction"] = instruction
        return refused

    return {
        "authorized": True,
        "reason": "live operator instruction covers an open, unprotected PR at its live head",
        "instruction": instruction,
        "pull_request": summary,
    }


def operator_provenance(
    instruction: dict[str, Any], pull_request: dict[str, Any]
) -> dict[str, Any]:
    return {
        "channel": OPERATOR_CHANNEL,
        "recorded_by": "agent",
        "instruction_id": instruction.get("id"),
        "host": instruction.get("host"),
        "session_id": instruction.get("session_id"),
        "scope": instruction.get("scope"),
        "recorded_at": instruction.get("recorded_at"),
        "instruction_expires_at": instruction.get("expires_at"),
        "prompt_sha256": instruction.get("prompt_sha256"),
        "excerpt": instruction.get("excerpt"),
        "pull_request_author": pull_request.get("author"),
    }


def main(
    argv: list[str] | None = None,
    *,
    confirm: Callable[[str], bool] | None = None,
    instruction_path: Path | None = None,
    pull_request: Callable[[str, int], dict[str, Any]] = fetch_pull_request,
    pull_request_files: Callable[[str, int], list[str] | None] = fetch_pull_request_files,
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
            pull_request_files=pull_request_files,
        )
        if not verdict["authorized"]:
            print(json.dumps({**verdict, "status": "MERGE_PENDING"}, indent=2, sort_keys=True))
            print(f"REFUSED: {verdict['reason']}", file=sys.stderr)
            return OPERATOR_REFUSED_EXIT
        instruction = verdict["instruction"]
        provenance = operator_provenance(instruction, verdict["pull_request"])
        stamp = time.time() if now is None else now
        remaining = int(float(instruction.get("expires_at") or 0) - stamp)
        ttl = max(1, min(ttl, remaining))
        reason = reason or f"operator prompt instruction {instruction.get('id')}"
    else:
        token = confirmation_token(args.repo, pr, sha)
        if not (confirm or confirm_on_terminal)(token):
            print(
                "REFUSED: no human confirmed this grant on a controlling terminal, and no "
                "--operator-instruction was requested. Merge grants are issued by a human "
                "(CANONICAL_LAW §6.2.12, §6.2.13); an agent reports MERGE_PENDING instead "
                "of running this mode.",
                file=sys.stderr,
            )
            return NOT_CONFIRMED_EXIT
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

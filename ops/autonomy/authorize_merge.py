#!/usr/bin/env python3
"""Issue a human merge grant: one repository, one PR, one exact head, expiring.

A grant is the only ordinary merge authority ``merge_gate.py`` and
``stack_safe_merge.py`` accept (CANONICAL_LAW §6.2.12). It is written only after
a human types the exact target back on the controlling terminal. Invoking
/l9-pr-remediation, entering Converge, green CI, an L4 release, ``make pr``, a
DAG step, or an agent instruction is NOT a grant, and an agent never runs this
script: autonomous remediation stops at MERGE_PENDING and reports the exact
command below for the human to run.

    "$HOME/.cursor-governance/.venv/bin/python" \\
        "$HOME/.cursor-governance/ops/autonomy/authorize_merge.py" \\
        --repo owner/name --pr 53 --head-sha <40-hex> --reason "reviewed; merge it"

Repository-wide authority (``--all-open`` / ``--pr '*'``) is not issuable, and a
receipt with no head binding, no ``issuer: human``, or a lifetime over
MAX_TTL_SECONDS authorizes nothing. The terminal challenge proves an
interactive caller, not identity: on a host where the worker runs as the same
OS account it is defeatable by deliberate forgery, which is the host-enforcement
gap §6.2.12 names.

It does not merge. It does not authorize force-push, admin-merge, or hard-reset.

Metadata:
  layer: ops
  role: merge_authorization
  version: 3.0.0
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

DEFAULT_TTL_SECONDS = 60 * 60
#: merge_gate.py refuses any grant whose expiry lies further out than this.
MAX_TTL_SECONDS = 4 * 60 * 60
ISSUER = "human"
DEFAULT_REASON = "human merge grant"
#: Exit status when no human confirmed the grant on a terminal.
NOT_CONFIRMED_EXIT = 3

_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")

REPO_WIDE_REFUSAL = (
    "Repository-wide merge authority is not issuable (CANONICAL_LAW §6.2.12). "
    "Issue one grant per PR and exact head SHA: "
    "authorize_merge.py --repo <owner/name> --pr <n> --head-sha <40-hex>."
)


def auth_path(explicit: str) -> Path:
    if explicit:
        return Path(explicit).expanduser()
    return Path.home() / ".l9" / "autonomy" / "merge-authorization.json"


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
    entry = {
        "repo": repo,
        "pr": normalized_pr,
        "head_sha": sha,
        "issuer": ISSUER,
        "issued_at": stamp,
        "expires_at": stamp + ttl_seconds,
        "reason": reason.strip(),
    }
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


def main(argv: list[str] | None = None, *, confirm: Callable[[str], bool] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr", default="", help="the PR number this grant covers")
    parser.add_argument("--head-sha", default="", help="exact 40-hex head the human reviewed")
    parser.add_argument(
        "--all-open",
        action="store_true",
        help="refused: repository-wide merge authority is not issuable",
    )
    parser.add_argument("--reason", default=DEFAULT_REASON)
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

    token = confirmation_token(args.repo, pr, sha)
    if not (confirm or confirm_on_terminal)(token):
        print(
            "REFUSED: no human confirmed this grant on a controlling terminal. Merge "
            "grants are issued by a human (CANONICAL_LAW §6.2.12); an agent reports "
            "MERGE_PENDING instead of running this script.",
            file=sys.stderr,
        )
        return NOT_CONFIRMED_EXIT
    try:
        entry = write_authorization(
            repo=args.repo,
            pr=pr,
            head_sha=sha,
            reason=args.reason,
            path=auth_path(args.auth_file),
            ttl_seconds=args.ttl_seconds,
        )
    except ValueError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(entry, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

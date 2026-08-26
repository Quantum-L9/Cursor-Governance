#!/usr/bin/env python3
"""Write merge authorization for ordinary gh pr merge.

Invoking /l9-pr-remediation (Converge) is the operator act that authorizes
merge of open PRs in the target repo after they are green and mergeable.
This script writes the receipt ops/autonomy/merge_gate.py accepts.

It does not merge. It does not authorize force-push, admin-merge, or hard-reset.

Default scope is the whole repo (pr: "*") so remediations can finish every
open PR. Pass --pr N to scope one pull request.

Metadata:
  layer: ops
  role: merge_authorization
  version: 2.0.0
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

DEFAULT_TTL_SECONDS = 4 * 60 * 60
REPO_SCOPE = "*"
DEFAULT_REASON = "l9-pr-remediation invoked"
DEFAULT_SOURCE = "l9-pr-remediation"


def auth_path(explicit: str) -> Path:
    if explicit:
        return Path(explicit).expanduser()
    return Path.home() / ".l9" / "autonomy" / "merge-authorization.json"


def _normalize_pr(pr: str | int) -> str | int:
    text = str(pr).strip()
    if text in {REPO_SCOPE, "all", "ALL"}:
        return REPO_SCOPE
    if not text.isdigit():
        raise ValueError("pr must be a number or *")
    return int(text)


def write_authorization(
    *,
    repo: str,
    reason: str,
    path: Path,
    pr: str | int = REPO_SCOPE,
    source: str = DEFAULT_SOURCE,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    head_sha: str = "",
    now: float | None = None,
) -> dict[str, Any]:
    if not repo or "/" not in repo:
        raise ValueError("repo must be owner/name")
    if not reason.strip():
        raise ValueError("reason is required")
    if ttl_seconds <= 0:
        raise ValueError("ttl_seconds must be positive (merge receipts must expire)")
    normalized_pr = _normalize_pr(pr)
    sha = head_sha.strip().lower()
    if sha and not (7 <= len(sha) <= 40 and all(c in "0123456789abcdef" for c in sha)):
        raise ValueError("head_sha must be a hex commit id (7-40 chars)")
    current: dict[str, Any] = {"authorizations": []}
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict) and isinstance(loaded.get("authorizations"), list):
                current = loaded
        except json.JSONDecodeError:
            current = {"authorizations": []}
    stamp = now if now is not None else time.time()
    entry = {
        "repo": repo,
        "pr": normalized_pr,
        "source": source.strip() or DEFAULT_SOURCE,
        "expires_at": int(stamp) + ttl_seconds,
        "reason": reason.strip(),
    }
    if sha:
        entry["head_sha"] = sha
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
    payload = {"authorizations": entries}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return entry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument(
        "--pr",
        default="",
        help="PR number, or * for every open PR in --repo (default: *)",
    )
    parser.add_argument(
        "--all-open",
        action="store_true",
        help="Authorize every open PR in --repo (same as --pr *)",
    )
    parser.add_argument("--reason", default=DEFAULT_REASON)
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--auth-file", default="")
    parser.add_argument("--ttl-seconds", type=int, default=DEFAULT_TTL_SECONDS)
    parser.add_argument(
        "--head-sha",
        default="",
        help="Bind the receipt to this immutable head revision; a moved HEAD is then rejected",
    )
    args = parser.parse_args()
    pr: str | int = REPO_SCOPE
    if args.pr and not args.all_open:
        pr = args.pr
    entry = write_authorization(
        repo=args.repo,
        pr=pr,
        reason=args.reason,
        source=args.source,
        path=auth_path(args.auth_file),
        ttl_seconds=args.ttl_seconds,
        head_sha=args.head_sha,
    )
    print(json.dumps(entry, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

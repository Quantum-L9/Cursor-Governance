#!/usr/bin/env python3
"""Write a one-shot merge authorization for one campaign PR.

Purpose: satisfy ops/autonomy/merge_gate.py after l9-pr-remediation reports
the campaign PR green and mergeable. Does not merge.

Metadata:
  parent: l9-pe-campaign-activate
  layer: script
  role: merge_authorization
  version: 1.0.0
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

DEFAULT_TTL_SECONDS = 4 * 60 * 60


def auth_path(explicit: str) -> Path:
    if explicit:
        return Path(explicit).expanduser()
    return Path.home() / ".l9" / "autonomy" / "merge-authorization.json"


def write_authorization(
    *,
    repo: str,
    pr: str,
    reason: str,
    path: Path,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    now: float | None = None,
) -> dict[str, object]:
    if not repo or "/" not in repo:
        raise ValueError("repo must be owner/name")
    if not str(pr).isdigit():
        raise ValueError("pr must be a number")
    if not reason.strip():
        raise ValueError("reason is required")
    current: dict[str, object] = {"authorizations": []}
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
        "pr": int(pr),
        "expires_at": int(stamp) + ttl_seconds,
        "reason": reason.strip(),
    }
    entries = [
        item
        for item in current.get("authorizations", [])
        if isinstance(item, dict)
        and not (str(item.get("repo")) == repo and str(item.get("pr")) == str(pr))
    ]
    entries.append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"authorizations": entries}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return entry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--auth-file", default="")
    parser.add_argument("--ttl-seconds", type=int, default=DEFAULT_TTL_SECONDS)
    args = parser.parse_args()
    entry = write_authorization(
        repo=args.repo,
        pr=args.pr,
        reason=args.reason,
        path=auth_path(args.auth_file),
        ttl_seconds=args.ttl_seconds,
    )
    print(json.dumps(entry, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

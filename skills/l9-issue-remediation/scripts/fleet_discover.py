#!/usr/bin/env python3
"""Discover non-archived GitHub org repos via gh (stdlib + gh CLI).

Read-only. Emits secret-free JSON: [{name, full_name, url, updated_at, description}].
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

_GH_OWNER_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})")


def _validated_owner(value: str) -> str:
    """Return ``value`` once proven to be a GitHub owner slug.

    It is passed to ``gh`` as a command argument. The rule that matters is the
    leading character: a value such as ``--template=...`` is an ordinary string
    to ``subprocess`` but an option to ``gh``, which turns a repository listing
    into an attacker-chosen gh invocation.
    """
    if not _GH_OWNER_RE.fullmatch(value):
        raise SystemExit(f"BLOCKED: not a valid GitHub owner: {value!r}")
    return value


def _validated_output(value: str) -> Path:
    base = Path.cwd().resolve()
    resolved = (base / value).resolve()
    if resolved != base and base not in resolved.parents:
        raise SystemExit("BLOCKED: --output must stay within the working directory")
    return resolved


def discover(org: str, limit: int) -> list[dict]:
    if not shutil.which("gh"):
        raise SystemExit("BLOCKED: gh CLI not found on PATH")
    cmd = [
        "gh",
        "repo",
        "list",
        org,
        "--limit",
        str(limit),
        "--json",
        "name,nameWithOwner,url,isArchived,updatedAt,description",
    ]
    try:
        raw = subprocess.check_output(cmd, text=True, timeout=120)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"BLOCKED: gh repo list failed: {exc}") from exc
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SystemExit(f"BLOCKED: gh repo list error: {exc}") from exc
    try:
        rows = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"BLOCKED: gh returned non-JSON: {exc}") from exc
    if not isinstance(rows, list):
        raise SystemExit("BLOCKED: unexpected gh payload")
    out: list[dict] = []
    for row in rows:
        if row.get("isArchived"):
            continue
        out.append(
            {
                "name": row.get("name"),
                "full_name": row.get("nameWithOwner"),
                "url": row.get("url"),
                "updated_at": row.get("updatedAt"),
                "description": row.get("description") or "",
            }
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--org", default="Quantum-L9")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--output", default="fleet.json")
    args = parser.parse_args()
    if args.limit < 1 or args.limit > 1000:
        raise SystemExit("BLOCKED: --limit must be 1..1000")
    repos = discover(_validated_owner(args.org), args.limit)
    payload = {
        "org": args.org,
        "generated_at": datetime.now(UTC).isoformat(),
        "count": len(repos),
        "repos": repos,
    }
    path = _validated_output(args.output)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "count": len(repos), "output": str(path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

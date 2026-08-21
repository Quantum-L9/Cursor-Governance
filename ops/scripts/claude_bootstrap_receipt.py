#!/usr/bin/env python3
"""Read the Claude adapter bootstrap receipt and classify it at read time.

Companion to governance_refresh_receipt.py, and it borrows that module's
timestamp and TTL handling rather than re-deriving it — one expiry rule for
every L9 receipt (INV-2).

The distinction this module exists to preserve:

    never_ran   no receipt on disk. The installer did not reach its own
                bookkeeping, so nothing about the environment is established.
                This is what the audited runtime actually looked like (B-04).
    failed      the installer ran and recorded the stage it died at.
    blocked     a required component could not be wired.
    degraded    an optional component is unavailable.
    ready       the required contract is satisfied.
    unknown     a receipt exists but has outlived its TTL, so it describes a
                state nobody has observed since.

`never_ran` and `ready` are the two that get confused when a reader treats a
missing file as benign, which is why they are separated here rather than in each
caller.

Usage:
  python3 ops/scripts/claude_bootstrap_receipt.py --read
  python3 ops/scripts/claude_bootstrap_receipt.py --read --json
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from governance_refresh_receipt import _parse_timestamp  # noqa: PLC2701

SCHEMA = "l9.claude-bootstrap.v1"

NEVER_RAN = "never_ran"
UNKNOWN = "unknown"
FAILED = "failed"
BLOCKED = "blocked"
DEGRADED = "degraded"
READY = "ready"

DEFAULT_TTL_SECONDS = 86400

#: Component keys the receipt carries, in the order a reader should show them.
COMPONENTS = (
    "shared_bootstrap",
    "settings",
    "skills",
    "rules",
    "capabilities",
    "memory",
    "mcp",
    "plugins",
)


def receipt_path(env: dict[str, str] | None = None) -> Path:
    source = os.environ if env is None else env
    override = (source.get("L9_CLAUDE_BOOTSTRAP_RECEIPT") or "").strip()
    if override:
        return Path(override)
    return Path(source.get("HOME", str(Path.home()))) / ".l9" / "claude" / "bootstrap-state.json"


def evaluate(receipt: dict[str, Any] | None, *, now: datetime | None = None) -> dict[str, Any]:
    moment = now or datetime.now(timezone.utc)

    if receipt is None:
        return {
            "state": NEVER_RAN,
            "reason": "no bootstrap receipt on disk — the adapter installer never completed",
            "remediation": "bash environment/agents/adapters/claude-code/install.sh",
            "components": {},
        }

    components = {key: receipt.get(key, "UNKNOWN") for key in COMPONENTS}
    carried = {
        "components": components,
        "stage": receipt.get("stage"),
        "workspace": receipt.get("workspace"),
        "governance_revision": receipt.get("governance_revision"),
        "generated_at": receipt.get("generated_at"),
        "remediation": receipt.get("remediation", ""),
    }

    written = _parse_timestamp(str(receipt.get("generated_at", "")))
    if written is None:
        return {"state": UNKNOWN, "reason": "receipt carries no parseable UTC timestamp", **carried}

    age = int((moment - written).total_seconds())
    ttl = receipt.get("ttl_seconds")
    ttl = DEFAULT_TTL_SECONDS if not isinstance(ttl, int) or ttl <= 0 else ttl
    carried["age_seconds"] = age
    if age > ttl:
        return {"state": UNKNOWN, "reason": f"receipt expired ({age}s old, ttl {ttl}s)", **carried}

    recorded = str(receipt.get("state") or receipt.get("overall") or "").upper()
    if recorded == "FAILED":
        return {
            "state": FAILED,
            "reason": f"installer failed at stage '{receipt.get('stage', 'unknown')}'",
            **carried,
        }
    if recorded == "BLOCKED" or "BLOCKED" in components.values():
        return {"state": BLOCKED, "reason": _first_non_ready(components, "BLOCKED"), **carried}
    if recorded == "DEGRADED" or "DEGRADED" in components.values():
        return {"state": DEGRADED, "reason": _first_non_ready(components, "DEGRADED"), **carried}
    if recorded == "READY":
        return {"state": READY, "reason": f"all components READY ({age}s ago)", **carried}
    return {"state": UNKNOWN, "reason": f"unrecognised recorded state {recorded!r}", **carried}


def _first_non_ready(components: dict[str, Any], level: str) -> str:
    named = [key for key, value in components.items() if value == level]
    return f"{level.lower()}: {', '.join(named)}" if named else level.lower()


def read(path: Path | None = None, *, now: datetime | None = None) -> dict[str, Any]:
    target = path or receipt_path()
    if not target.is_file():
        return evaluate(None, now=now)
    try:
        parsed = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {
            "state": UNKNOWN,
            "reason": f"receipt at {target} is unreadable or malformed",
            "components": {},
        }
    if not isinstance(parsed, dict):
        return {"state": UNKNOWN, "reason": "receipt is not a JSON object", "components": {}}
    return evaluate(parsed, now=now)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--read", action="store_true", required=True)
    parser.add_argument("--path", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = read(Path(args.path) if args.path else None)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"claude bootstrap: {result['state']} — {result['reason']}")
        for key, value in (result.get("components") or {}).items():
            print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

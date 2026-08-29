#!/usr/bin/env python3
"""Read the governance refresh receipt and recompute its state AT READ TIME.

The receipt is written by the Claude Code SessionStart hook. Its `state` field
records what was true when it was written; this module never trusts that field,
because the defect it exists to prevent is exactly a receipt whose claim
outlived its truth. The audit found `gov-refresh.log` still reading
`fresh 941ab77` days after it was written, while the clone it described sat four
commits behind main and the hook that would have refreshed it had not run since
(finding B-05).

State is therefore derived from three independent signals, any one of which can
demote:

    age         refreshed_at + ttl_seconds elapsed        -> unknown
    divergence  local_sha != origin_sha                   -> stale
    distance    commits_behind > 0                        -> stale

Absence of the receipt is `never_ran` — a distinct state from `unknown`, because
"the refresh never happened" and "the refresh happened but I cannot vouch for it
now" call for different responses (INV-2).

Usage:
  python3 ops/scripts/governance_refresh_receipt.py --read
  python3 ops/scripts/governance_refresh_receipt.py --read --json
  python3 ops/scripts/governance_refresh_receipt.py --read --path /some/receipt.json
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = "l9.governance-refresh.v1"

#: Terminal states. `fresh` is the only one that means "you may rely on the
#: governance tree being current".
FRESH = "fresh"
STALE = "stale"
UNKNOWN = "unknown"
NEVER_RAN = "never_ran"

DEFAULT_TTL_SECONDS = 3600
_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def receipt_path(env: dict[str, str] | None = None) -> Path:
    source = os.environ if env is None else env
    override = (source.get("L9_GOV_REFRESH_RECEIPT") or "").strip()
    if override:
        return Path(override)
    return Path(source.get("HOME", str(Path.home()))) / ".l9" / "claude" / "gov-refresh.json"


def _parse_timestamp(raw: str) -> datetime | None:
    try:
        return datetime.strptime(raw, _TIMESTAMP_FORMAT).replace(tzinfo=UTC)
    except (TypeError, ValueError):
        return None


def evaluate(receipt: dict[str, Any] | None, *, now: datetime | None = None) -> dict[str, Any]:
    """Derive the live state of a parsed receipt. Pure; `now` is injectable."""
    moment = now or datetime.now(UTC)

    if receipt is None:
        return {
            "state": NEVER_RAN,
            "reason": "no governance refresh receipt on disk",
            "age_seconds": None,
        }

    written = _parse_timestamp(str(receipt.get("refreshed_at", "")))
    if written is None:
        return {
            "state": UNKNOWN,
            "reason": "receipt carries no parseable UTC timestamp",
            "age_seconds": None,
            **_carry(receipt),
        }

    age = int((moment - written).total_seconds())
    ttl = receipt.get("ttl_seconds")
    ttl = DEFAULT_TTL_SECONDS if not isinstance(ttl, int) or ttl <= 0 else ttl
    carried = {"age_seconds": age, **_carry(receipt)}

    # Expiry dominates every other signal. A receipt past its TTL describes a
    # world we have not observed since, whatever it claimed at write time.
    if age > ttl:
        return {
            "state": UNKNOWN,
            "reason": f"receipt expired ({age}s old, ttl {ttl}s)",
            **carried,
        }

    outcome = str(receipt.get("outcome", ""))
    if outcome == "fetch-failed":
        return {"state": UNKNOWN, "reason": "last fetch failed; origin state unobserved", **carried}
    if outcome == "reset-failed":
        return {"state": STALE, "reason": "fetch succeeded but reset to origin failed", **carried}

    local_sha = str(receipt.get("local_sha", ""))
    origin_sha = str(receipt.get("origin_sha", ""))
    if not local_sha or local_sha == "unknown":
        return {"state": UNKNOWN, "reason": "receipt records no local revision", **carried}
    if origin_sha and origin_sha != "unknown" and origin_sha != local_sha:
        return {
            "state": STALE,
            "reason": f"local {local_sha[:8]} != origin {origin_sha[:8]}",
            **carried,
        }

    behind = receipt.get("commits_behind")
    if isinstance(behind, int) and behind > 0:
        return {"state": STALE, "reason": f"{behind} commits behind origin", **carried}

    return {"state": FRESH, "reason": f"refreshed {age}s ago at {local_sha[:8]}", **carried}


def _carry(receipt: dict[str, Any]) -> dict[str, Any]:
    return {
        "outcome": receipt.get("outcome"),
        "local_sha": receipt.get("local_sha"),
        "origin_sha": receipt.get("origin_sha"),
        "refreshed_at": receipt.get("refreshed_at"),
        "commits_behind": receipt.get("commits_behind"),
        "state_at_write": receipt.get("state"),
    }


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
            "age_seconds": None,
        }
    if not isinstance(parsed, dict):
        return {"state": UNKNOWN, "reason": "receipt is not a JSON object", "age_seconds": None}
    return evaluate(parsed, now=now)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    # Read is the only action these CLIs have, so requiring a flag to select it
    # made the obvious invocation fail with a usage error instead of answering.
    # LOADER-1: bare invocation reads; --read stays accepted so every documented
    # call site and hook keeps working unchanged.
    parser.add_argument(
        "--read",
        action="store_true",
        help="read and print the receipt (default action; accepted for compatibility)",
    )
    parser.add_argument("--path", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = read(Path(args.path) if args.path else None)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"governance refresh: {result['state']} — {result['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

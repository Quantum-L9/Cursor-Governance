#!/usr/bin/env python3
"""Classify SessionStart hydrate markdown as degraded or healthy.

The hydrate markdown emitted by compile_session_packet.py embeds the
SessionHydrationPacket as a JSON fence. That fence contains the literal
text ``"degraded": false`` on every healthy boot, so any substring or
shell-glob match on ``degraded`` reports a false DEGRADED
(FAIL: session_start_bootstrap.sh lines 449-456 pre-fix).

Authority order:
1. Packet JSON booleans — ``degraded`` (top level or ``hydrate_stats``)
   and ``hydrate_stats.close_gap`` are the only packet positives.
2. When no packet parses: explicit text markers only — a line starting
   with ``DEGRADED`` or the phrase ``hydrate CLI missing``.

Usage: classify_hydrate_state.py [--reason-limit N] < hydrate.md
Prints two lines: ``true``/``false``, then the reason (may be empty).
Exit code is always 0 (classification, not a gate).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any

_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_LEADING_DEGRADED_RE = re.compile(r"^\s*DEGRADED\b", re.MULTILINE)


def _extract_packet(markdown: str) -> dict[str, Any] | None:
    """Return the last parseable JSON object embedded in the markdown."""
    packet: dict[str, Any] | None = None
    for match in _FENCE_RE.finditer(markdown):
        try:
            candidate = json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(candidate, dict):
            packet = candidate
    if packet is not None:
        return packet
    # Unfenced fallback: a line that is itself a JSON object.
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                candidate = json.loads(stripped)
            except (json.JSONDecodeError, ValueError):
                continue
            if isinstance(candidate, dict):
                packet = candidate
    return packet


def classify(markdown: str) -> tuple[bool, str]:
    """Return (degraded, reason) for a hydrate markdown block."""
    packet = _extract_packet(markdown)
    if packet is not None:
        stats = packet.get("hydrate_stats") or {}
        if not isinstance(stats, dict):
            stats = {}
        if packet.get("degraded") is True or stats.get("degraded") is True:
            reason = str(stats.get("degrade_reason") or "").strip()
            return True, reason or "packet degraded=true"
        if stats.get("close_gap") is True:
            return True, "close_gap=true — prior session did not close"
        return False, ""
    if "hydrate CLI missing" in markdown:
        return True, "hydrate CLI missing"
    if "hydration degraded" in markdown.casefold():
        return True, "hydration degraded"
    if _LEADING_DEGRADED_RE.search(markdown):
        for line in markdown.splitlines():
            if "DEGRADED" in line:
                return True, line.strip()
        return True, "DEGRADED marker present"
    return False, ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reason-limit", type=int, default=200)
    args = parser.parse_args()
    degraded, reason = classify(sys.stdin.read())
    print("true" if degraded else "false")
    print(reason[: max(args.reason_limit, 0)].replace("\n", " "))
    return 0


if __name__ == "__main__":
    sys.exit(main())

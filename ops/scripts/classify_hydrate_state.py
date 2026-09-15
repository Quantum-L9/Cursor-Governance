#!/usr/bin/env python3
"""Classify SessionStart hydrate markdown as degraded or healthy.

The hydrate markdown emitted by compile_session_packet.py embeds the
SessionHydrationPacket as a JSON fence. That fence contains the literal
text ``"degraded": false`` on every healthy boot, so any substring or
shell-glob match on ``degraded`` reports a false DEGRADED
(FAIL: session_start_bootstrap.sh lines 449-456 pre-fix).

Degraded means one thing (ADR-0032): canonical memory ran and did not
answer. Two other conditions travel on the same packet and are reported as
*conditions*, never as degradation:

- ``ENVIRONMENT_FAULT`` — the runtime never reached memory (``BINDING_FAILED``,
  ``NAMESPACE_UNRESOLVED``); the repair is the environment, not memory.
- ``CLOSE_GAP`` — the prior session left no close receipt; the repair is
  ``/end-session``.
- ``STALE`` — a continuation exists but the repository moved on; the current
  git state wins. Not a fault at all.

Authority order:
1. Packet JSON — ``memory_degraded`` (top level or ``hydrate_stats``), falling
   back to ``degraded`` for packets that predate the split; then
   ``environment_fault`` / ``fault_class`` / ``memory_status``;
   ``close_gap``; ``continuation_stale is True`` (``None`` / ``False`` are
   not stale).
2. When no packet parses: explicit text markers only — a line starting
   with ``DEGRADED`` / ``ENVIRONMENT_FAULT`` / ``CLOSE_GAP`` or the phrase
   ``hydrate CLI missing``.

Usage: classify_hydrate_state.py [--reason-limit N] < hydrate.md
Prints three lines: ``true``/``false`` (degraded), the degraded reason (may be
empty), then the condition (``ENVIRONMENT_FAULT`` / ``CLOSE_GAP`` / ``STALE``
or empty) followed by ``: <detail>`` when there is one. Consumers that read
only the first two lines are unaffected.
Exit code is always 0 (classification, not a gate).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from typing import Any

_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_LEADING_DEGRADED_RE = re.compile(r"^\s*DEGRADED\b", re.MULTILINE)
_LEADING_ENVIRONMENT_RE = re.compile(r"^\s*ENVIRONMENT_FAULT\b", re.MULTILINE)
_LEADING_CLOSE_GAP_RE = re.compile(r"^\s*CLOSE_GAP\b", re.MULTILINE)

CONDITION_ENVIRONMENT_FAULT = "ENVIRONMENT_FAULT"
CONDITION_CLOSE_GAP = "CLOSE_GAP"
CONDITION_STALE = "STALE"
_ENVIRONMENT_STATUSES = {"BINDING_FAILED", "NAMESPACE_UNRESOLVED"}


@dataclass(frozen=True)
class HydrateVerdict:
    degraded: bool
    reason: str
    condition: str = ""
    condition_detail: str = ""

    @property
    def condition_line(self) -> str:
        if not self.condition:
            return ""
        if self.condition_detail:
            return f"{self.condition}: {self.condition_detail}"
        return self.condition


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


def _first(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _memory_degraded(packet: dict[str, Any], stats: dict[str, Any]) -> bool:
    typed = _first(packet.get("memory_degraded"), stats.get("memory_degraded"))
    if typed is not None:
        return typed is True
    # Pre-split packet: ``degraded`` was ORed with close_gap. Subtract the
    # lifecycle bit so an old packet still reads as memory truth.
    legacy = packet.get("degraded") is True or stats.get("degraded") is True
    if legacy and stats.get("close_gap") is True and not stats.get("memory_status"):
        return False
    if legacy and str(stats.get("memory_status") or "") in _ENVIRONMENT_STATUSES:
        return False
    return legacy


def _environment_fault(packet: dict[str, Any], stats: dict[str, Any]) -> bool:
    typed = _first(packet.get("environment_fault"), stats.get("environment_fault"))
    if typed is not None:
        return typed is True
    if str(stats.get("fault_class") or "") == "environment":
        return True
    return str(stats.get("memory_status") or "") in _ENVIRONMENT_STATUSES


def _first_marker_line(markdown: str, token: str) -> str:
    for line in markdown.splitlines():
        if token in line:
            return line.strip()
    return f"{token} marker present"


def classify_verdict(markdown: str) -> HydrateVerdict:
    """Full verdict: degraded flag + reason, and the typed non-degraded condition."""
    packet = _extract_packet(markdown)
    if packet is not None:
        stats = packet.get("hydrate_stats") or {}
        if not isinstance(stats, dict):
            stats = {}
        if _memory_degraded(packet, stats):
            reason = str(stats.get("degrade_reason") or packet.get("degrade_reason") or "").strip()
            return HydrateVerdict(True, reason or "packet memory_degraded=true")
        if _environment_fault(packet, stats):
            detail = str(
                stats.get("environment_fault_reason") or stats.get("memory_status") or ""
            ).strip()
            return HydrateVerdict(False, "", CONDITION_ENVIRONMENT_FAULT, detail)
        if stats.get("close_gap") is True or packet.get("close_gap") is True:
            detail = str(
                packet.get("close_gap_reason")
                or stats.get("close_gap_reason")
                or "prior session did not close"
            ).strip()
            return HydrateVerdict(False, "", CONDITION_CLOSE_GAP, detail)
        if stats.get("continuation_stale") is True:
            return HydrateVerdict(False, "", CONDITION_STALE, "continuation_stale=true")
        return HydrateVerdict(False, "")
    if "hydrate CLI missing" in markdown:
        return HydrateVerdict(True, "hydrate CLI missing")
    if "hydration degraded" in markdown.casefold():
        return HydrateVerdict(True, "hydration degraded")
    if _LEADING_DEGRADED_RE.search(markdown):
        return HydrateVerdict(True, _first_marker_line(markdown, "DEGRADED"))
    if _LEADING_ENVIRONMENT_RE.search(markdown):
        return HydrateVerdict(
            False, "", CONDITION_ENVIRONMENT_FAULT, _first_marker_line(markdown, "REPAIR:")
        )
    if _LEADING_CLOSE_GAP_RE.search(markdown):
        return HydrateVerdict(False, "", CONDITION_CLOSE_GAP, "prior session did not close")
    return HydrateVerdict(False, "")


def classify(markdown: str) -> tuple[bool, str]:
    """Return (degraded, reason) for a hydrate markdown block.

    ``degraded`` is canonical memory degradation only. Close-gap, staleness and
    an unbound runtime are conditions — read them from :func:`classify_verdict`.
    """
    verdict = classify_verdict(markdown)
    return verdict.degraded, verdict.reason


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reason-limit", type=int, default=200)
    args = parser.parse_args()
    verdict = classify_verdict(sys.stdin.read())
    limit = max(args.reason_limit, 0)
    print("true" if verdict.degraded else "false")
    print(verdict.reason[:limit].replace("\n", " "))
    print(verdict.condition_line[:limit].replace("\n", " "))
    return 0


if __name__ == "__main__":
    sys.exit(main())

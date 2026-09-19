"""Classify a canonical record as an agent-lane write (ADR-0034).

SessionStart's 24h prefetch and sessionEnd capsule enrichment need the
records a model wrote mid-session (``memory.write_agent`` / MCP write),
not hook-lane capsules, META closes, or operator CLI writes. Classification
is client-side over the receipt the control plane already returned: this
module does not open the store (INV-03).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta
from typing import Any

from ops.memory.session_contracts import CANDIDATE_CLASS, CONTINUATION_SCHEMA, PRODUCER

AGENT_LANE_WINDOW = timedelta(hours=24)
AGENT_LANE_LIMIT = 20

_HOOK_MEMORY_CLASSES = frozenset({"meta", "session_summary"})
_HOOK_PRODUCER_MARKERS = (
    PRODUCER,
    "session-end",
    "session_end",
    "cursor-session-end",
    "claude-session-end",
    "legacy-reconciliation",
)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _provenance(record: Any) -> Mapping[str, Any]:
    metadata = _mapping(getattr(record, "metadata", None))
    raw = _mapping(getattr(record, "raw", None))
    for candidate in (
        metadata.get("provenance"),
        raw.get("provenance"),
        metadata,
    ):
        if isinstance(candidate, Mapping) and (
            "producer" in candidate or "source_agent_id" in candidate
        ):
            return candidate
    return {}


def is_agent_lane_record(record: Any) -> bool:
    """True when ``record`` looks like a mid-session agent write.

    Fail closed toward "not agent": a typed continuation, a META close, or a
    Cursor-Governance hook producer is never treated as agent-lane evidence.
    """

    tags = tuple(str(item) for item in (getattr(record, "tags", ()) or ()))
    if CANDIDATE_CLASS in tags:
        return False
    metadata = _mapping(getattr(record, "metadata", None))
    if metadata.get("payload_schema") == CONTINUATION_SCHEMA:
        return False
    memory_class = str(getattr(record, "memory_class", "") or "").strip().lower()
    if memory_class in _HOOK_MEMORY_CLASSES:
        return False
    provenance = _provenance(record)
    producer = str(provenance.get("producer") or metadata.get("producer") or "")
    lowered = producer.lower()
    if any(marker.lower() in lowered for marker in _HOOK_PRODUCER_MARKERS if marker):
        return False
    if any(tag.startswith("agent:") for tag in tags):
        return True
    return bool(provenance.get("source_agent_id"))


__all__ = [
    "AGENT_LANE_LIMIT",
    "AGENT_LANE_WINDOW",
    "is_agent_lane_record",
]

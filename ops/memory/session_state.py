"""Local, non-authoritative memory session state (plan §22).

Replaces the provider state file (``~/.cursor/graphiti-state/*``) whose
fields claimed Graphiti authority. What survives is orchestration evidence
only: which session hydrated, what it requested, and digests of what came
back. Nothing here is memory truth, and no gate may treat it as a grant.

Since stage C8 the Cursor write gates read this file too. The only question
they may ask of it is "was this session hydrated recently, or did the agent
consult memory for the current task?" — the permitted gate shape is
``fresh hydration? yes → continue; no → hydrate, then continue``. A subagent
reads its parent's state and never writes one of its own.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ops.memory.hydration import CanonicalHydration

ENV_STATE_DIR = "L9_MEMORY_SESSION_STATE_DIR"
STATE_SCHEMA = "cursor.memory-session-state/v1"
#: Task signatures the agent explicitly satisfied by consulting memory
#: (postToolUse on a canonical memory tool call). Cleared when the task changes.
SATISFIED_KEY = "satisfied_task_signatures"
DEFAULT_FRESHNESS_MINUTES = 30
#: Hydration outcomes that count as "memory answered".
FRESH_STATUSES = frozenset({"OK", "NO_HITS"})
_SAFE = re.compile(r"[^A-Za-z0-9_.-]")


def state_dir(directory: str | Path | None = None) -> Path:
    if directory is not None:
        return Path(directory).expanduser()
    configured = os.environ.get(ENV_STATE_DIR, "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".cursor" / "l9-memory-session-state"


def state_path(session_id: str, directory: str | Path | None = None) -> Path:
    safe = _SAFE.sub("_", session_id or "default")[:120] or "default"
    return state_dir(directory) / f"{safe}.json"


def _write(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_session_state(
    session_id: str,
    hydration: CanonicalHydration,
    *,
    directory: str | Path | None = None,
) -> Path:
    receipts = list(hydration.integration_receipts)
    previous = read_session_state(session_id, directory=directory) or {}
    payload = {
        "schema": STATE_SCHEMA,
        "authority": "none",
        "session_id": session_id,
        "task_signature": hydration.task_signature,
        # Explicit satisfactions survive a re-hydration of the same session.
        SATISFIED_KEY: list(previous.get(SATISFIED_KEY) or []),
        "namespace_request": {
            "write": hydration.namespace_context.write_namespace_hint,
            "read": list(hydration.requested_namespaces),
        },
        "memory_status": hydration.status,
        "hydration_receipt_digest": hydration.hydrate_receipt_digest,
        "canonical_result_digest": hashlib.sha256(
            json.dumps(
                {
                    "record_ids": list(hydration.record_ids),
                    "continuation": hydration.continuation.record_id
                    if hydration.continuation
                    else None,
                },
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest(),
        "integration_receipt_ids": [
            receipt.get("canonical_receipt_id") for receipt in receipts if isinstance(receipt, dict)
        ],
        "timestamp": datetime.now(UTC).isoformat(),
    }
    return _write(state_path(session_id, directory), payload)


def read_session_state(
    session_id: str, *, directory: str | Path | None = None
) -> dict[str, Any] | None:
    path = state_path(session_id, directory)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get("schema") == STATE_SCHEMA else None


# ---------------------------------------------------------------------------
# Gate evidence (stage C8): what the Cursor hooks may ask of this file
# ---------------------------------------------------------------------------


def set_task_signature(
    session_id: str, signature: str, *, directory: str | Path | None = None
) -> dict[str, Any]:
    """Record the current task; a changed task clears explicit satisfactions.

    Creates a minimal state when none exists so the signature survives until
    the session hydrates; the stub carries no ``memory_status`` and therefore
    satisfies nothing on its own.
    """
    data = read_session_state(session_id, directory=directory) or {
        "schema": STATE_SCHEMA,
        "authority": "none",
        "session_id": session_id,
        "memory_status": None,
        "timestamp": None,
    }
    if data.get("task_signature") != signature:
        data["task_signature"] = signature
        data[SATISFIED_KEY] = []
    _write(state_path(session_id, directory), data)
    return data


def mark_satisfied(session_id: str, *, directory: str | Path | None = None) -> bool:
    """The agent consulted memory for the current task; remember that."""
    data = read_session_state(session_id, directory=directory)
    if not data:
        return False
    signature = data.get("task_signature")
    if not signature:
        return False
    satisfied = list(data.get(SATISFIED_KEY) or [])
    if signature not in satisfied:
        satisfied.append(signature)
    data[SATISFIED_KEY] = satisfied
    _write(state_path(session_id, directory), data)
    return True


def hydration_is_fresh(
    state: dict[str, Any] | None,
    *,
    ttl_minutes: int = DEFAULT_FRESHNESS_MINUTES,
    now: datetime | None = None,
) -> bool:
    """A recent canonical hydration that memory actually answered."""
    if not state or str(state.get("memory_status") or "") not in FRESH_STATUSES:
        return False
    raw = state.get("timestamp")
    if not raw:
        return False
    try:
        then = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return False
    if then.tzinfo is None:
        then = then.replace(tzinfo=UTC)
    age_minutes = ((now or datetime.now(UTC)) - then).total_seconds() / 60
    return 0 <= age_minutes <= ttl_minutes


def memory_satisfied(
    state: dict[str, Any] | None,
    *,
    task_signature: str | None = None,
    ttl_minutes: int = DEFAULT_FRESHNESS_MINUTES,
    now: datetime | None = None,
) -> bool:
    """Hydration-only gate predicate (rules/96 E7; rules/98).

    True when the agent explicitly satisfied the current task signature, or
    when the session's canonical hydration is fresh. Never consults a lock.
    """
    if not state:
        return False
    signature = task_signature or state.get("task_signature")
    if signature and signature in (state.get(SATISFIED_KEY) or []):
        return True
    return hydration_is_fresh(state, ttl_minutes=ttl_minutes, now=now)


__all__ = [
    "DEFAULT_FRESHNESS_MINUTES",
    "ENV_STATE_DIR",
    "FRESH_STATUSES",
    "SATISFIED_KEY",
    "STATE_SCHEMA",
    "hydration_is_fresh",
    "mark_satisfied",
    "memory_satisfied",
    "read_session_state",
    "set_task_signature",
    "state_dir",
    "state_path",
    "write_session_state",
]

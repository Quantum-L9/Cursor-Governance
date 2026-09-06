"""Local, non-authoritative memory session state (plan §22).

Replaces the provider state file (``~/.cursor/graphiti-state/*``) whose
fields claimed Graphiti authority. What survives is orchestration evidence
only: which session hydrated, what it requested, and digests of what came
back. Nothing here is memory truth, and no gate may treat it as a grant.
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


def write_session_state(
    session_id: str,
    hydration: CanonicalHydration,
    *,
    directory: str | Path | None = None,
) -> Path:
    receipts = list(hydration.integration_receipts)
    payload = {
        "schema": STATE_SCHEMA,
        "authority": "none",
        "session_id": session_id,
        "task_signature": hydration.task_signature,
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
    path = state_path(session_id, directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def read_session_state(
    session_id: str, *, directory: str | Path | None = None
) -> dict[str, Any] | None:
    path = state_path(session_id, directory)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get("schema") == STATE_SCHEMA else None


__all__ = [
    "ENV_STATE_DIR",
    "STATE_SCHEMA",
    "read_session_state",
    "state_dir",
    "state_path",
    "write_session_state",
]

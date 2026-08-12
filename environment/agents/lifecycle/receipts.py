from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from environment.agents.lifecycle.schemas import (
    ASSIGNMENT_SCHEMA,
    DISPATCH_SCHEMA,
    PR_ASSIGNMENT_SCHEMA,
    RETURN_SCHEMA,
)
from environment.agents.runtime_paths import assignment_root, subagent_receipt_root


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _digest(body: dict[str, Any]) -> str:
    payload = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def write_json(path: Path, body: dict[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = _digest(body)
    body = {**body, "receipt_digest": digest}
    path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return body


def assignment_path(assignment_id: str) -> Path:
    return assignment_root() / f"{assignment_id}.json"


def dispatch_path(assignment_id: str) -> Path:
    return subagent_receipt_root() / "dispatch" / f"{assignment_id}.json"


def return_path(assignment_id: str) -> Path:
    return subagent_receipt_root() / "return" / f"{assignment_id}.json"


def write_assignment(fields: dict[str, Any]) -> dict[str, Any]:
    body = {"schema": ASSIGNMENT_SCHEMA, "observed_at": _now(), "status": "ASSIGNED", **fields}
    return write_json(assignment_path(fields["assignment_id"]), body)


def write_dispatch(fields: dict[str, Any]) -> dict[str, Any]:
    body = {"schema": DISPATCH_SCHEMA, "observed_at": _now(), "status": "DISPATCHED", **fields}
    return write_json(dispatch_path(fields["assignment_id"]), body)


def write_return(fields: dict[str, Any]) -> dict[str, Any]:
    body = {"schema": RETURN_SCHEMA, "observed_at": _now(), "status": "RETURNED", **fields}
    return write_json(return_path(fields["assignment_id"]), body)


def write_pr_remediation_assignment(fields: dict[str, Any]) -> dict[str, Any]:
    aid = fields["assignment_id"]
    body = {
        "schema": PR_ASSIGNMENT_SCHEMA,
        "observed_at": _now(),
        "status": "ASSIGNED",
        "role": "l9-pr-remediation",
        "max_cycles": fields.get("max_cycles", 3),
        "never_merge": True,
        "never_force_push": True,
        **fields,
    }
    path = assignment_root() / "pr-remediation" / f"{aid}.json"
    return write_json(path, body)


def load_dispatch(assignment_id: str) -> dict[str, Any] | None:
    path = dispatch_path(assignment_id)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_return(assignment_id: str) -> dict[str, Any] | None:
    path = return_path(assignment_id)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))

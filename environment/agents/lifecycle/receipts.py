from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from environment.agents.lifecycle.schemas import (
    ASSIGNMENT_SCHEMA,
    DISPATCH_SCHEMA,
    HOST_CORRELATION_SCHEMA,
    HOST_RAW_STOP_SCHEMA,
    PR_ASSIGNMENT_SCHEMA,
    RETURN_SCHEMA,
)
from environment.agents.runtime_paths import (
    agent_runtime_root,
    assignment_root,
    subagent_receipt_root,
)


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        ).encode("utf-8")
        + b"\n"
    )


def _digest(body: Any) -> str:
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def write_json(path: Path, body: dict[str, Any]) -> dict[str, Any]:
    identity = {key: value for key, value in body.items() if key != "observed_at"}
    digest = _digest(identity)
    if path.is_file():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get("receipt_digest") != digest:
            raise RuntimeError(f"receipt collision at {path}: existing body differs")
        return existing
    stored = {**body, "receipt_digest": digest}
    encoded = (
        json.dumps(stored, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    )
    _atomic_write(path, encoded)
    return stored


def assignment_path(assignment_id: str) -> Path:
    return assignment_root() / f"{assignment_id}.json"


def dispatch_path(assignment_id: str) -> Path:
    return subagent_receipt_root() / "dispatch" / f"{assignment_id}.json"


def return_path(assignment_id: str) -> Path:
    return subagent_receipt_root() / "return" / f"{assignment_id}.json"


def raw_result_path(assignment_id: str) -> Path:
    return agent_runtime_root() / "results" / "raw" / f"{assignment_id}.json"


def host_correlation_path(subagent_id: str) -> Path:
    return subagent_receipt_root() / "host-correlation" / f"{subagent_id}.json"


def host_stop_path(subagent_id: str) -> Path:
    return subagent_receipt_root() / "host-stop" / f"{subagent_id}.json"


def write_host_correlation(fields: dict[str, Any]) -> dict[str, Any]:
    subagent_id = str(fields.get("subagent_id") or "").strip()
    assignment_id = str(fields.get("assignment_id") or "").strip()
    if not subagent_id or not assignment_id:
        raise ValueError("host correlation requires subagent_id and assignment_id")
    body = {
        "schema": HOST_CORRELATION_SCHEMA,
        "observed_at": _now(),
        "status": "CORRELATED",
        **fields,
    }
    return write_json(host_correlation_path(subagent_id), body)


def load_host_correlation(subagent_id: str) -> dict[str, Any] | None:
    path = host_correlation_path(subagent_id)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def write_host_stop(subagent_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = {
        "schema": HOST_RAW_STOP_SCHEMA,
        "observed_at": _now(),
        "status": str(payload.get("status") or "UNKNOWN"),
        "subagent_id": subagent_id,
        "payload": payload,
    }
    return write_json(host_stop_path(subagent_id), body)


def write_raw_result(assignment_id: str, result: Any) -> dict[str, Any]:
    """Persist raw subagent output before any validation or distillation.

    The raw evidence object is immutable for an assignment. A repeated stop with
    identical bytes is idempotent; the same assignment with different output is
    a collision and is refused rather than silently replacing evidence.
    """

    envelope = {
        "schema": "l9.subagent-raw-result.v1",
        "assignment_id": assignment_id,
        "captured_at": _now(),
        "result": result,
    }
    # captured_at is not part of the immutable payload identity.
    identity = {
        "schema": envelope["schema"],
        "assignment_id": assignment_id,
        "result": result,
    }
    result_digest = _digest(identity)
    envelope["result_digest"] = result_digest
    path = raw_result_path(assignment_id)
    if path.is_file():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get("result_digest") != result_digest:
            raise RuntimeError(
                f"raw result collision for assignment {assignment_id}: existing evidence differs"
            )
        return {
            "path": str(path),
            "result_digest": result_digest,
            "idempotent": True,
            "result": existing.get("result"),
        }
    _atomic_write(
        path,
        json.dumps(envelope, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n",
    )
    return {
        "path": str(path),
        "result_digest": result_digest,
        "idempotent": False,
        "result": result,
    }


def load_raw_result(assignment_id: str) -> dict[str, Any] | None:
    path = raw_result_path(assignment_id)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


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


def load_assignment(assignment_id: str) -> dict[str, Any] | None:
    path = assignment_path(assignment_id)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def load_dispatch(assignment_id: str) -> dict[str, Any] | None:
    path = dispatch_path(assignment_id)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def load_return(assignment_id: str) -> dict[str, Any] | None:
    path = return_path(assignment_id)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

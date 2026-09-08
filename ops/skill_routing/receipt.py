"""Conversation-scoped, atomically written route receipts (schema v2).

Every Cursor prompt event ends in exactly one receipt state for its
conversation — ``routed``, ``no_route``, ``disabled`` or ``degraded`` — so a
prompt that produced no recommendation can never inherit an earlier route
(VSP-P0-003 / VSP-P0-004 / VSP-P1-004).

Layout: ``<state_root>/<conversation-key>/current.json``; the state root is
injectable (``state_root=`` or ``$L9_ROUTE_STATE_ROOT``) so tests never touch
``~/.cursor``. Writes are same-directory temp + flush + fsync + ``os.replace``:
a reader sees the old complete receipt or the new complete receipt, never a
torn one. Raw prompts are never stored; ``prompt_sha256`` is the only
correlation.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

from .session_locator import (
    RouteLocator,
    conversation_key,
    default_state_root,
    locator_from_payload,
    receipt_path_for,
)

RECEIPT_SCHEMA = "l9.cursor-skill-route.v2"
STATUSES = ("routed", "no_route", "disabled", "degraded")
DEFAULT_TTL_SECONDS = 1800
TTL_ENV = "L9_ROUTE_TTL_SECONDS"
_REQUIRED = (
    "schema",
    "status",
    "conversation_id",
    "generation_id",
    "workspace_roots",
    "workspace_key",
    "issued_at",
    "expires_at",
    "registry",
)


class ReceiptError(ValueError):
    """The receipt is absent, malformed, out of scope, stale, or unbound."""


def ttl_seconds() -> int:
    raw = os.environ.get(TTL_ENV, "").strip()
    if raw.isdigit() and int(raw) > 0:
        return int(raw)
    return DEFAULT_TTL_SECONDS


def prompt_digest(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def build_receipt(
    *,
    status: str,
    locator: RouteLocator,
    generation_id: str,
    registry_identity: dict[str, str] | None,
    decision: dict[str, Any] | None = None,
    materialized: dict[str, Any] | None = None,
    reason: str = "",
    prompt: str | None = None,
    now: float | None = None,
    ttl: int | None = None,
) -> dict[str, Any]:
    if status not in STATUSES:
        raise ReceiptError(f"invalid status {status!r}")
    issued = float(now if now is not None else time.time())
    lifetime = int(ttl if ttl is not None else ttl_seconds())
    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "status": status,
        "conversation_id": locator.conversation_id,
        "conversation_key": locator.conversation_key,
        "generation_id": generation_id,
        "workspace_roots": list(locator.workspace_roots),
        "workspace_key": locator.workspace_key,
        "issued_at": issued,
        "expires_at": issued + lifetime,
        "registry": dict(registry_identity or {}),
    }
    if prompt is not None:
        receipt["prompt_sha256"] = prompt_digest(prompt)
    if reason:
        receipt["reason"] = reason
    if status == "routed":
        if decision is None or materialized is None:
            raise ReceiptError("routed receipt requires decision and materialized resources")
        receipt["decision"] = {
            "route_id": str(decision.get("route_id", "")),
            "score": int(decision.get("score", 0)),
            "source": str(decision.get("source", "")),
            "primary": dict(materialized["primary"]),
            "supporting": [dict(item) for item in materialized.get("supporting", [])],
        }
    return receipt


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """Same-directory temp → flush → fsync → os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def write_receipt(receipt: dict[str, Any], state_root: Path | None = None) -> Path:
    """Persist ``receipt`` at its conversation-scoped path and return it."""
    conversation_id = str(receipt.get("conversation_id") or "")
    if not conversation_id:
        raise ReceiptError("receipt has no conversation_id")
    path = receipt_path_for(conversation_id, state_root or default_state_root())
    atomic_write_json(path, receipt)
    return path


def _resource_present(resource: Any) -> bool:
    if not isinstance(resource, dict):
        return False
    skill_md = resource.get("skill_md")
    return isinstance(skill_md, str) and Path(skill_md).is_file()


def validate_receipt(
    receipt: Any,
    *,
    conversation_id: str,
    workspace_roots: list[str] | None = None,
    generation_id: str | None = None,
    now: float | None = None,
    require_generation: bool = True,
) -> list[str]:
    """Return every reason the receipt must not be consumed (empty == valid)."""
    problems: list[str] = []
    if not isinstance(receipt, dict):
        return ["receipt is not an object"]
    missing = [key for key in _REQUIRED if key not in receipt]
    if missing:
        problems.append(f"missing fields: {missing}")
        return problems
    if receipt["schema"] != RECEIPT_SCHEMA:
        problems.append(f"schema {receipt['schema']!r} != {RECEIPT_SCHEMA}")
    if receipt["status"] not in STATUSES:
        problems.append(f"status {receipt['status']!r} invalid")
    if receipt["conversation_id"] != conversation_id:
        problems.append("conversation identity mismatch")
    if receipt.get("conversation_key") != conversation_key(conversation_id):
        problems.append("conversation key mismatch")
    if workspace_roots is not None and list(receipt["workspace_roots"]) != list(workspace_roots):
        problems.append("workspace scope mismatch")
    current = float(now if now is not None else time.time())
    try:
        if float(receipt["expires_at"]) < current:
            problems.append("receipt expired")
    except (TypeError, ValueError):
        problems.append("expires_at invalid")
    if require_generation and generation_id is not None:
        if receipt["generation_id"] != generation_id:
            problems.append("registry generation mismatch")
        if receipt["registry"].get("generation_id") != generation_id:
            problems.append("registry identity mismatch")
    if receipt["status"] == "routed":
        decision = receipt.get("decision")
        if not isinstance(decision, dict):
            problems.append("routed receipt without decision")
        else:
            if not _resource_present(decision.get("primary")):
                problems.append("materialized primary missing")
            supports = decision.get("supporting", [])
            if not isinstance(supports, list) or len(supports) > 2:
                problems.append("supporting must be a list of at most 2")
            else:
                for item in supports:
                    if not _resource_present(item):
                        problems.append("materialized support missing")
                        break
    return problems


def read_receipt(
    conversation_id: str,
    *,
    state_root: Path | None = None,
    workspace_roots: list[str] | None = None,
    generation_id: str | None = None,
    now: float | None = None,
    require_generation: bool = True,
) -> dict[str, Any]:
    """Load and validate the current receipt for a conversation or raise."""
    path = receipt_path_for(conversation_id, state_root or default_state_root())
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ReceiptError(f"receipt absent: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ReceiptError(f"receipt malformed: {path}: {exc}") from exc
    problems = validate_receipt(
        data,
        conversation_id=conversation_id,
        workspace_roots=workspace_roots,
        generation_id=generation_id,
        now=now,
        require_generation=require_generation,
    )
    if problems:
        raise ReceiptError("; ".join(problems))
    return data


__all__ = [
    "DEFAULT_TTL_SECONDS",
    "RECEIPT_SCHEMA",
    "STATUSES",
    "ReceiptError",
    "atomic_write_json",
    "build_receipt",
    "locator_from_payload",
    "prompt_digest",
    "read_receipt",
    "validate_receipt",
    "write_receipt",
]

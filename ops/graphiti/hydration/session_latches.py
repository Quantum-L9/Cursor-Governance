"""Session open/close latches and the local close obligation (ADR-0028, plan §16).

A close receipt here is a *close obligation*: it answers "do I still owe the
canonical memory service a close?" and never "what is true memory?". The
authoritative close is the canonical CloseReceipt; ``closed_canonically`` is
written only after one was validated (campaign stage C6).
"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$")

#: Canonical outcomes (stage C6) plus the legacy receipt statuses still on disk.
STATUS_CLOSED_CANONICALLY = "closed_canonically"
STATUS_CLOSE_INCOMPLETE = "close_incomplete"
#: Same idempotency key, different payload (audit CG-P1-01). The obligation is
#: neither closed nor merely unfinished: memory holds a *different* committed
#: close under this key, so retrying the same request cannot resolve it. It
#: stays a close gap on purpose — a human or a new key has to settle it.
STATUS_CLOSE_CONFLICTED = "close_conflicted"

RECEIPT_STATUSES = frozenset(
    {
        STATUS_CLOSED_CANONICALLY,
        STATUS_CLOSE_INCOMPLETE,
        STATUS_CLOSE_CONFLICTED,
        "closed",
        "closed_enqueue_failed",
        "close_failed",
        "skipped_no_project",
        "skipped_disabled",
        "skipped_cli_missing",
    }
)

SKIP_OR_FAIL_STATUSES = frozenset(
    {
        STATUS_CLOSE_INCOMPLETE,
        STATUS_CLOSE_CONFLICTED,
        "close_failed",
        "skipped_no_project",
        "skipped_disabled",
        "skipped_cli_missing",
    }
)

#: Close-obligation fields (plan §16). Scalars only; no memory content.
OBLIGATION_FIELDS = (
    "canonical_namespace_requested",
    "canonical_operation_id",
    "close_idempotency_key",
    "payload_digest",
    "continuation_status",
    "continuation_reference",
    "failure_class",
    "last_error_code",
)

#: The exact ``memory.close`` request material (audit P2-01). A retry of an
#: interrupted close replays *this* summary and digest under the recorded
#: idempotency key, never a synthesized "retry" summary: memory's replay
#: forensics compare the stored record with the replayed payload, and a
#: drifted replay is a defect to surface, not an idempotent success.
#: ``close_summary`` keeps the full close summary (close_session caps it at
#: 2000 chars), so it gets its own bound rather than the 200-char scalar cap.
CLOSE_REQUEST_FIELDS: dict[str, int] = {
    "close_summary": 2000,
    "close_capsule_digest": 200,
    "close_session_id": 200,
}


def _usable_session_id(candidate: str | None) -> str:
    """Return a real session id, or empty when the value is missing/placeholder.

    ``default`` is the last-resort shared id. Treating it as a real explicit
    value made SessionStart stamp ``default.json`` while the write gate looked
    up the hook conversation UUID.
    """
    value = str(candidate).strip() if candidate else ""
    if not value or value == "default":
        return ""
    return value[:120]


def _payload_session_id() -> str:
    """session_id from the SessionStart hook payload. Never conversation_id.

    SessionStart runs once per session. conversation_id is a later-chat key
    and must not become the session id (that lets every chat share one pass).
    """
    raw = os.environ.get("L9_HOOK_PAYLOAD", "")
    if not raw.strip():
        return ""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return ""
    if not isinstance(data, dict):
        return ""
    for key in ("session_id", "sessionId"):
        value = data.get(key)
        if isinstance(value, str):
            usable = _usable_session_id(value)
            if usable:
                return usable
    return ""


def resolve_session_id(*, explicit: str | None = None) -> str:
    """Session-scoped id for open, close, and SessionStart compile.

    Order: explicit → CURSOR_SESSION_ID → ``L9_HOOK_PAYLOAD`` session_id →
    ``default``. conversation_id is never a session id.
    """
    for candidate in (
        explicit,
        os.environ.get("CURSOR_SESSION_ID"),
        _payload_session_id(),
    ):
        usable = _usable_session_id(candidate)
        if usable:
            return usable
    return "default"


#: ``source`` stamped on a generated lifecycle id (``.l9/memory/session.json``).
SESSION_POINTER_SOURCE = "session_start_generated"


def session_pointer_path(project_dir: str | Path) -> Path:
    """Where SessionStart records the lifecycle id it generated for this repo."""
    return Path(project_dir).expanduser().resolve() / ".l9" / "memory" / "session.json"


def persisted_session_id(project_dir: str | Path) -> str:
    """The lifecycle id an earlier SessionStart persisted, or empty. Never raises."""
    try:
        pointer = session_pointer_path(project_dir)
        if not pointer.is_file():
            return ""
        data = json.loads(pointer.read_text(encoding="utf-8"))
    except (OSError, ValueError, RuntimeError):
        # ValueError covers json.JSONDecodeError; RuntimeError is expanduser()
        # with no resolvable home. A pointer that cannot be read is no pointer.
        return ""
    if not isinstance(data, dict):
        return ""
    return _usable_session_id(str(data.get("session_id") or ""))


def create_session_id(
    project_dir: str | Path, *, conversation_id: str | None = None
) -> tuple[str, str]:
    """Generate a lifecycle id and try to persist it. Never raises.

    Returns ``(session_id, persistence_error)``: the id is always usable, and
    ``persistence_error`` is ``""`` or the exception class name when the
    pointer could not be written (``.l9/memory`` is a file, ``session.json``
    is a directory, a read-only checkout). Persistence is a convenience for
    later hooks, not a precondition — the SessionStart hooks are fail-open
    and a filesystem fault must not raise into them (audit P573-F3).
    """
    generated = str(uuid.uuid4())
    payload: dict[str, Any] = {
        "session_id": generated,
        "source": SESSION_POINTER_SOURCE,
        "created_at": datetime.now(UTC).isoformat(),
    }
    conversation = _usable_session_id(conversation_id)
    if conversation:
        payload["conversation_id"] = conversation
    try:
        pointer = session_pointer_path(project_dir)
        pointer.parent.mkdir(parents=True, exist_ok=True)
        pointer.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    except (OSError, ValueError, RuntimeError) as exc:
        return generated, type(exc).__name__
    return generated, ""


def resolve_session_lifecycle(
    project_dir: str | Path,
    *,
    explicit: str | None = None,
    rotate: bool = False,
    conversation_id: str | None = None,
) -> tuple[str, str]:
    """ONE lifecycle id for open, compile and close, plus its persistence status.

    Order: a real id from :func:`resolve_session_id` (explicit →
    ``CURSOR_SESSION_ID`` → hook payload ``session_id``) is returned unchanged.
    Otherwise — a conversation-only SessionStart payload, or none at all — the
    id is generated here and persisted under ``.l9/memory/session.json`` so
    every later caller in the session resolves the same value.

    ``rotate=True`` is SessionStart's mode: it is the only hook that knows a
    new session began, so it never reuses the pointer a previous session left
    behind (a shared ``default`` open rotated nothing and hid every close
    gap — audit P573-F2). Later callers keep ``rotate=False`` and reuse.

    Never raises; see :func:`create_session_id` for the persistence status.
    """
    found = resolve_session_id(explicit=explicit)
    if found != "default":
        return found, ""
    if not rotate:
        persisted = persisted_session_id(project_dir)
        if persisted:
            return persisted, ""
    return create_session_id(project_dir, conversation_id=conversation_id)


def resolve_or_create_session_id(
    project_dir: str | Path,
    *,
    explicit: str | None = None,
    rotate: bool = False,
    conversation_id: str | None = None,
) -> str:
    """The session id from :func:`resolve_session_lifecycle`, status dropped."""
    session_id, _error = resolve_session_lifecycle(
        project_dir, explicit=explicit, rotate=rotate, conversation_id=conversation_id
    )
    return session_id


def re_safe(session_id: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)[:120]


def _memory_dir(project_dir: Path) -> str:
    root_r = os.path.realpath(str(Path(project_dir).expanduser()))
    mem_r = os.path.realpath(os.path.join(root_r, ".l9", "memory"))
    if os.path.commonpath([root_r, mem_r]) != root_r:
        raise ValueError("memory directory escapes project root")
    return mem_r


def _bounded_child(parent_r: str, name: str) -> str:
    path_r = os.path.realpath(os.path.join(parent_r, name))
    if os.path.commonpath([parent_r, path_r]) != parent_r:
        raise ValueError("path escapes memory directory")
    return path_r


def opens_dir(project_dir: Path) -> str:
    return _bounded_child(_memory_dir(project_dir), "opens")


def closes_dir(project_dir: Path) -> str:
    return _bounded_child(_memory_dir(project_dir), "closes")


def shadow_dir(project_dir: Path) -> str:
    """Discrepancy receipts from the migration-only legacy shadow read (plan §11)."""

    return _bounded_child(_memory_dir(project_dir), "shadow")


def last_opened_path(project_dir: Path) -> str:
    return _bounded_child(_memory_dir(project_dir), "last_opened.json")


def previous_opened_path(project_dir: Path) -> str:
    return _bounded_child(_memory_dir(project_dir), "previous_opened.json")


def receipt_path(project_dir: Path, session_id: str) -> str:
    safe = re_safe(session_id)
    if not _SAFE_NAME.match(safe):
        raise ValueError("invalid session_id for receipt path")
    closes_r = closes_dir(project_dir)
    path_r = os.path.realpath(os.path.join(closes_r, f"{safe}.json"))
    if os.path.commonpath([closes_r, path_r]) != closes_r:
        raise ValueError("receipt path escapes closes directory")
    return path_r


def _write_json(path_r: str, payload: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path_r), exist_ok=True)
    with open(path_r, "w", encoding="utf-8") as handle:  # NOSONAR python:S2083
        handle.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def _read_json(path_r: str) -> dict[str, Any] | None:
    if not os.path.isfile(path_r):
        return None
    try:
        with open(path_r, encoding="utf-8") as handle:  # NOSONAR python:S2083
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def write_open_latch(
    project_dir: Path,
    session_id: str,
    *,
    background: bool = False,
) -> dict[str, Any]:
    """Record this session open. Background must not rotate last_opened."""
    session_id = resolve_session_id(explicit=session_id)
    opened = {
        "session_id": session_id,
        "opened_at": datetime.now(UTC).isoformat(),
        "background": bool(background),
    }
    opens_r = opens_dir(project_dir)
    os.makedirs(opens_r, exist_ok=True)
    open_file = os.path.realpath(os.path.join(opens_r, f"{re_safe(session_id)}.json"))
    if os.path.commonpath([opens_r, open_file]) != opens_r:
        raise ValueError("open latch escapes opens directory")
    _write_json(open_file, opened)
    if background:
        return {"opened": opened, "rotated": False, "previous": read_previous_opened(project_dir)}
    prev = read_last_opened(project_dir)
    if prev and str(prev.get("session_id") or "") not in {"", session_id}:
        _write_json(previous_opened_path(project_dir), prev)
    _write_json(last_opened_path(project_dir), opened)
    return {
        "opened": opened,
        "rotated": bool(prev and prev.get("session_id") != session_id),
        "previous": read_previous_opened(project_dir),
    }


def read_last_opened(project_dir: Path) -> dict[str, Any] | None:
    try:
        return _read_json(last_opened_path(project_dir))
    except ValueError:
        return None


def read_previous_opened(project_dir: Path) -> dict[str, Any] | None:
    try:
        return _read_json(previous_opened_path(project_dir))
    except ValueError:
        return None


def load_close_receipt(project_dir: Path, session_id: str) -> dict[str, Any] | None:
    try:
        return _read_json(receipt_path(project_dir, session_id))
    except ValueError:
        return None


def receipt_is_successful_close(receipt: dict[str, Any] | None) -> bool:
    """True when the canonical close committed (legacy: provider writes landed)."""
    if not receipt:
        return False
    status = str(receipt.get("status") or "")
    if status == STATUS_CLOSED_CANONICALLY:
        return bool(receipt.get("canonical_operation_id"))
    write_count = int(receipt.get("write_count") or 0)
    if write_count <= 0:
        return False
    if status == "closed":
        return True
    if status == "closed_enqueue_failed" and receipt.get("phase_a") is True:
        return True
    return False


def receipt_is_close_gap(receipt: dict[str, Any] | None) -> bool:
    if receipt is None:
        return True
    if receipt_is_successful_close(receipt):
        return False
    if int(receipt.get("write_count") or 0) <= 0:
        return True
    return str(receipt.get("status") or "") in SKIP_OR_FAIL_STATUSES


def prior_session_id(project_dir: Path, current_session_id: str) -> str | None:
    """Previous foreground session, not the one SessionStart just opened."""
    prev = read_previous_opened(project_dir)
    sid = str((prev or {}).get("session_id") or "").strip()
    if not sid or sid == current_session_id:
        return None
    if (prev or {}).get("background") is True:
        return None
    return sid


def close_gap_reason(project_dir: Path, current_session_id: str) -> str:
    """Empty string when there is no receipt close-gap."""
    prior = prior_session_id(project_dir, current_session_id)
    if not prior:
        return ""
    receipt = load_close_receipt(project_dir, prior)
    if receipt is None:
        return f"prior session {prior} has no close receipt"
    if receipt_is_close_gap(receipt):
        status = receipt.get("status") or "unknown"
        count = receipt.get("write_count")
        return f"prior session {prior} receipt status={status} write_count={count}"
    return ""


def write_receipt(project_dir: Path, session_id: str, payload: dict[str, Any]) -> None:
    """Persist a close receipt with taint-safe scalars only."""
    path_r = receipt_path(project_dir, session_id)
    status = payload.get("status")
    status_out = status if status in RECEIPT_STATUSES else "close_failed"
    enqueue_ok = payload.get("enqueue_ok")
    safe: dict[str, Any] = {
        "status": status_out,
        "session_id": str(session_id),
        "head_hash": str(payload.get("head_hash") or ""),
        "phase_a": bool(payload.get("phase_a") is True),
        "enqueue_ok": True if enqueue_ok is True else (False if enqueue_ok is False else None),
        "enqueue_error_present": bool(payload.get("enqueue_error")),
        "write_count": int(payload.get("write_count") or 0),
        "closed_at": str(payload.get("closed_at") or datetime.now(UTC).isoformat())[:64],
        "attempt_timestamp": str(payload.get("attempt_timestamp") or "")[:64],
        "retry_count": int(payload.get("retry_count") or 0),
        "authority": "none",
    }
    for key in OBLIGATION_FIELDS:
        value = payload.get(key)
        safe[key] = None if value is None else str(value)[:200]
    for key, cap in CLOSE_REQUEST_FIELDS.items():
        value = payload.get(key)
        safe[key] = None if value is None else str(value)[:cap]
    _write_json(path_r, safe)


def record_skip_receipt(
    project_dir: Path,
    session_id: str,
    status: str,
    *,
    write_count: int = 0,
) -> dict[str, Any]:
    """Always-write skip/fail receipt when the project dir is known."""
    if status not in RECEIPT_STATUSES:
        status = "close_failed"
    payload = {
        "status": status,
        "session_id": session_id,
        "write_count": write_count,
        "phase_a": False,
        "closed_at": datetime.now(UTC).isoformat(),
    }
    write_receipt(project_dir, session_id, payload)
    return payload

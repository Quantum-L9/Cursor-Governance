"""Session open/close latches. Not resume SSOT — Graphiti remains SSOT (ADR-0028)."""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$")

RECEIPT_STATUSES = frozenset(
    {
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
        "close_failed",
        "skipped_no_project",
        "skipped_disabled",
        "skipped_cli_missing",
    }
)


def resolve_session_id(*, explicit: str | None = None) -> str:
    """Single session id for open, close, compile, and fallback.

    Order: explicit → CURSOR_CONVERSATION_ID → CURSOR_SESSION_ID → ``default``.
    ``default`` is last resort (shared-id collision risk).
    """
    for candidate in (
        explicit,
        os.environ.get("CURSOR_CONVERSATION_ID"),
        os.environ.get("CURSOR_SESSION_ID"),
    ):
        if candidate and str(candidate).strip():
            return str(candidate).strip()[:120]
    return "default"


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
    """True when Graphiti writes landed (S3 enqueue fail is not a close-gap)."""
    if not receipt:
        return False
    status = str(receipt.get("status") or "")
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
    safe = {
        "status": status_out,
        "session_id": str(session_id),
        "head_hash": str(payload.get("head_hash") or ""),
        "phase_a": bool(payload.get("phase_a") is True),
        "phase_b": bool(payload.get("phase_b") is True),
        "enqueue_ok": True if enqueue_ok is True else (False if enqueue_ok is False else None),
        "enqueue_error_present": bool(payload.get("enqueue_error")),
        "write_count": int(payload.get("write_count") or 0),
        "closed_at": str(payload.get("closed_at") or datetime.now(UTC).isoformat())[:64],
    }
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
        "phase_b": False,
        "closed_at": datetime.now(UTC).isoformat(),
    }
    write_receipt(project_dir, session_id, payload)
    return payload

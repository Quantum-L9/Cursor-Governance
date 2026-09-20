#!/usr/bin/env python3
"""Bounded Manus lifecycle adapter over the canonical L9 memory control plane.

Manus does not expose Cursor/Claude lifecycle hooks.  This module therefore
binds *explicit*, bearer-protected MCP lifecycle calls to the same shared
SessionStart/SessionEnd authorities used by peer adapters:

* startup calls :func:`ops.memory.hydration.canonical_hydrate` under a
  read-only Manus hook envelope and records non-authoritative session evidence;
* closure calls :func:`ops.graphiti.hydration.close_session` under a narrowly
  bounded Manus close envelope.

It is not an agent-memory proxy.  Ordinary agent reads and writes remain the
package-owned ``l9-graphite-memory`` MCP/CLI lane (ADR-0031/ADR-0033).  In
particular, this wrapper refuses to invoke memory when the signed Manus agent
door is absent rather than silently falling back to a local-operator principal.
"""

from __future__ import annotations

import os
import re
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ops.graphiti.hydration.close_session import close_session
from ops.memory.hydration import (
    CONTINUATION_POLICY_REPOSITORY_FALLBACK,
    CanonicalHydration,
    canonical_hydrate,
)
from ops.memory.session_state import write_session_state

MANUS_AGENT_ID = "manus"
MANUS_USER_ID = "manus_agent"
MANUS_SOURCE = "manus"
START_SURFACE = "manus-session-start"
END_SURFACE = "manus-session-end"
MAX_TASK_CHARS = 1_000
MAX_SUMMARY_CHARS = 4_000
MAX_NEXT_ACTION_CHARS = 1_000
MAX_CONTEXT_CHARS = 12_000
_SESSION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$")
_AGENT_DOOR_ENV = (
    "L9_MEMORY_AGENTS_DOOR_SECRET",
    "L9_MEMORY_AGENT_ASSERTION",
    "L9_MEMORY_AGENT_SIGNING_KEYS_JSON",
    "L9_MEMORY_AGENT_GRANTS_JSON",
)


class MemoryAccessError(RuntimeError):
    """The signed Manus agent door is not safely available to this process."""


def _required_text(value: Any, *, name: str, limit: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must not be empty")
    if len(normalized) > limit:
        raise ValueError(f"{name} exceeds {limit} characters")
    return normalized


def validate_session_id(value: Any) -> str:
    session_id = _required_text(value, name="session_id", limit=120)
    if not _SESSION_ID.fullmatch(session_id):
        raise ValueError("session_id may contain only letters, numbers, dot, underscore, and dash")
    return session_id


def signed_agent_door_status(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Return names-only signed-door readiness; values never leave the process."""

    values = os.environ if env is None else env
    identity = str(values.get("L9_MEMORY_AGENT_ID") or "").strip()
    user_id = str(values.get("USER_ID") or "").strip()
    source = str(values.get("L9_MEMORY_SOURCE") or "").strip()
    missing = [name for name in _AGENT_DOOR_ENV if not str(values.get(name) or "").strip()]
    errors: list[str] = []
    if identity != MANUS_AGENT_ID:
        errors.append(f"L9_MEMORY_AGENT_ID must be {MANUS_AGENT_ID!r}")
    if user_id != MANUS_USER_ID:
        errors.append(f"USER_ID must be {MANUS_USER_ID!r}")
    if source != MANUS_SOURCE:
        errors.append(f"L9_MEMORY_SOURCE must be {MANUS_SOURCE!r}")
    if str(values.get("L9_MEMORY_HUMAN_DOOR_SECRET") or "").strip():
        errors.append("human memory door must never be present in a Manus agent process")
    if missing:
        errors.append("signed agent door is incomplete")
    return {
        "status": "ready" if not errors else "unavailable",
        "missing": missing,
        "errors": errors,
        "agent_id": identity or None,
    }


def require_signed_agent_door(env: Mapping[str, str] | None = None) -> None:
    """Fail closed before a lifecycle call could use a local-operator fallback."""

    status = signed_agent_door_status(env)
    if status["status"] != "ready":
        details = list(status["errors"])
        missing = list(status["missing"])
        if missing:
            details.append("missing " + ", ".join(missing))
        raise MemoryAccessError("; ".join(details))


def _context(hydration: CanonicalHydration) -> str:
    """Return bounded model context without exposing raw operation receipts."""

    text = "\n\n".join(content for _kind, content in hydration.context_sections if content)
    if len(text) <= MAX_CONTEXT_CHARS:
        return text
    return text[:MAX_CONTEXT_CHARS] + "\n… context truncated by the Manus lifecycle adapter"


def _hydration_result(
    session_id: str, hydration: CanonicalHydration, state_path: Path
) -> dict[str, Any]:
    """Produce a model-facing result, retaining evidence but not raw receipts."""

    context = hydration.namespace_context
    return {
        "status": hydration.status,
        "session_id": session_id,
        "transport": "memory-control-plane/v1",
        "surface": START_SURFACE,
        "session_state_path": str(state_path),
        "namespace": {
            "repository_identity": context.repository_identity,
            "write_namespace_hint": context.write_namespace_hint,
            "requested_namespaces": list(hydration.requested_namespaces),
        },
        "record_ids": list(hydration.record_ids),
        "continuation": hydration.continuation.as_dict() if hydration.continuation else None,
        "continuation_policy": hydration.continuation_policy,
        "fault_class": hydration.fault_class,
        "context": _context(hydration),
        "context_truncated": sum(len(value) for _kind, value in hydration.context_sections)
        > MAX_CONTEXT_CHARS,
        "warnings_count": len(hydration.warnings),
    }


def start_session(
    *,
    workspace: Path,
    task: Any,
    session_id: Any,
) -> dict[str, Any]:
    """Run canonical hydration and persist only local session evidence."""

    require_signed_agent_door()
    resolved_task = _required_text(task, name="task", limit=MAX_TASK_CHARS)
    resolved_session_id = validate_session_id(session_id)
    hydration = canonical_hydrate(
        workspace,
        task=resolved_task,
        session_id=resolved_session_id,
        token_budget=1_200,
        max_records=40,
        continuation_policy=CONTINUATION_POLICY_REPOSITORY_FALLBACK,
        surface=START_SURFACE,
    )
    state_path = write_session_state(resolved_session_id, hydration)
    return _hydration_result(resolved_session_id, hydration, state_path)


def _runtime_dir() -> Path | None:
    raw = os.environ.get("XDG_RUNTIME_DIR", "").strip()
    if not raw:
        return None
    candidate = Path(raw).expanduser()
    return candidate if candidate.is_dir() and os.access(candidate, os.W_OK) else None


def _close_transcript(*, summary: str, next_action: str) -> Path:
    """Build a short redaction-bound close source and return its 0600 path."""

    descriptor, raw_path = tempfile.mkstemp(
        prefix="l9-manus-close-",
        suffix=".txt",
        dir=_runtime_dir(),
        text=True,
    )
    path = Path(raw_path)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(f"assistant: {summary}\nuser: {next_action}\n")
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path


def _close_result(report: Mapping[str, Any]) -> dict[str, Any]:
    """Return lifecycle evidence without replaying close summaries or warnings."""

    writes = report.get("writes") if isinstance(report.get("writes"), list) else []
    safe_writes = [
        {
            "kind": item.get("kind"),
            "status": item.get("status"),
            "written": bool(item.get("written")),
            "record_id": item.get("record_id"),
            "receipt_id": item.get("receipt_id"),
        }
        for item in writes
        if isinstance(item, dict)
    ]
    continuation = (
        report.get("continuation") if isinstance(report.get("continuation"), dict) else None
    )
    close = report.get("close") if isinstance(report.get("close"), dict) else None
    return {
        "status": report.get("status"),
        "session_id": report.get("session_id"),
        "transport": "memory-control-plane/v1",
        "surface": END_SURFACE,
        "namespace": report.get("group_id"),
        "phase_a": bool(report.get("phase_a")),
        "continuation": continuation,
        "close": {
            key: close.get(key)
            for key in (
                "status",
                "receipt_id",
                "record_id",
                "replayed",
                "replay_payload_matched",
                "idempotency_key",
            )
        }
        if close
        else None,
        "writes": safe_writes,
        "warnings_count": len(report.get("warnings") or []),
        "elapsed_s": report.get("elapsed_s"),
    }


def close_session_from_manus(
    *,
    workspace: Path,
    session_id: Any,
    summary: Any,
    next_action: Any,
) -> dict[str, Any]:
    """Close one explicitly started Manus session through canonical SessionEnd."""

    require_signed_agent_door()
    resolved_session_id = validate_session_id(session_id)
    resolved_summary = _required_text(summary, name="summary", limit=MAX_SUMMARY_CHARS)
    resolved_next_action = _required_text(
        next_action, name="next_action", limit=MAX_NEXT_ACTION_CHARS
    )
    transcript = _close_transcript(summary=resolved_summary, next_action=resolved_next_action)
    try:
        report = close_session(
            project_dir=workspace,
            session_id=resolved_session_id,
            reason="manus-session-end",
            transcript_path=str(transcript),
            agent_id=MANUS_AGENT_ID,
            is_background_agent=False,
            dry_run=False,
            surface=END_SURFACE,
        )
    finally:
        transcript.unlink(missing_ok=True)
    return _close_result(report)


__all__ = [
    "END_SURFACE",
    "MAX_CONTEXT_CHARS",
    "MANUS_AGENT_ID",
    "MemoryAccessError",
    "START_SURFACE",
    "close_session_from_manus",
    "require_signed_agent_door",
    "signed_agent_door_status",
    "start_session",
    "validate_session_id",
]

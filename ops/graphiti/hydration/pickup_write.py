"""Graphiti PICKUP writes for hook fallback and /end-session repair (ADR-0028)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ops.graphiti.hydration.session_latches import (
    load_close_receipt,
    receipt_is_successful_close,
    resolve_session_id,
    write_receipt,
)


def fallback_pickup_write(
    *,
    project_dir: str | Path,
    session_id: str | None = None,
    reason: str = "close_fallback",
    transcript_path: str | None = None,
    agent_id: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """One Graphiti pickup_context write after close_session write_count=0."""
    from group_resolver import resolve_group_id

    from ops.graphiti.hydration.close_session import _heuristic_pickup, _write_kind
    from ops.graphiti.hydration.identity import resolve_write_identity
    from ops.graphiti.hydration.transcript import load_transcript_excerpt

    project = Path(project_dir).expanduser().resolve()
    sid = resolve_session_id(explicit=session_id)
    report: dict[str, Any] = {
        "status": "close_failed",
        "session_id": sid,
        "written": False,
        "write_count": 0,
        "warnings": [],
    }
    identity = resolve_write_identity(
        explicit_agent_id=agent_id,
        surface="claude-code" if (agent_id or "").startswith("claude") else "cursor",
    )
    resolved = resolve_group_id(project)
    group_id = str(resolved.get("group_id") or "")
    if not group_id or resolved.get("readonly"):
        report["warnings"].append("fallback write blocked: group unresolved/readonly")
        if not dry_run:
            write_receipt(project, sid, {**report, "phase_a": False})
        return report

    transcript, _src = load_transcript_excerpt(
        transcript_path=transcript_path,
        conversation_id=sid,
    )
    pickup = _heuristic_pickup(
        project_dir=project,
        session_id=sid,
        transcript=transcript,
        reason=reason,
    )
    search_line = (
        f"PICKUP|objective={pickup['active_objective']}|next={pickup['next_action']}|"
        f"agent={identity['agent_id']}|session={sid}"
    )
    body = search_line
    try:
        result = _write_kind(
            body,
            kind="pickup_context",
            group_id=group_id,
            agent_id=identity["agent_id"],
            user_id=identity["user_id"],
            dry_run=dry_run,
        )
        written = bool(result.get("written") or result.get("dry_run"))
        report["written"] = written
        report["write_count"] = 1 if written else 0
        report["status"] = "closed" if written else "close_failed"
        report["phase_a"] = written
        report["result"] = result
    except Exception as exc:  # noqa: BLE001
        report["warnings"].append(f"fallback write failed: {type(exc).__name__}")
        report["status"] = "close_failed"
    if not dry_run:
        write_receipt(project, sid, report)
    return report


def repair_pickup_write(
    *,
    project_dir: str | Path,
    session_id: str | None = None,
    objective: str,
    next_action: str,
    files: str = "",
    blocker: str = "",
    agent_id: str | None = None,
    supersede: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Primary /end-session path: client write, skip if already closed."""
    from group_resolver import resolve_group_id

    from ops.graphiti.hydration.close_session import _write_kind
    from ops.graphiti.hydration.identity import resolve_write_identity

    project = Path(project_dir).expanduser().resolve()
    sid = resolve_session_id(explicit=session_id)
    existing = load_close_receipt(project, sid)
    if receipt_is_successful_close(existing) and not supersede:
        return {
            "status": "skipped_already_closed",
            "session_id": sid,
            "written": False,
            "write_count": int((existing or {}).get("write_count") or 0),
        }

    identity = resolve_write_identity(
        explicit_agent_id=agent_id,
        surface="claude-code" if (agent_id or "").startswith("claude") else "cursor",
    )
    resolved = resolve_group_id(project)
    group_id = str(resolved.get("group_id") or "")
    if not group_id or resolved.get("readonly"):
        return {"status": "close_failed", "session_id": sid, "written": False, "write_count": 0}

    line = (
        f"PICKUP|date={datetime.now(UTC).date().isoformat()}|task={objective}|"
        f"files={files}|next={next_action}|blocker={blocker}|session={sid}"
    )
    result = _write_kind(
        line,
        kind="pickup_context",
        group_id=group_id,
        agent_id=identity["agent_id"],
        user_id=identity["user_id"],
        dry_run=dry_run,
    )
    written = bool(result.get("written") or result.get("dry_run"))
    report = {
        "status": "closed" if written else "close_failed",
        "session_id": sid,
        "written": written,
        "write_count": 1 if written else 0,
        "phase_a": written,
        "closed_at": datetime.now(UTC).isoformat(),
    }
    if not dry_run:
        write_receipt(project, sid, report)
    return report

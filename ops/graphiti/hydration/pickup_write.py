"""Canonical close retry and forced ``/end-session`` repair (ADR-0028, stage C6).

Both paths converge on the same memory boundary as the hook close: a
continuation capsule admitted as a governed candidate, then ``memory.close``
with the idempotency key recorded in the local close obligation. A retry of
an interrupted close therefore resolves to exactly one logical close
(adversarial tests G and H); a forced repair supersedes nothing by hand and
never writes a provider.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ops.graphiti.hydration.session_latches import (
    STATUS_CLOSE_INCOMPLETE,
    STATUS_CLOSED_CANONICALLY,
    load_close_receipt,
    receipt_is_successful_close,
    resolve_session_id,
    write_receipt,
)
from ops.memory.namespace_context import repository_state_digest, resolve_namespace_context


def _finish(
    project: Path,
    session_id: str,
    *,
    status: str,
    dry_run: bool,
    write_count: int,
    obligation: dict[str, Any],
    **fields: Any,
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    payload = {
        "status": status,
        "session_id": session_id,
        "phase_a": write_count > 0,
        "write_count": write_count,
        "closed_at": now,
        "attempt_timestamp": now,
        "retry_count": int(obligation.get("retry_count") or 0) + 1,
        "canonical_namespace_requested": obligation.get("canonical_namespace_requested"),
        "close_idempotency_key": obligation.get("close_idempotency_key"),
        "payload_digest": obligation.get("payload_digest"),
        "continuation_status": obligation.get("continuation_status"),
        "continuation_reference": obligation.get("continuation_reference"),
        "close_summary": obligation.get("close_summary"),
        "close_capsule_digest": obligation.get("close_capsule_digest"),
        "close_session_id": obligation.get("close_session_id"),
        **fields,
    }
    if not dry_run:
        write_receipt(project, session_id, payload)
    report = dict(payload)
    report["written"] = write_count > 0
    return report


def retry_close(
    *,
    project_dir: str | Path,
    session_id: str | None = None,
    reason: str = "close_retry",
    transcript_path: str | None = None,
    agent_id: str | None = None,
    dry_run: bool = False,
    client: Any = None,
) -> dict[str, Any]:
    """Discharge a ``close_incomplete`` obligation with the same idempotency key.

    Replays the canonical close the interrupted attempt started — the *exact*
    close request the obligation recorded (summary, capsule digest, session),
    under the recorded key — so memory returns the close it already committed
    (``replayed``, with ``replay_payload_matched`` proving it was the same
    request) or commits it now (audit P2-01). An obligation that predates the
    recorded close request cannot be replayed exactly and gets a full
    canonical close instead; with no prior obligation this is a full
    canonical close too.
    """
    from ops.graphiti.hydration.close_session import close_session, memory_client

    project = Path(project_dir).expanduser().resolve()
    sid = resolve_session_id(explicit=session_id)
    obligation = load_close_receipt(project, sid) or {}
    if receipt_is_successful_close(obligation):
        return {
            "status": "skipped_already_closed",
            "session_id": sid,
            "written": False,
            "write_count": int(obligation.get("write_count") or 0),
        }
    key = obligation.get("close_idempotency_key")
    namespace = obligation.get("canonical_namespace_requested")
    stored_summary = obligation.get("close_summary")
    if key and namespace and obligation.get("continuation_reference") and stored_summary:
        # The capsule was admitted and the exact close request is on record;
        # only the close is owed. Same key + same payload -> one logical close.
        client = client or memory_client(sid)
        closed = client.close(
            workspace=resolve_namespace_context(project).git_root or str(project),
            namespace=str(namespace),
            summary=str(stored_summary),
            session_id=str(obligation.get("close_session_id") or sid),
            capsule_digest=obligation.get("close_capsule_digest")
            or obligation.get("payload_digest"),
            idempotency_key=str(key),
            dry_run=dry_run,
        )
        receipt = closed.receipt
        committed = closed.ok and receipt is not None and receipt.committed
        drifted = bool(getattr(receipt, "payload_drifted", False))
        report = _finish(
            project,
            sid,
            status=STATUS_CLOSED_CANONICALLY if committed else STATUS_CLOSE_INCOMPLETE,
            dry_run=dry_run,
            write_count=1 if committed else 0,
            obligation=obligation,
            canonical_operation_id=getattr(receipt, "receipt_id", None),
            failure_class=None if committed else closed.status.value,
            last_error_code=None if committed else closed.status.value,
            replayed=bool(getattr(receipt, "replayed", False)),
            replay_payload_matched=getattr(receipt, "replay_payload_matched", None),
        )
        report["warnings"] = list(getattr(receipt, "warnings", ()) or ())
        if drifted:
            report["warnings"].append(
                "close replay payload drift: the stored close differs from the replayed request"
            )
        return report
    report = close_session(
        project_dir=project,
        session_id=sid,
        reason=reason,
        transcript_path=transcript_path,
        agent_id=agent_id,
        dry_run=dry_run,
        client=client,
    )
    receipt = report.get("receipt") or {}
    return {
        "status": report.get("status"),
        "session_id": sid,
        "written": bool(receipt.get("write_count")),
        "write_count": int(receipt.get("write_count") or 0),
        "warnings": report.get("warnings", []),
    }


def repair_close(
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
    client: Any = None,
) -> dict[str, Any]:
    """Forced ``/end-session`` parity: explicit capsule -> candidate -> memory.close.

    Skips when the session already closed canonically unless ``supersede``;
    a superseding repair admits a newer capsule (hydrate prefers the newest)
    and closes under a distinct idempotency key naming the repair.
    """
    from ops.graphiti.hydration.close_session import build_capsule, memory_client
    from ops.graphiti.hydration.identity import resolve_write_identity

    project = Path(project_dir).expanduser().resolve()
    sid = resolve_session_id(explicit=session_id)
    existing = load_close_receipt(project, sid) or {}
    if receipt_is_successful_close(existing) and not supersede:
        return {
            "status": "skipped_already_closed",
            "session_id": sid,
            "written": False,
            "write_count": int(existing.get("write_count") or 0),
        }
    identity = resolve_write_identity(
        explicit_agent_id=agent_id,
        surface="claude-code" if (agent_id or "").startswith("claude") else "cursor",
    )
    context = resolve_namespace_context(project)
    namespace = context.write_namespace_hint
    if not namespace:
        return {
            "status": "close_failed",
            "session_id": sid,
            "written": False,
            "write_count": 0,
            "warnings": list(context.warnings),
        }
    head = repository_state_digest(project)
    pickup = {
        "active_objective": objective,
        "next_action": next_action,
        "active_files": [f.strip() for f in files.split(",") if f.strip()],
        "blockers": [blocker] if blocker.strip() else [],
    }
    capsule = build_capsule(
        session_id=sid,
        repository_identity=context.repository_identity or namespace,
        head=head,
        pickup=pickup,
    )
    client = client or memory_client(sid)
    workspace = context.git_root or str(project)
    admitted = client.ingest_candidate(
        capsule.to_governed_candidate(
            namespace=namespace, source_sha=head or "0" * 40, agent_id=identity["agent_id"]
        ),
        workspace=workspace,
    )
    continuation_status = (
        admitted.receipt.status if admitted.receipt is not None else admitted.status.value.lower()
    )
    continuation_reference = admitted.receipt.record_id if admitted.receipt is not None else None
    key = str(existing.get("close_idempotency_key") or f"cursor-close:{namespace}:{sid}:repair")
    if supersede:
        key = f"{key}:repair:{capsule.digest()[:12]}"
    closed = client.close(
        workspace=workspace,
        namespace=namespace,
        summary=f"session {sid} end-session repair: {objective} | next: {next_action}",
        session_id=sid,
        capsule_digest=capsule.digest(),
        idempotency_key=key,
        dry_run=dry_run,
    )
    receipt = closed.receipt
    committed = closed.ok and receipt is not None and receipt.committed
    obligation = {
        **existing,
        "canonical_namespace_requested": namespace,
        "close_idempotency_key": key,
        "payload_digest": capsule.digest(),
        "continuation_status": continuation_status,
        "continuation_reference": continuation_reference,
    }
    report = _finish(
        project,
        sid,
        status=STATUS_CLOSED_CANONICALLY if committed else STATUS_CLOSE_INCOMPLETE,
        dry_run=dry_run,
        write_count=(1 if admitted.ok else 0) + (1 if committed else 0),
        obligation=obligation,
        canonical_operation_id=getattr(receipt, "receipt_id", None),
        failure_class=None if committed else closed.status.value,
        last_error_code=None if committed else closed.status.value,
    )
    report["continuation"] = {"status": continuation_status, "record_id": continuation_reference}
    return report


# Compatibility names for the hook and the l9-end-session skill (retired at C11).
fallback_pickup_write = retry_close
repair_pickup_write = repair_close

__all__ = ["fallback_pickup_write", "repair_close", "repair_pickup_write", "retry_close"]

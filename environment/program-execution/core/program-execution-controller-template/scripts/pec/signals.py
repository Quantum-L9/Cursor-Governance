"""Dry-run distill enqueue + optional OutcomePublisher projection."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .common import digest_object

# Receipt fields a distill job may carry verbatim. Everything else is
# represented by the receipt digest, so a job never becomes a second copy of
# controller state and never widens what leaves the workspace.
_SCALAR_RECEIPT_FIELDS = ("task_id", "status", "attempt", "evidence_id")


def distill_queue_dir(workspace: Path) -> Path:
    return workspace / "runtime" / "distill_queue"


def enqueue_dry_run(
    workspace: Path,
    *,
    event: str,
    receipt: dict[str, Any],
) -> dict[str, Any]:
    """Write one observable distill job. Never reports S3 acceptance."""

    queue = distill_queue_dir(workspace)
    queue.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)
    subject = {
        key: receipt[key]
        for key in _SCALAR_RECEIPT_FIELDS
        if isinstance(receipt.get(key), str | int)
    }
    job = {
        "schema": "program-execution-controller.distill-job.v1",
        "event": event,
        "enqueued_at": now.replace(microsecond=0).isoformat(),
        "subject": subject,
        "receipt_digest": digest_object(receipt),
        "receipt_keys": sorted(receipt),
        "status": "enqueued",
        "accepted": False,
    }
    # Microsecond stamp: two same-event signals inside one second are ordinary
    # (record-attempt then verify on a fast task) and a second-resolution name
    # made the later one silently overwrite the earlier.
    stamp = now.strftime("%Y%m%dT%H%M%S.%fZ")
    path = queue / f"{stamp}-{event}.json"
    path.write_text(json.dumps(job, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"path": str(path), "status": "enqueued", "accepted": False}


def list_dry_run_queue(workspace: Path) -> list[Path]:
    queue = distill_queue_dir(workspace)
    if not queue.is_dir():
        return []
    return sorted(queue.glob("*.json"))


def publish_controller_event(
    workspace: Path,
    *,
    event: str,
    receipt: dict[str, Any],
) -> dict[str, Any]:
    """Enqueue locally, best-effort. Never fails the caller's operation.

    Every call site (record-attempt, verify, evaluate-gate, export-handoff)
    invokes this *after* the controller has transitioned state and appended its
    ledger event. A queue write that raises -- a full disk, a read-only mount, a
    receipt the digest cannot canonicalise -- would surface as a failed
    controller operation that in fact succeeded. Observability is not authority.
    """

    try:
        queued = enqueue_dry_run(workspace, event=event, receipt=receipt)
    except Exception as exc:  # noqa: BLE001 - signal must not fail the operation
        return {
            "event": event,
            "distill": {"status": "failed", "accepted": False, "error": str(exc)},
        }
    return {"event": event, "distill": queued}

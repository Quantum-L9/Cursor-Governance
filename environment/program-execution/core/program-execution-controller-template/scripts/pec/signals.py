"""Dry-run distill enqueue + optional OutcomePublisher projection."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


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
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    job = {
        "schema": "program-execution-controller.distill-job.v1",
        "event": event,
        "enqueued_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "receipt_keys": sorted(receipt),
        "status": "enqueued",
        "accepted": False,
    }
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
    """Always enqueue locally. OutcomePublisher is best-effort projection."""

    queued = enqueue_dry_run(workspace, event=event, receipt=receipt)
    return {"event": event, "distill": queued}

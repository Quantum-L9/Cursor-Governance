"""
File-based task queue for local Cursor ↔ Agent UI Control.

No VPS, WebSocket, or reverse tunnel required.

Queue layout:
  ~/.l9/mac_tasks/pending/<task_id>.json
  ~/.l9/mac_tasks/completed/<task_id>.json
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

QUEUE_BASE = Path.home() / ".l9" / "mac_tasks"
PENDING_DIR = QUEUE_BASE / "pending"
COMPLETED_DIR = QUEUE_BASE / "completed"


def enqueue_task(task: dict[str, Any]) -> str:
    """Write task to pending queue. Returns task_id."""
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    task_id = task.get("task_id") or f"task-{uuid4().hex[:12]}"
    task = dict(task)
    task["task_id"] = task_id
    (PENDING_DIR / f"{task_id}.json").write_text(json.dumps(task, indent=2) + "\n")
    return task_id


def get_next_task() -> dict[str, Any] | None:
    """Runner: pop oldest pending task."""
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(PENDING_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime)
    if not files:
        return None
    task_file = files[0]
    task = json.loads(task_file.read_text())
    task_file.unlink()
    return task


def mark_task_completed(task_id: str, result: dict[str, Any] | None = None) -> None:
    """Runner: persist result for Cursor to poll. Always stores a result object."""
    COMPLETED_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "task_id": task_id,
        "result": result if result is not None else {"status": "done"},
        "completed_at": time.time(),
    }
    (COMPLETED_DIR / f"{task_id}.json").write_text(json.dumps(payload, indent=2) + "\n")


def poll_for_result(
    task_id: str, timeout_seconds: int = 300, interval: float = 1.0
) -> dict[str, Any] | None:
    """Cursor/console: wait until runner writes completed/<task_id>.json."""
    result_file = COMPLETED_DIR / f"{task_id}.json"
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if result_file.exists():
            return json.loads(result_file.read_text())
        time.sleep(interval)
    return None

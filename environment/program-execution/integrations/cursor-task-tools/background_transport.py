from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from peer_execution.runtime_store import write_json_atomic


class BackgroundTransport:
    def __init__(self, runtime_root: str | Path) -> None:
        self.root = Path(runtime_root).resolve() / "cursor-tasks" / "background"
        self.root.mkdir(parents=True, exist_ok=True)

    def dispatch(self, dispatch_id: str, task: dict[str, Any]) -> Path:
        path = self.root / f"{dispatch_id}.request.json"
        # The host polls this file from another process: write-then-rename.
        write_json_atomic(path, task)
        return path

    def status(self, dispatch_id: str) -> str:
        if (self.root / f"{dispatch_id}.result.json").is_file():
            return "PASS"
        if (self.root / f"{dispatch_id}.cancelled.json").is_file():
            return "CANCELLED"
        return "RUNNING"

    def cancel(self, dispatch_id: str) -> bool:
        handle = self.root / f"{dispatch_id}.handle.json"
        if not handle.is_file():
            return False
        marker = self.root / f"{dispatch_id}.cancel.request.json"
        marker.write_text(
            json.dumps({"dispatch_id": dispatch_id, "cancel": True}) + "\n",
            encoding="utf-8",
        )
        return True

    def collect(self, dispatch_id: str) -> dict[str, Any] | None:
        path = self.root / f"{dispatch_id}.result.json"
        if not path.is_file():
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("Cursor result must be an object")
        return value

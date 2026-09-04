from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from peer_execution.runtime_store import write_json_atomic


class ForegroundTransport:
    def __init__(self, runtime_root: str | Path) -> None:
        self.root = Path(runtime_root).resolve() / "cursor-tasks" / "foreground"
        self.root.mkdir(parents=True, exist_ok=True)

    def dispatch(self, dispatch_id: str, task: dict[str, Any]) -> Path:
        path = self.root / f"{dispatch_id}.request.json"
        # The host polls this file from another process: write-then-rename.
        write_json_atomic(path, task)
        return path

    def collect(self, dispatch_id: str) -> dict[str, Any] | None:
        path = self.root / f"{dispatch_id}.result.json"
        if not path.is_file():
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("Cursor result must be an object")
        return value

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


class RuntimeStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, directory: str, identifier: str) -> Path:
        safe = identifier.replace("/", "_").replace("..", "_")
        path = (self.root / directory / f"{safe}.json").resolve()
        if self.root not in path.parents:
            raise ValueError("runtime path escapes runtime root")
        return path

    def _dispatch_path(self, dispatch_id: str) -> Path:
        return self._safe_path("dispatches", dispatch_id)

    def _capability_path(self, adapter_id: str) -> Path:
        return self._safe_path("capabilities", adapter_id)

    @staticmethod
    def _atomic_write(path: Path, value: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            delete=False,
        ) as handle:
            handle.write(payload)
            temporary = Path(handle.name)
        os.replace(temporary, path)

    @staticmethod
    def _load_object(path: Path) -> dict[str, Any]:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("runtime record must be an object")
        return value

    def save(self, dispatch_id: str, value: dict[str, Any]) -> Path:
        path = self._dispatch_path(dispatch_id)
        self._atomic_write(path, value)
        return path

    def load(self, dispatch_id: str) -> dict[str, Any]:
        return self._load_object(self._dispatch_path(dispatch_id))

    def delete(self, dispatch_id: str) -> bool:
        path = self._dispatch_path(dispatch_id)
        if not path.exists():
            return False
        path.unlink()
        return True

    def save_capability(
        self,
        adapter_id: str,
        value: dict[str, Any],
    ) -> Path:
        path = self._capability_path(adapter_id)
        self._atomic_write(path, value)
        return path

    def load_capability(self, adapter_id: str) -> dict[str, Any] | None:
        path = self._capability_path(adapter_id)
        if not path.is_file():
            return None
        return self._load_object(path)

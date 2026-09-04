from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$")


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    """Write JSON so a concurrent or crashed reader never sees a half file.

    Shared by the runtime store and by every host-facing file another process
    polls (Cursor task requests, ChatGPT envelopes, autonomy grant receipts).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            delete=False,
        ) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


class RuntimeStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _identifier(value: str) -> str:
        if not isinstance(value, str) or not _SAFE_IDENTIFIER.fullmatch(value):
            raise ValueError(f"unsafe runtime identifier: {value!r}")
        return value

    def _safe_path(self, directory: str, identifier: str) -> Path:
        safe = self._identifier(identifier)
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
        write_json_atomic(path, value)

    @staticmethod
    def _load_object(path: Path) -> dict[str, Any]:
        if path.is_symlink():
            raise ValueError(f"refusing symlinked runtime record: {path}")
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
        if not path.exists() and not path.is_symlink():
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
        if not path.exists() and not path.is_symlink():
            return None
        return self._load_object(path)

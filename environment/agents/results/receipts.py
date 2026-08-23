from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from environment.agents.runtime_paths import agent_runtime_root

SCHEMA = "l9.result-acceptance-receipt.v1"
_SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]+$")


def _root() -> Path:
    return agent_runtime_root() / "results"


def _safe_id(value: Any) -> str:
    text = str(value or "").strip()
    if not text or not _SAFE_ID.fullmatch(text):
        raise ValueError("result_id contains unsupported characters")
    return text


def acceptance_path(result_id: str) -> Path:
    return _root() / f"{_safe_id(result_id)}.json"


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    try:
        os.chmod(temporary, 0o600)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")


def write_acceptance(body: dict[str, Any]) -> dict[str, Any]:
    result_id = _safe_id(body["result_id"])
    stored = {
        **body,
        "schema": SCHEMA,
        "result_id": result_id,
        "observed_at": body.get("observed_at")
        or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    stored["receipt_digest"] = hashlib.sha256(_canonical(stored)).hexdigest()
    encoded = (
        json.dumps(stored, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    )
    path = acceptance_path(result_id)
    if path.is_file():
        existing = path.read_bytes()
        if existing == encoded:
            return json.loads(existing)
        prior = json.loads(existing)
        if prior.get("result_digest") == stored.get("result_digest") and prior.get(
            "status"
        ) == stored.get("status"):
            return prior
        raise RuntimeError(f"acceptance receipt collision: {path}")
    _atomic_write(path, encoded)
    return stored


def load_acceptance(result_id: str) -> dict[str, Any] | None:
    path = acceptance_path(result_id)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

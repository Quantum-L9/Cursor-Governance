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


def safe_receipt_id(value: Any, *, label: str = "result_id") -> str:
    """One identifier grammar for every receipt path component.

    Receipt files are named after identifiers a host or a subagent supplied;
    anything outside this alphabet (``..``, ``/``, whitespace) would let such
    an identifier escape the receipt root, so it is refused rather than
    written.
    """
    text = str(value or "").strip()
    if not text or not _SAFE_ID.fullmatch(text) or set(text) == {"."}:
        raise ValueError(f"{label} contains unsupported characters")
    return text


def _safe_id(value: Any) -> str:
    return safe_receipt_id(value)


def acceptance_path(result_id: str, assignment_id: str | None = None) -> Path:
    """Acceptance receipts are keyed by ``(assignment_id, result_id)``.

    A result_id is chosen by the producing subagent, so two agents on two
    actions may legitimately pick the same one; only within one assignment is
    a differing body under the same result_id a collision.
    """
    name = f"{_safe_id(result_id)}.json"
    if assignment_id is None:
        return _root() / name
    return _root() / safe_receipt_id(assignment_id, label="assignment_id") / name


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
    path = acceptance_path(result_id, body.get("assignment_id"))
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


def load_acceptance(result_id: str, assignment_id: str | None = None) -> dict[str, Any] | None:
    path = acceptance_path(result_id, assignment_id)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

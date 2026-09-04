from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from environment.agents.runtime_paths import (
    generated_data_evidence_root,
    generated_data_quarantine_root,
    generated_data_receipt_root,
)

SCHEMA = "l9.generated-data-ingress-receipt.v1"
OUTCOMES = {"CAPTURED", "NO_REUSABLE_DATA", "QUARANTINED", "REJECTED", "FAILED"}
PROCESSING_STATUSES = {
    "NOT_STARTED",
    "PENDING",
    "VALIDATED",
    "HARVESTED",
    "CLASSIFIED",
    "ROUTED",
    "PROMOTION_DECIDED",
    "DELIVERY_PENDING",
    "DESTINATION_SUBMITTED",
    "DESTINATION_DEFERRED",
    "DESTINATION_ACCEPTED",
    "DESTINATION_REJECTED",
    "LEARNING_CLOSED",
    "REJECTED",
    "RETRY_WAIT",
    "DEAD_LETTERED",
    "FAILED",
    "UNKNOWN",
}


#: One path segment: no separator, no `.`/`..`, nothing that leaves the
#: receipt directory. A sha256 hex digest satisfies it; so do the short
#: acceptance digests ingest hands in (`"none"` for a refused result). The
#: filename used to be built from the caller's string verbatim, so a digest of
#: `../../escape` wrote outside the receipt root.
_DIGEST_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _digest_segment(value: Any, *, label: str) -> str:
    text = value if isinstance(value, str) else ""
    if not _DIGEST_SEGMENT_RE.match(text) or "/" in text or "\\" in text:
        raise ValueError(f"{label} is not a safe receipt filename segment: {value!r}")
    return text


def _path(acceptance_digest: str) -> Path:
    segment = _digest_segment(acceptance_digest, label="acceptance receipt digest")
    return generated_data_receipt_root() / "ingress" / f"{segment}.json"


def packet_evidence_path(packet_digest: str) -> Path:
    segment = _digest_segment(packet_digest, label="packet digest")
    return generated_data_evidence_root() / "packets" / f"{segment}.json"


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
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def write_packet_evidence(packet: dict[str, Any], packet_digest: str) -> Path:
    path = packet_evidence_path(packet_digest)
    encoded = (
        json.dumps(packet, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    )
    if path.is_file():
        if path.read_bytes() != encoded:
            raise RuntimeError(f"packet digest collision at {path}")
        return path
    _atomic_write(path, encoded)
    return path


def write_ingress(body: dict[str, Any]) -> dict[str, Any]:
    if body["outcome"] not in OUTCOMES:
        raise ValueError(f"unsupported ingress outcome: {body['outcome']}")
    processing_status = str(body.get("processing_status") or "NOT_STARTED")
    if processing_status not in PROCESSING_STATUSES:
        raise ValueError(f"unsupported processing status: {processing_status}")
    stored = {
        **body,
        "processing_status": processing_status,
        "schema": SCHEMA,
        "observed_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }
    digest = hashlib.sha256(
        json.dumps(stored, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()
    stored["receipt_digest"] = digest
    path = _path(stored["acceptance_receipt_digest"])
    _atomic_write(
        path,
        json.dumps(stored, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n",
    )
    return stored


def load_ingress(acceptance_digest: str) -> dict[str, Any] | None:
    path = _path(acceptance_digest)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def quarantine_meta(meta: dict[str, Any]) -> Path:
    segment = _digest_segment(meta.get("packet_digest", "unknown"), label="packet digest")
    path = generated_data_quarantine_root() / f"{segment}.json"
    _atomic_write(
        path,
        json.dumps(meta, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n",
    )
    return path

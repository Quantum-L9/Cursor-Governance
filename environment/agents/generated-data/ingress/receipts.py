from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from environment.agents.runtime_paths import (
    generated_data_quarantine_root,
    generated_data_receipt_root,
)

SCHEMA = "l9.generated-data-ingress-receipt.v1"
OUTCOMES = {"CAPTURED", "NO_REUSABLE_DATA", "QUARANTINED", "REJECTED"}


def _path(acceptance_digest: str) -> Path:
    return generated_data_receipt_root() / "ingress" / f"{acceptance_digest}.json"


def write_ingress(body: dict[str, Any]) -> dict[str, Any]:
    assert body["outcome"] in OUTCOMES
    body = {
        **body,
        "schema": SCHEMA,
        "observed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    digest = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    body["receipt_digest"] = digest
    path = _path(body["acceptance_receipt_digest"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, indent=2, sort_keys=True) + '\n', encoding="utf-8")
    return body


def load_ingress(acceptance_digest: str) -> dict[str, Any] | None:
    path = _path(acceptance_digest)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def quarantine_meta(meta: dict[str, Any]) -> Path:
    path = generated_data_quarantine_root() / f"{meta.get('packet_digest', 'unknown')}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta, indent=2, sort_keys=True) + '\n', encoding="utf-8")
    return path

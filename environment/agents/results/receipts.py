from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from environment.agents.runtime_paths import agent_runtime_root

SCHEMA = "l9.result-acceptance-receipt.v1"


def _root() -> Path:
    return agent_runtime_root() / "results"


def acceptance_path(result_id: str) -> Path:
    return _root() / f"{result_id}.json"


def write_acceptance(body: dict[str, Any]) -> dict[str, Any]:
    body = {
        **body,
        "schema": SCHEMA,
        "observed_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }
    digest = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    body["receipt_digest"] = digest
    path = acceptance_path(body["result_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return body


def load_acceptance(result_id: str) -> dict[str, Any] | None:
    path = acceptance_path(result_id)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

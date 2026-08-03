from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from adapters.common.digests import digest_object, normalize_digest


def collect_returned_artifact(path: str | Path, envelope: dict[str, Any]) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("returned ChatGPT artifact must be an object")
    for key in ("task_id", "program_lock_digest", "contract_digest", "producer_identity"):
        if value.get(key) != envelope.get(key):
            raise ValueError(f"returned artifact {key} mismatch")
    claimed = value.get("artifact_digest")
    body = dict(value)
    body.pop("artifact_digest", None)
    if not isinstance(claimed, str) or normalize_digest(claimed) != digest_object(body):
        raise ValueError("returned artifact digest mismatch")
    return value

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

_DIGEST = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def digest_object(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def normalize_digest(value: str) -> str:
    lowered = value.strip().lower()
    if not _DIGEST.fullmatch(lowered):
        raise ValueError(f"invalid SHA-256 digest: {value!r}")
    if lowered.startswith("sha256:"):
        return lowered
    return "sha256:" + lowered


def verify_embedded_digest(
    payload: Mapping[str, Any],
    field: str,
) -> bool:
    claimed = payload.get(field)
    if not isinstance(claimed, str):
        return False
    body = dict(payload)
    body.pop(field, None)
    return normalize_digest(claimed) == digest_object(body)

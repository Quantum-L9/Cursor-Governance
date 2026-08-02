from __future__ import annotations

import hashlib
import json
from typing import Any


def loads_json(raw: str | bytes) -> Any:
    text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON: line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc


def dumps_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


# Back-compat aliases used by library call sites that already hold text/dicts.
load_json = loads_json
write_json_text = dumps_json

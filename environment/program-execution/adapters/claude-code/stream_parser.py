from __future__ import annotations

import json
import re
from typing import Any

_FENCED_JSON = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _object_from_text(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        return parsed
    fenced = _FENCED_JSON.search(stripped)
    if fenced:
        try:
            parsed = json.loads(fenced.group(1))
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            return parsed
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(stripped[start : end + 1])
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            return parsed
    return None


def _coerce_changed_files(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("changed_files")
    if isinstance(value, str) and value.strip():
        payload["changed_files"] = [value.strip()]
    return payload


def parse_claude_json(output: str) -> dict[str, Any]:
    if not isinstance(output, str) or not output.strip():
        raise ValueError("Claude output must be a non-empty JSON string")
    value = json.loads(output)
    if not isinstance(value, dict):
        raise ValueError("Claude output must be a JSON object")
    result = value.get("result")
    if isinstance(result, dict):
        value["result_payload"] = _coerce_changed_files(dict(result))
    elif isinstance(result, str):
        parsed = _object_from_text(result)
        value["result_payload"] = _coerce_changed_files(
            parsed if parsed is not None else {"text": result}
        )
    return value

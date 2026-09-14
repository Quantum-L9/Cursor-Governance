from __future__ import annotations

import json
from typing import Any


def parse_claude_json(output: str) -> dict[str, Any]:
    if not isinstance(output, str) or not output.strip():
        raise ValueError("Claude output must be a non-empty JSON string")
    value = json.loads(output)
    if not isinstance(value, dict):
        raise ValueError("Claude output must be a JSON object")
    result = value.get("result")
    if isinstance(result, dict):
        value["result_payload"] = dict(result)
    elif isinstance(result, str):
        try:
            parsed = json.loads(result)
        except json.JSONDecodeError:
            parsed = {"text": result}
        if isinstance(parsed, dict):
            value["result_payload"] = parsed
    return value

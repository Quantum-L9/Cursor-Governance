from __future__ import annotations

import json
from typing import Any


def parse_claude_json(output: str) -> dict[str, Any]:
    value = json.loads(output)
    if not isinstance(value, dict):
        raise ValueError("Claude output must be a JSON object")
    result = value.get("result")
    if isinstance(result, str):
        try:
            parsed = json.loads(result)
        except json.JSONDecodeError:
            parsed = {"text": result}
        if isinstance(parsed, dict):
            value["result_payload"] = parsed
    return value

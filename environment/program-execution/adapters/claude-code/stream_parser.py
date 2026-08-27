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
    # #region agent log
    try:
        import time as _time
        from pathlib import Path as _Path

        _log = _Path("/Users/macm2/Cursor-Governance/Cursor-Governance/.cursor/debug-65906b.log")
        _log.parent.mkdir(parents=True, exist_ok=True)
        with _log.open("a", encoding="utf-8") as _dbg:
            _dbg.write(
                json.dumps(
                    {
                        "sessionId": "65906b",
                        "runId": "pre-fix",
                        "hypothesisId": "E",
                        "location": "adapters/claude-code/stream_parser.py:parse_claude_json",
                        "message": "parsed Claude host JSON",
                        "data": {
                            "host_keys": sorted(value.keys()),
                            "result_type": type(result).__name__,
                            "has_result_payload": "result_payload" in value,
                            "payload_keys": (
                                sorted(value["result_payload"].keys())
                                if isinstance(value.get("result_payload"), dict)
                                else None
                            ),
                            "is_error": value.get("is_error"),
                            "subtype": value.get("subtype"),
                            "num_turns": value.get("num_turns"),
                        },
                        "timestamp": int(_time.time() * 1000),
                    }
                )
                + "\n"
            )
    except Exception:
        pass
    # #endregion
    return value

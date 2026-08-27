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

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

_BRIDGE = Path(__file__).resolve().parents[2] / "cursor-subagents" / "result_bridge.py"

def _load_bridge():
    spec = importlib.util.spec_from_file_location("cursor_result_bridge", _BRIDGE)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {_BRIDGE}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cursor_result_bridge"] = mod
    spec.loader.exec_module(mod)
    return mod

result_bridge = _load_bridge()


def normalize(surface_result: dict[str, Any]) -> dict[str, Any]:
    for name in ("validate_and_project", "project_result", "normalize_result"):
        fn = getattr(result_bridge, name, None)
        if callable(fn):
            return fn(surface_result)
    schema = getattr(result_bridge, "RESULT_SCHEMA", "l9.cursor-subagent.result.v1")
    if surface_result.get("schema") != schema:
        if surface_result.get("status") in getattr(result_bridge, "VALID_STATUSES", {"completed"}):
            return {**surface_result, "schema": schema}
        raise ValueError("unsupported cursor result schema")
    return surface_result

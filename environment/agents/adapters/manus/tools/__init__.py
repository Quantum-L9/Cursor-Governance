"""Registry for the Manus governance tool surface.

``build_registry`` is the single source of truth for which tools exist. The
HTTP transport in ``mcp_server.py`` merges this registry into ``tools/list``
and dispatches ``tools/call`` through it, so adding a tool is a module plus a
contract entry — never an edit to the transport.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

from .base import RuntimeContext, ToolInputError, ToolSpec

TOOL_MODULES = (
    "binding",
    "resolve",
    "capabilities",
    "validate_artifact",
    "commands",
    "diff",
)

_ADAPTER_DIR = Path(__file__).resolve().parent.parent
if str(_ADAPTER_DIR) not in sys.path:  # session/ is a sibling package
    sys.path.insert(0, str(_ADAPTER_DIR))


def build_registry(context: RuntimeContext) -> dict[str, ToolSpec]:
    registry: dict[str, ToolSpec] = {}
    for name in TOOL_MODULES:
        module = importlib.import_module(f"{__name__}.{name}")
        spec: ToolSpec = module.build_spec()
        registry[spec.name] = spec
    from session import session_start  # noqa: PLC0415 — sibling package, lazy by design

    session_spec = session_start.build_spec()
    registry[session_spec.name] = session_spec
    return registry


__all__ = ["RuntimeContext", "ToolInputError", "ToolSpec", "build_registry"]

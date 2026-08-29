#!/usr/bin/env python3
"""One beforeShellExecution process: Graphiti shell + L4 + plan-kernel.

Reads stdin once. First deny wins. Does not install a git commit hook.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from types import ModuleType

HOOK_DIR = Path(__file__).resolve().parent
OPS = HOOK_DIR.parent
AUTONOMY = OPS / "autonomy"
GRAPHITI = OPS / "graphiti"
INTERNAL_EVALUATION_ERROR = (
    "INTERNAL_EVALUATION_ERROR: the execution gate could not complete a policy "
    "evaluation for this command, so it denied it. This is a gate fault, not a "
    "policy decision about the command."
)

for extra in (AUTONOMY, GRAPHITI, HOOK_DIR):
    text = str(extra)
    if text not in sys.path:
        sys.path.insert(0, text)


def _emit(permission: str, message: str | None = None) -> int:
    payload: dict[str, str] = {"permission": permission}
    if message:
        payload["user_message"] = message
    print(json.dumps(payload))
    return 0


def _graphiti(raw: str) -> tuple[str, str]:
    try:
        import graphiti_gate_lib as lib
    except Exception:
        return "allow", ""
    try:
        result = lib.shell_gate(raw)
    except Exception:
        if lib.gates_enabled():
            return "deny", "Graphiti gate error — failClosed"
        return "allow", ""
    perm = str(result.get("permission") or "allow")
    msg = str(result.get("user_message") or "")
    return perm, msg


def _load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _l4(raw: str) -> tuple[str, str | None]:
    import resolve_execution_gate as resolver

    try:
        event = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        event = {}
    workspace = resolver.workspace_from_event(event) if isinstance(event, dict) else None
    try:
        gate = resolver.resolve_gate(
            workspace=workspace,
            hook_file=Path(__file__),
            env=os.environ,
        )
    except FileNotFoundError:
        return "deny", INTERNAL_EVALUATION_ERROR
    try:
        module = _load_module(gate, "l9_local_execution_gate")
        return module.cursor_shell_verdict(raw)
    except Exception:
        return "deny", INTERNAL_EVALUATION_ERROR


def _plan_kernel(raw: str) -> tuple[str, str]:
    import plan_kernel_gate as pk

    try:
        event = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        event = {}
    if not isinstance(event, dict):
        event = {}
    permission, message = pk.execute_verdict(event)
    return permission, message or ""


def main() -> int:
    raw = sys.stdin.read()
    perm, msg = _graphiti(raw)
    if perm == "deny":
        return _emit("deny", msg or "Graphiti gate denied")
    perm, msg = _l4(raw)
    if perm == "deny":
        return _emit("deny", msg or INTERNAL_EVALUATION_ERROR)
    perm, msg = _plan_kernel(raw)
    if perm == "deny":
        return _emit("deny", msg or "plan kernel denied")
    return _emit("allow")


if __name__ == "__main__":
    raise SystemExit(main())

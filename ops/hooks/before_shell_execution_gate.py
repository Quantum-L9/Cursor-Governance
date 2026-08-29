#!/usr/bin/env python3
"""One beforeShellExecution process: Graphiti shell + L4 + plan-kernel.

Reads stdin once. First deny wins. Does not install a git commit hook.

When setup copies this file into ``~/.cursor/hooks`` (a real file, not a
symlink into ``ops/hooks``), ``Path(__file__).parent`` is not the governance
``ops/hooks`` tree. Resolve ``ops`` from the hook event's workspace first,
then from a live SSOT, then from this file's adjacent layout.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from types import ModuleType

INTERNAL_EVALUATION_ERROR = (
    "INTERNAL_EVALUATION_ERROR: the execution gate could not complete a policy "
    "evaluation for this command, so it denied it. This is a gate fault, not a "
    "policy decision about the command."
)
_FAULT_LOG = Path.home() / ".cursor" / "hooks" / "before-shell-execution-gate.last-error"


def _record_fault(detail: str) -> None:
    try:
        _FAULT_LOG.write_text(detail[:4000], encoding="utf-8")
    except OSError:
        pass


def _existing_ops(root: Path, *, require_combined: bool = False) -> Path | None:
    try:
        ops = root.expanduser().resolve() / "ops"
    except OSError:
        return None
    if not (ops / "autonomy" / "local_execution_gate.py").is_file():
        return None
    if require_combined and not (ops / "hooks" / "before_shell_execution_gate.py").is_file():
        return None
    return ops


def _event_roots(event: dict[str, object]) -> list[Path]:
    candidates: list[Path] = []
    for key in ("cwd", "workspace", "workspace_path"):
        raw = event.get(key)
        if raw:
            candidates.append(Path(str(raw)))
    roots = event.get("workspace_roots") or event.get("workspaceRoots") or []
    if isinstance(roots, list):
        candidates.extend(Path(str(item)) for item in roots)
    return candidates


def _ops_from_event(event: dict[str, object]) -> Path | None:
    for cand in _event_roots(event):
        found = _existing_ops(cand, require_combined=True)
        if found is not None:
            return found
    return None


def _ops_fallback() -> Path:
    here = Path(__file__).resolve().parent
    adjacent = here.parent
    if (adjacent / "autonomy" / "local_execution_gate.py").is_file() and (
        here / "before_shell_execution_gate.py"
    ).is_file():
        return adjacent
    env = os.environ.get("GOV_ROOT") or os.environ.get("L9_GOV_ROOT")
    if env:
        found = _existing_ops(Path(env), require_combined=True)
        if found is not None:
            return found
    wt_home = Path.home() / ".l9" / "gov-worktrees"
    if wt_home.is_dir():
        matches = list(wt_home.glob("*/ops/hooks/before_shell_execution_gate.py"))
        if matches:
            newest = max(matches, key=lambda path: path.stat().st_mtime)
            return newest.resolve().parent.parent
    ssot = _existing_ops(Path.home() / ".cursor-governance")
    if ssot is not None:
        return ssot
    return adjacent


def _bind_ops(ops: Path) -> None:
    for extra in (ops / "autonomy", ops / "graphiti", ops / "hooks"):
        text = str(extra)
        if extra.is_dir() and text not in sys.path:
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


def _l4(raw: str, event: dict[str, object], ops: Path) -> tuple[str, str | None]:
    import resolve_execution_gate as resolver

    del event  # ops is already bound from the event / fallback
    workspace = ops.parent
    hook_file = ops / "hooks" / "before_shell_execution_gate.py"
    if not hook_file.is_file():
        hook_file = Path(__file__)
    try:
        gate = resolver.resolve_gate(
            workspace=workspace,
            hook_file=hook_file,
            env=os.environ,
        )
    except FileNotFoundError as exc:
        _record_fault(f"resolve_gate:{exc}")
        return "deny", INTERNAL_EVALUATION_ERROR
    try:
        module = _load_module(gate, "l9_local_execution_gate")
        return module.cursor_shell_verdict(raw)
    except Exception as exc:  # noqa: BLE001 — hook must fail closed
        _record_fault(f"cursor_shell_verdict:{type(exc).__name__}:{exc}")
        return "deny", INTERNAL_EVALUATION_ERROR


def _plan_kernel(raw: str, event: dict[str, object]) -> tuple[str, str]:
    import plan_kernel_gate as pk

    permission, message = pk.execute_verdict(event)
    return permission, message or ""


def main() -> int:
    try:
        return _main()
    except Exception as exc:  # noqa: BLE001 — hook must fail closed
        _record_fault(f"main:{type(exc).__name__}:{exc}")
        return _emit("deny", INTERNAL_EVALUATION_ERROR)


def _main() -> int:
    raw = sys.stdin.read()
    try:
        parsed = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        parsed = {}
    event: dict[str, object] = parsed if isinstance(parsed, dict) else {}
    ops = _ops_from_event(event) or _ops_fallback()
    _bind_ops(ops)
    perm, msg = _graphiti(raw)
    if perm == "deny":
        return _emit("deny", msg or "Graphiti gate denied")
    perm, msg = _l4(raw, event, ops)
    if perm == "deny":
        return _emit("deny", msg or INTERNAL_EVALUATION_ERROR)
    perm, msg = _plan_kernel(raw, event)
    if perm == "deny":
        return _emit("deny", msg or "plan kernel denied")
    return _emit("allow")


if __name__ == "__main__":
    raise SystemExit(main())

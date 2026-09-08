#!/usr/bin/env python3
"""Thin Claude adapter → canonical memory control plane (campaign stage C8).

Single egress for agent episodic memory on the Claude surface: every
lifecycle hook reaches memory through ``ops/memory`` — the runtime binding
proves which ``l9-graphite-memory`` package runs, and
``MemoryControlPlaneClient`` turns one request into one ``l9-memory <op>``
call whose exit code and receipt are the verdict. No HTTP ``L9_MEMORY_*``
client, no provider URL, no bearer, no second store. This module replaces
the retired provider bridge, which shelled out to the legacy provider client
under ``ops/graphiti``.

The bridge deliberately exposes no phase-lock surface. Memory conflicts are
*evidence* an agent may reason about; nothing here can mint repository-write
permission (rules/96-multi-agent-main-bound-execution.mdc, E7/E8).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

#: The file that proves a checkout is the governance root for this bridge.
BOUNDARY_REL = Path("ops/memory/control_plane_client.py")


def find_governance_root() -> Path:
    configured = os.environ.get("L9_GOVERNANCE_DIR", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if (candidate / BOUNDARY_REL).is_file():
            return candidate
    home = Path.home() / ".cursor-governance"
    if (home / BOUNDARY_REL).is_file():
        return home
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / BOUNDARY_REL).is_file():
            return parent
    return home


def ensure_importable(root: Path | None = None) -> Path:
    """Put the governance root first on ``sys.path`` so ``ops.memory`` imports."""
    root = root or find_governance_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root


def bind_session_env(env: dict[str, str], session_id: str | None) -> dict[str, str]:
    """Force the memory session id to the caller's session (no setdefault)."""
    if session_id:
        env["CURSOR_CONVERSATION_ID"] = session_id
    return env


def memory_client(session_id: str | None = None) -> Any:
    """A canonical client bound to this checkout's memory runtime.

    Returns the client even when unbound: callers read ``client.binding.ok``
    and its reasons, so an unbound runtime is reported rather than guessed.
    """
    ensure_importable()
    from ops.memory.control_plane_client import MemoryControlPlaneClient
    from ops.memory.runtime_binding import resolve_runtime_binding

    return MemoryControlPlaneClient(resolve_runtime_binding(), session_id=session_id)


def hydrate(
    task: str, *, workspace: Path, session_id: str, continuation_policy: str = "task"
) -> dict[str, Any]:
    """Canonical hydration for one repository (integration-receipt shape).

    ``continuation_policy`` is ``task`` (resume only this task's capsule) or
    ``repository_fallback`` (a SessionStart with no task yet may take the
    newest repository capsule, marked as a fallback on the receipt).
    """
    ensure_importable()
    from ops.memory.hydration import canonical_hydrate

    return canonical_hydrate(
        workspace, task=task, session_id=session_id, continuation_policy=continuation_policy
    ).as_dict()


def conflicts(*, workspace: Path, session_id: str) -> dict[str, Any]:
    """Memory conflicts are evidence, never a mutex."""
    ensure_importable()
    from ops.memory.namespace_context import resolve_namespace_context

    context = resolve_namespace_context(workspace)
    namespace = context.write_namespace_hint
    if not namespace:
        return {"status": "NAMESPACE_UNRESOLVED", "warnings": list(context.warnings)}
    outcome = memory_client(session_id).conflicts(workspace=str(workspace), namespace=namespace)
    return {"status": outcome.status.value, "ok": outcome.ok, "error": outcome.error}


__all__ = [
    "BOUNDARY_REL",
    "bind_session_env",
    "conflicts",
    "ensure_importable",
    "find_governance_root",
    "hydrate",
    "memory_client",
]

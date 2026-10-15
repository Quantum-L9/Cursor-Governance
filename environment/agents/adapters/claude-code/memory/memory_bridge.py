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


#: Hook-lane surface for the Claude SessionStart health check (ADR-0033 B7):
#: a resolve/health/capabilities-only envelope in
#: ``ops/config/memory-hook-envelopes.json`` — SessionStart reads no records. The agent
#: itself writes through the public MCP / ``l9-memory`` surface, never here.
HOOK_SURFACE = "claude-session-start"


def memory_client(session_id: str | None = None, *, surface: str = HOOK_SURFACE) -> Any:
    """A canonical client bound to this checkout's memory runtime.

    Returns the client even when unbound: callers read ``client.binding.ok``
    and its reasons, so an unbound runtime is reported rather than guessed.
    """
    ensure_importable()
    from ops.memory.control_plane_client import MemoryControlPlaneClient
    from ops.memory.runtime_binding import resolve_runtime_binding

    return MemoryControlPlaneClient(
        resolve_runtime_binding(), session_id=session_id, surface=surface
    )


__all__ = [
    "BOUNDARY_REL",
    "bind_session_env",
    "ensure_importable",
    "find_governance_root",
    "memory_client",
]

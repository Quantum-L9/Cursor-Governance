#!/usr/bin/env python3
"""Refusal-only Manus lifecycle compatibility, not a native Memory client.

Startup policy is health-only; retrieval is explicit/on-demand and never a
repository-write precondition. The owner has no admitted Manus native API, so
these methods do no filesystem, subprocess, hydrate, close, or temporary-file
work. Bounded operator/hook authority stays with the existing shared owners.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from typing import Any

MANUS_AGENT_ID = "manus"
MANUS_USER_ID = "manus_agent"
MANUS_SOURCE = "manus"
START_SURFACE = "manus-session-start"
END_SURFACE = "manus-session-end"
MAX_TASK_CHARS = 1_000
MAX_SUMMARY_CHARS = 4_000
MAX_NEXT_ACTION_CHARS = 1_000
MAX_CONTEXT_CHARS = 12_000
_SESSION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$")
_LEGACY_AUTHORITY_NAMES = (
    "L9_MANUS_MEMORY_AUTHORITY_JSON",
    "L9_MEMORY_AGENTS_DOOR_SECRET",
    "L9_MEMORY_HUMAN_DOOR_SECRET",
    "L9_MEMORY_AGENT_ASSERTION",
    "L9_MEMORY_AGENT_SIGNING_KEYS_JSON",
    "L9_MEMORY_AGENT_GRANTS_JSON",
    "L9_MEMORY_IDENTITY_ASSERTION_JSON",
    "L9_MEMORY_IDENTITY_ASSERTION_HMAC",
    "L9_MEMORY_SECRET_MAP",
    "L9_MEMORY_GRANTS_MAP",
)


class MemoryAccessError(RuntimeError):
    """The native Memory package/client admission is unavailable."""


def native_memory_status(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Report fixed unproved admission layers and environment names, not values."""
    source = os.environ if env is None else env
    return {
        "status": "UPSTREAM_BLOCKED",
        "transport": "streamable-http",
        "authentication": "unverified",
        "package": "UPSTREAM_BLOCKED",
        "native_client": "UNBOUND",
        "live": "UNKNOWN",
        "startup": "health-only",
        "retrieval": "explicit-on-demand",
        "coding_session_requires_memory": False,
        "legacy_environment_present": [name for name in _LEGACY_AUTHORITY_NAMES if name in source],
        "errors": ["native owner package/Manus client API and OAuth actor admission unavailable"],
    }


def signed_agent_door_status(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Retained name only: inherited assertions never mean native ready."""
    return native_memory_status(env)


def require_signed_agent_door(env: Mapping[str, str] | None = None) -> None:
    del env
    raise MemoryAccessError("UPSTREAM_BLOCKED: stdio/HMAC retired; native Manus client UNBOUND")


def validate_session_id(value: Any) -> str:
    if not isinstance(value, str) or not _SESSION_ID.fullmatch(value):
        raise ValueError("session_id must be 1-120 safe identifier characters")
    return value


def start_session(*, workspace: Any, task: Any, session_id: Any) -> dict[str, Any]:
    """Refuse before resolving workspace or inspecting task/session content."""
    del workspace, task, session_id
    return native_memory_status() | {"operation": "health-only-start", "surface": START_SURFACE}


def close_session_from_manus(
    *, workspace: Any, session_id: Any, summary: Any, next_action: Any
) -> dict[str, Any]:
    """No fake close receipt or admin distill emulation while native is blocked."""
    del workspace, session_id, summary, next_action
    return native_memory_status() | {"operation": "close", "surface": END_SURFACE}


__all__ = [
    "END_SURFACE",
    "MAX_CONTEXT_CHARS",
    "MANUS_AGENT_ID",
    "MemoryAccessError",
    "START_SURFACE",
    "close_session_from_manus",
    "native_memory_status",
    "require_signed_agent_door",
    "signed_agent_door_status",
    "start_session",
    "validate_session_id",
]

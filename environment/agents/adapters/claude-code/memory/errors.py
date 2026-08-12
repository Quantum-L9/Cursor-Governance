#!/usr/bin/env python3
"""Shared exception types for the memory enforcement modules.

Stdlib only — these hooks run in any consumer repository without a virtualenv.
Transport is Cursor Graphiti via ``graphiti_bridge`` (ADR-0006); there is no
HTTP ``memory_client`` side door.
"""

from __future__ import annotations


class MemoryErrorBase(RuntimeError):
    """Base class for every memory-subsystem error."""


class MemoryWriteDenied(MemoryErrorBase):
    """Raised when a memory write is refused by attribution policy.

    The write never reaches Graphiti because the writer's identity failed —
    missing namespace/agent/user identity, or an identity reserved for another
    surface (for example Cursor's ``cursor_agent``).
    """

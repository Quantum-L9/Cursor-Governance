#!/usr/bin/env python3
"""Shared exception types for the memory enforcement modules.

Stdlib only — these hooks run in any consumer repository without a virtualenv.
Transport is the canonical memory control plane via ``memory_bridge``
(``ops/memory``, stage C8); there is no HTTP ``memory_client`` side door and
no provider client.
"""

from __future__ import annotations


class MemoryErrorBase(RuntimeError):
    """Base class for every memory-subsystem error."""


class MemoryWriteDenied(MemoryErrorBase):
    """Raised when a memory write is refused by attribution policy.

    The write never reaches memory because the writer's identity failed —
    missing namespace/agent/user identity, or an identity reserved for another
    surface (for example Cursor's ``cursor_agent``).
    """

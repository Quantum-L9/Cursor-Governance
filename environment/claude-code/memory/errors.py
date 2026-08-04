#!/usr/bin/env python3
"""Shared exception types for the memory enforcement modules.

Defined in their own module so the policy layer (``memory_state``) and the
transport client (``memory_client``) can both import them without either
importing the other. This breaks the cycle that would otherwise appear once the
client's write guard has to raise a policy-defined error: ``memory_client``
depends on ``memory_state`` for identity policy, so ``memory_state`` must not
import ``memory_client`` to obtain the exception it raises.

Stdlib only — these hooks run in any consumer repository without a virtualenv.
"""

from __future__ import annotations


class MemoryErrorBase(RuntimeError):
    """Base class for every memory-subsystem error."""


class MemoryWriteDenied(MemoryErrorBase):
    """Raised when a memory write is refused before it reaches the server.

    Distinct from a transport error (``memory_client.MemoryError``): the write
    never left the client because the writer's identity failed the attribution
    policy — missing namespace/agent/user identity, or an identity reserved for
    another surface (for example Cursor's ``cursor_agent``). Callers on read
    paths fail open; write paths let this propagate so the write is disabled
    rather than silently mis-attributed.
    """

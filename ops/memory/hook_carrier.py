"""Which carrier delivers a hook-lane write to canonical memory.

Two carriers, one decision, made here and nowhere else:

- ``local`` — the hook lane spawns the bound ``l9-memory`` runtime (transport
  A). Correct where that runtime *is* the shared authority for the surface.
- ``relay`` — the hook lane does not open a local store at all. Each
  envelope-admitted record is queued for the agent, which writes it to the
  hosted ``MemoryService`` through the account-managed connector
  (CANONICAL_LAW §8.10) and acknowledges the connector receipt
  (``ops/memory/relay.py``). This is the interim carrier while the hosted
  service admits no hook principal (memory ADR-103; CANONICAL_LAW §8.11).

On a Claude Code cloud container the local store is container-scratch: it is
discarded with the container, so a "committed" local write there is a write
nobody will ever read. Relay is therefore the default when
``CLAUDE_CODE_REMOTE=true``. ``L9_MEMORY_HOOK_CARRIER`` overrides in either
direction, and an unrecognised value is refused rather than guessed: a
misspelt override that silently fell back to ``local`` is exactly how hook
memories were being lost.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

CARRIER_ENV = "L9_MEMORY_HOOK_CARRIER"
RELAY = "relay"
LOCAL = "local"
CARRIERS = frozenset({RELAY, LOCAL})


class CarrierError(ValueError):
    """The carrier override names no known carrier; nothing may be written."""


def resolve_carrier(env: Mapping[str, str] | None = None) -> str:
    """``relay`` or ``local`` for this process; raises :class:`CarrierError`."""

    source = os.environ if env is None else env
    requested = str(source.get(CARRIER_ENV, "")).strip().lower()
    if requested in CARRIERS:
        return requested
    if requested:
        msg = (
            f"{CARRIER_ENV}={requested!r} names no hook carrier "
            f"(expected one of {sorted(CARRIERS)}); refusing to write anywhere"
        )
        raise CarrierError(msg)
    if str(source.get("CLAUDE_CODE_REMOTE", "")).strip().lower() == "true":
        return RELAY
    return LOCAL

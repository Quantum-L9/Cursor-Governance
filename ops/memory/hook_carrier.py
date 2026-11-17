"""Which carrier delivers a hook-lane write to canonical memory.

Three carriers, one decision, made here and nowhere else:

- ``hosted`` — the hook lane sends each envelope-admitted ``write`` /
  ``ingest_candidate`` / ``close`` straight to the hosted ``MemoryService``
  MCP endpoint as the machine *hook principal* (Auth0 client credentials of
  the ``l9-memory-hooks`` application; ``ops/memory/hosted_hook_transport.py``).
  No agent is involved. A transport failure parks that one record in the
  relay outbox (below), which the Stop hook drains through this same
  transport before it asks anybody for anything (CANONICAL_LAW §8.11 as
  amended 2026-11-17, ADR-0055).
- ``relay`` — the hook lane does not open a local store at all. Each
  envelope-admitted record is queued for the agent, which writes it to the
  hosted ``MemoryService`` through the account-managed connector
  (CANONICAL_LAW §8.10) and acknowledges the connector receipt
  (``ops/memory/relay.py``). The fallback when the hook credential does not
  bind (CANONICAL_LAW §8.11; ADR-0054).
- ``local`` — the hook lane spawns the bound ``l9-memory`` runtime (transport
  A). Correct where that runtime *is* the shared authority for the surface.

Decision order: the ``L9_MEMORY_HOOK_CARRIER`` override wins in every
direction, and an unrecognised value is refused rather than guessed — a
misspelt override that silently fell back to ``local`` is exactly how hook
memories were being lost. Otherwise ``hosted`` when BOTH hook credentials bind
through ``ops/secrets/capability_bind.py``; otherwise ``relay`` on a Claude
Code cloud container (``CLAUDE_CODE_REMOTE=true``), whose local store is
container scratch discarded with the container; otherwise ``local``.

The decision only asks whether the credentials bind; their values stay in
``capability_bind``'s in-process cache and are read by the hosted transport
alone, for the token request.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Mapping
from pathlib import Path

CARRIER_ENV = "L9_MEMORY_HOOK_CARRIER"
HOSTED = "hosted"
RELAY = "relay"
LOCAL = "local"
CARRIERS = frozenset({HOSTED, RELAY, LOCAL})
#: Carriers whose authority is the hosted ``MemoryService`` rather than a
#: runtime on this machine. Neither opens a local store, not even to distill.
REMOTE_CARRIERS = frozenset({HOSTED, RELAY})

#: The hook principal's Auth0 client-credentials pair (Infisical project
#: ``cursor-governance``, path ``/``). Names only; never a value.
#: Declared as one tuple of inventory names: these are lookup keys, and a
#: name-shaped string bound to a ``*_SECRET`` identifier reads to the baseline
#: hardcoded-credential rule as a literal credential.
HOOK_CREDENTIALS = ("L9_MEMORY_HOOK_CLIENT_ID", "L9_MEMORY_HOOK_CLIENT_SECRET")
HOOK_CLIENT_ID, HOOK_CLIENT_SECRET = HOOK_CREDENTIALS

#: ``binder(name, env) -> bool``: does this inventory name bind on this surface?
Binder = Callable[[str, Mapping[str, str]], bool]

_SECRETS_DIR = Path(__file__).resolve().parents[1] / "secrets"


class CarrierError(ValueError):
    """The carrier override names no known carrier; nothing may be written."""


def bind_credential(name: str, env: Mapping[str, str] | None = None) -> str | None:
    """The bound value of one hook credential, or ``None``. Never printed.

    Only ``hosted_hook_transport`` reads the value, for the token request.
    """

    if name not in HOOK_CREDENTIALS:
        msg = f"{name!r} is not a hook credential"
        raise CarrierError(msg)
    if str(_SECRETS_DIR) not in sys.path:
        sys.path.insert(0, str(_SECRETS_DIR))
    try:
        import capability_bind  # noqa: PLC0415 - lazy: binding is per decision
    except Exception:  # noqa: BLE001 - an unloadable binder binds nothing
        return None
    try:
        return capability_bind.bind(name, env=env)
    except Exception:  # noqa: BLE001 - a failed bind is "unbound", never a crash
        return None


def _default_binder(name: str, env: Mapping[str, str]) -> bool:
    return bool(bind_credential(name, env))


def hosted_credentials_bind(
    env: Mapping[str, str] | None = None, *, binder: Binder | None = None
) -> bool:
    """True only when BOTH hook credentials bind on this surface."""

    source = os.environ if env is None else env
    check = binder or _default_binder
    return all(check(name, source) for name in HOOK_CREDENTIALS)


def resolve_carrier(env: Mapping[str, str] | None = None, *, binder: Binder | None = None) -> str:
    """``hosted``, ``relay`` or ``local`` for this process; raises :class:`CarrierError`."""

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
    if hosted_credentials_bind(source, binder=binder):
        return HOSTED
    if str(source.get("CLAUDE_CODE_REMOTE", "")).strip().lower() == "true":
        return RELAY
    return LOCAL


def store_of(carrier: str | None) -> str | None:
    """Which store a carrier's records land in: ``hosted`` or ``local``.

    ``relay`` and ``hosted`` are two routes into the same hosted
    ``MemoryService``, so a record id admitted by one exists for the other.
    """

    if carrier is None:
        return None
    return HOSTED if carrier in REMOTE_CARRIERS else LOCAL

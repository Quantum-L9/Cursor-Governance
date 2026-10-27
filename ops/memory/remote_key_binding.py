"""Durable per-agent signing-key seam for the dormant remote stdio bridge.

The bridge may hold one agent's key in this process. It never creates a key,
writes Infisical, or returns the grants map. An ephemeral key minted inside a
hosted container is not hosted signed-agent parity and is refused.

``capability_bind`` is called only when ``L9_MEMORY_REMOTE_KEY_NAME`` is set
and the caller did not inject a binder. Tests inject the binder, so validation
does not read a real secret.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from pathlib import Path

SECRET_MAP_ENV = "L9_MEMORY_REMOTE_SECRET_MAP"
KEY_NAME_ENV = "L9_MEMORY_REMOTE_KEY_NAME"
EPHEMERAL_HOSTED = (
    "ephemeral hosted signing keys are not hosted signed-agent parity; set a durable key ref"
)

Bind = Callable[[str], str | None]


def resolve_signing_key(
    agent_id: str,
    env: Mapping[str, str],
    *,
    bind: Bind | None = None,
) -> str:
    """Return ``agent_id``'s signing key, or raise ``KeyError`` without the key."""

    if not agent_id or agent_id == "human":
        raise KeyError("no remote signing key for an unresolved or human actor")
    secret_map = env.get(SECRET_MAP_ENV, "").strip()
    key_name = env.get(KEY_NAME_ENV, "").strip()
    hosted = env.get("CLAUDE_CODE_REMOTE", "").strip().lower() == "true"
    if hosted and not secret_map and not key_name:
        raise KeyError(EPHEMERAL_HOSTED)
    if secret_map:
        return _key_from_map(Path(secret_map), agent_id)
    if key_name:
        resolver = bind if bind is not None else _default_bind()
        value = resolver(key_name)
        if not value:
            raise KeyError(f"durable key name is unbound for agent_id={agent_id}")
        return value
    raise KeyError(
        f"remote opt-in has no durable signing key ref ({SECRET_MAP_ENV} or {KEY_NAME_ENV})"
    )


def _key_from_map(path: Path, agent_id: str) -> str:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise KeyError(f"durable signing-key map is unreadable: {type(exc).__name__}") from exc
    keys = raw.get("agent_signing_keys") if isinstance(raw, dict) else None
    if not isinstance(keys, dict) or agent_id not in keys:
        raise KeyError(f"no signing key for agent_id={agent_id}")
    value = keys[agent_id]
    if not isinstance(value, str) or not value:
        raise KeyError(f"no signing key for agent_id={agent_id}")
    return value


def _default_bind() -> Bind:
    from ops.secrets.capability_bind import bind as capability_bind

    return capability_bind

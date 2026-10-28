"""Writer identity for Graphiti episodes (agent_id dual-stamp)."""

from __future__ import annotations

from typing import Any


class IdentityError(ValueError):
    """Missing or cross-surface writer identity."""


def resolve_write_identity(
    *,
    explicit_agent_id: str | None = None,
    explicit_user_id: str | None = None,
    surface: str = "",
) -> dict[str, str]:
    """agent_id / user_id for a memory write — DERIVED, never configured (no drift).

    ``ops/memory/agent_identity.py`` is the one source. The returned ``surface``
    is the resolved SurfaceIdentity id, and the key is omitted when that
    surface is unknown. ``surface`` on the call is a coarse cross-surface
    gate (``cursor`` / ``claude-code``), not the identity value.
    """
    del explicit_user_id  # derived from agent_id; a configured value could drift
    from ops.memory.agent_identity import (  # noqa: PLC0415
        resolve_agent_id,
        resolve_surface_id,
        unresolved_reason,
        user_id_for,
    )

    derived = resolve_agent_id()
    explicit = (explicit_agent_id or "").strip()
    if not derived:
        raise IdentityError(f"memory write denied: no memory identity ({unresolved_reason()})")
    if explicit and explicit != derived:
        raise IdentityError(
            f"memory write denied: identity drift — caller says {explicit!r} but this "
            f"process is {derived!r} (ops/memory/agent_identity.py)"
        )
    if surface == "claude-code" and derived == "cursor":
        raise IdentityError(
            "memory write denied: a Claude surface cannot stamp the Cursor identity"
        )
    identity = {"agent_id": derived, "user_id": user_id_for(derived)}
    fine = resolve_surface_id()
    if fine:
        identity["surface"] = fine
    return identity


def stamp_source_description(agent_id: str, kind: str) -> str:
    return f"agent={agent_id};kind={kind}"


def envelope_body(body: str, *, agent_id: str, user_id: str, kind: str) -> str:
    """Prefix a compact attribution envelope; preserve JSON bodies when possible."""
    text = body.strip()
    if text.startswith("{"):
        try:
            import json

            data: Any = json.loads(text)
            if isinstance(data, dict):
                data.setdefault("agent_id", agent_id)
                data.setdefault("user_id", user_id)
                data.setdefault("kind", kind)
                return json.dumps(data, ensure_ascii=False)
        except (json.JSONDecodeError, TypeError):
            # Malformed or non-serializable JSON: fall back to the text envelope below.
            pass
    return f"[agent={agent_id} user={user_id} kind={kind}]\n{text}"

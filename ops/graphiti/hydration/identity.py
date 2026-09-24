"""Writer identity for Graphiti episodes (agent_id dual-stamp)."""

from __future__ import annotations

import os
from typing import Any


class IdentityError(ValueError):
    """Missing or cross-surface writer identity."""


def resolve_write_identity(
    *,
    explicit_agent_id: str | None = None,
    explicit_user_id: str | None = None,
    surface: str = "cursor",
) -> dict[str, str]:
    """agent_id / user_id for a memory write — DERIVED, never configured (no drift).

    ``ops/memory/agent_identity.py`` is the one source: on a Cursor or Claude
    Code surface the identity comes from the host's own markers (cursor,
    claude-code-desktop, claude-code-mobile). An explicit id that disagrees
    with the surface that is actually running is refused as drift rather than
    recorded. Only a process with no host markers (manus, codex, gemini, an
    operator shell) is identified by its explicit id / L9_MEMORY_AGENT_ID. The
    retired single ``claude-code`` names no surface and is refused. ``user_id``
    is always derived from ``agent_id``; ``explicit_user_id`` is ignored.
    """
    del explicit_user_id  # derived from agent_id; a configured value could drift
    from ops.memory.agent_identity import (  # noqa: PLC0415
        RETIRED,
        resolve_agent_id,
        unresolved_reason,
        user_id_for,
    )

    derived = resolve_agent_id()
    explicit = (explicit_agent_id or "").strip()
    if derived:
        if explicit and explicit != derived:
            raise IdentityError(
                f"memory write denied: identity drift — caller says {explicit!r} but this "
                f"process is {derived!r} (ops/memory/agent_identity.py)"
            )
        agent_id = derived
    else:
        agent_id = explicit or os.environ.get("L9_MEMORY_AGENT_ID", "").strip()
        if not agent_id or agent_id in RETIRED:
            raise IdentityError(f"memory write denied: no memory identity ({unresolved_reason()})")
    if surface == "claude-code" and agent_id == "cursor":
        raise IdentityError(
            "memory write denied: a Claude surface cannot stamp the Cursor identity"
        )
    return {"agent_id": agent_id, "user_id": user_id_for(agent_id), "surface": surface}


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

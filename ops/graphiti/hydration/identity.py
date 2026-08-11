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
    """Resolve agent_id / user_id for a memory write.

    Cursor hooks export ``L9_MEMORY_AGENT_ID=cursor`` and ``USER_ID=cursor_agent``.
    Claude keeps ``claude-code`` / contract defaults. Empty agent_id is refused.
    """
    agent_id = (explicit_agent_id or os.environ.get("L9_MEMORY_AGENT_ID", "")).strip()
    user_id = (explicit_user_id or os.environ.get("USER_ID", "")).strip()
    if not agent_id:
        raise IdentityError("memory write denied: missing agent_id (set L9_MEMORY_AGENT_ID)")
    if surface == "claude-code":
        # Claude must not impersonate Cursor reserved user identities.
        reserved = {"cursor_agent", "cursor-agent", "cursor"}
        if agent_id in reserved or user_id in {"cursor_agent", "cursor-agent"}:
            raise IdentityError(
                f"memory write denied: Claude cannot stamp Cursor identity "
                f"(agent_id={agent_id!r}, user_id={user_id!r})"
            )
        if not user_id:
            user_id = "claude_code_agent"
    elif not user_id:
        user_id = "cursor_agent" if agent_id == "cursor" else f"{agent_id}_agent"
    return {"agent_id": agent_id, "user_id": user_id, "surface": surface}


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

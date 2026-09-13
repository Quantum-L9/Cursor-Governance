"""Mint ADR-0031 signed agent assertions for MCP stdio launch env.

Never loads or emits L9_MEMORY_HUMAN_DOOR_SECRET into agent processes.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# Prefer package helper when the bound interpreter has l9-graphite-memory>=2.4.0
try:
    from l9_graphite_memory.authz.signed_assertion import mint_assertion
except Exception:  # pragma: no cover - fallback for unbound runtimes
    import hashlib
    import hmac
    import secrets
    import time

    def mint_assertion(agent_id: str, signing_key: str, ttl_seconds: int = 3600) -> str:
        exp = int(time.time()) + int(ttl_seconds)
        nonce = secrets.token_hex(8)
        payload = f"{agent_id}.{exp}.{nonce}"
        sig = hmac.new(
            signing_key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        return f"{payload}.{sig}"


def load_grants_file(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "grants" in data:
        return data["grants"]
    return data


def build_agent_mcp_env(
    *,
    agent_id: str,
    agents_door_secret: str,
    signing_key: str,
    grants: dict[str, Any],
    signing_keys: dict[str, str] | None = None,
    ttl_seconds: int = 3600,
) -> dict[str, str]:
    """Env block for an agent MCP server process (never includes human secret)."""
    if "HUMAN" in agent_id.upper() or agent_id == "human":
        raise ValueError("refusing to mint agent MCP env for human private entrance")
    assertion = mint_assertion(agent_id, signing_key, ttl_seconds=ttl_seconds)
    keys = signing_keys or {agent_id: signing_key}
    return {
        "L9_MEMORY_AGENTS_DOOR_SECRET": agents_door_secret,
        "L9_MEMORY_AGENT_ASSERTION": assertion,
        "L9_MEMORY_AGENT_SIGNING_KEYS_JSON": json.dumps(keys),
        "L9_MEMORY_AGENT_GRANTS_JSON": json.dumps(grants),
        "L9_MEMORY_AGENT_ID": agent_id,
    }


def env_from_local_secret_map(
    agent_id: str,
    secret_map_path: Path,
    grants_path: Path,
    *,
    ttl_seconds: int = 3600,
) -> dict[str, str]:
    raw = json.loads(secret_map_path.read_text(encoding="utf-8"))
    door = raw["agents_door_secret"]
    keys = raw["agent_signing_keys"]
    if agent_id not in keys:
        raise KeyError(f"no signing key for agent_id={agent_id}")
    grants = load_grants_file(grants_path)
    return build_agent_mcp_env(
        agent_id=agent_id,
        agents_door_secret=door,
        signing_key=keys[agent_id],
        grants=grants,
        signing_keys=keys,
        ttl_seconds=ttl_seconds,
    )

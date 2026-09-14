"""Mint ADR-0031 signed agent assertions for MCP stdio launch env.

Per-principal by construction. The environment built here carries exactly one
signing key (``{agent_id: key}``) and exactly one grant entry
(``{agent_id: grant}``) — the launching principal's own. The package server
selects the verifying key by the ``agent_id`` the assertion claims, so a launch
context holding only its own material can neither read nor replace a peer's
key, and an assertion it forges for a peer fails at the verifier as an unknown
agent (the peer's key is absent) rather than being accepted under the peer's
grants. The whole signing-key map and the whole grants map never leave the
local secret store.

Never loads or emits ``L9_MEMORY_HUMAN_DOOR_SECRET`` into agent processes.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

#: Wire format shared with ``l9_graphite_memory.authz.signed_assertion``:
#: token ``agent_id.exp.nonce.hexsig`` over the payload ``agent_id|exp|nonce``.
_TOKEN_SEP = "."
_PAYLOAD_SEP = "|"

HUMAN_PRINCIPAL = "human"

ENV_AGENTS_DOOR_SECRET = "L9_MEMORY_AGENTS_DOOR_SECRET"
ENV_AGENT_ASSERTION = "L9_MEMORY_AGENT_ASSERTION"
ENV_AGENT_SIGNING_KEYS_JSON = "L9_MEMORY_AGENT_SIGNING_KEYS_JSON"
ENV_AGENT_GRANTS_JSON = "L9_MEMORY_AGENT_GRANTS_JSON"
ENV_AGENT_ID = "L9_MEMORY_AGENT_ID"
ENV_HUMAN_DOOR_SECRET = "L9_MEMORY_HUMAN_DOOR_SECRET"


def _fallback_mint_assertion(
    agent_id: str,
    signing_key: str | bytes,
    *,
    ttl_seconds: int = 3600,
) -> str:
    """Mint for a runtime without ``l9-graphite-memory>=2.4.0`` importable.

    Same wire format as the package, so a token minted here still verifies at
    the package server: the payload is ``agent_id|exp|nonce`` and the token is
    ``agent_id.exp.nonce.hexsig``. A fallback that signed a different payload
    would mint tokens the server can only reject.
    """
    if not agent_id or _TOKEN_SEP in agent_id:
        raise ValueError(f"agent_id must be non-empty and must not contain '.': {agent_id!r}")
    exp = int(time.time()) + int(ttl_seconds)
    nonce = secrets.token_hex(16)
    payload = f"{agent_id}{_PAYLOAD_SEP}{exp}{_PAYLOAD_SEP}{nonce}"
    key = signing_key.encode("utf-8") if isinstance(signing_key, str) else signing_key
    sig = hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{agent_id}{_TOKEN_SEP}{exp}{_TOKEN_SEP}{nonce}{_TOKEN_SEP}{sig}"


try:
    from l9_graphite_memory.authz.signed_assertion import mint_assertion
except ImportError:  # unbound runtime: same wire format, verified by the same server
    mint_assertion = _fallback_mint_assertion


def _refuse_human(agent_id: str) -> None:
    if agent_id == HUMAN_PRINCIPAL or "HUMAN" in agent_id.upper():
        raise ValueError("refusing to mint agent MCP env for human private entrance")


def load_grants_file(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "grants" in data:
        return data["grants"]
    return data


def own_grant(grants: Mapping[str, Any], agent_id: str) -> dict[str, Any]:
    """The launching principal's grant entry, and nothing else.

    Fails closed on a missing or empty entry: the package server refuses an
    agent without grants, so minting an environment for it would only defer
    the same refusal to launch time.
    """
    entry = grants.get(agent_id) if isinstance(grants, Mapping) else None
    if not isinstance(entry, dict) or not entry:
        raise KeyError(f"no grants for agent_id={agent_id}")
    return dict(entry)


def build_agent_mcp_env(
    *,
    agent_id: str,
    agents_door_secret: str,
    signing_key: str,
    grants: Mapping[str, Any],
    ttl_seconds: int = 3600,
) -> dict[str, str]:
    """Env block for ONE agent MCP server process (never includes human secret).

    ``grants`` may be the whole registry-rendered map; only ``grants[agent_id]``
    is exported. The signing-key map exported is ``{agent_id: signing_key}``.
    """
    _refuse_human(agent_id)
    grant = own_grant(grants, agent_id)
    assertion = mint_assertion(agent_id, signing_key, ttl_seconds=ttl_seconds)
    return {
        ENV_AGENTS_DOOR_SECRET: agents_door_secret,
        ENV_AGENT_ASSERTION: assertion,
        ENV_AGENT_SIGNING_KEYS_JSON: json.dumps({agent_id: signing_key}),
        ENV_AGENT_GRANTS_JSON: json.dumps({agent_id: grant}),
        ENV_AGENT_ID: agent_id,
    }


def env_from_local_secret_map(
    agent_id: str,
    secret_map_path: Path,
    grants_path: Path,
    *,
    ttl_seconds: int = 3600,
) -> dict[str, str]:
    """Read the local secret store and export only ``agent_id``'s material.

    The store holds every agent's signing key plus both door secrets; this
    function is the boundary that keeps peers' keys, peers' grants, and the
    human door out of an agent launch context.
    """
    _refuse_human(agent_id)
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
        ttl_seconds=ttl_seconds,
    )

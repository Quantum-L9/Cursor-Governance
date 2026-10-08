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
ENV_IDENTITY_ASSERTION_JSON = "L9_MEMORY_IDENTITY_ASSERTION_JSON"
ENV_IDENTITY_ASSERTION_HMAC = "L9_MEMORY_IDENTITY_ASSERTION_HMAC"


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


def local_assertion_digest(assertion: Mapping[str, Any]) -> str:
    """Local interop digest shared with l9-graphiti-memory. Not global L9 law.

    Copy the object, drop ``assertion_digest``, and hash UTF-8 JSON with
    sorted keys, compact separators, and ``ensure_ascii=False``. Prefix
    ``sha256:``.
    """

    body = {key: value for key, value in assertion.items() if key != "assertion_digest"}
    payload = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def identity_assertion_hmac(assertion_digest: str, signing_key: str | bytes) -> str:
    """HMAC-SHA256 of the ASCII assertion digest under the per-agent signing key.

    Transport integrity only. It grants no role or namespace.
    """

    key = signing_key.encode("utf-8") if isinstance(signing_key, str) else signing_key
    return hmac.new(key, assertion_digest.encode("ascii"), hashlib.sha256).hexdigest()


def seal_identity_assertion(assertion: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy of *assertion* with ``assertion_digest`` recomputed."""

    sealed = {key: value for key, value in assertion.items() if key != "assertion_digest"}
    sealed["assertion_digest"] = local_assertion_digest(sealed)
    return sealed


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
    identity_assertion: Mapping[str, Any],
    ttl_seconds: int = 3600,
) -> dict[str, str]:
    """Env block for ONE agent MCP server process (never includes human secret).

    ``grants`` may be the whole registry-rendered map; only ``grants[agent_id]``
    is exported. The signing-key map exported is ``{agent_id: signing_key}``.
    The authentication token wire format is unchanged. The canonical identity
    assertion and its HMAC travel beside it and grant nothing.
    """
    _refuse_human(agent_id)
    grant = own_grant(grants, agent_id)
    assertion = mint_assertion(agent_id, signing_key, ttl_seconds=ttl_seconds)
    sealed = seal_identity_assertion(identity_assertion)
    digest = str(sealed["assertion_digest"])
    return {
        ENV_AGENTS_DOOR_SECRET: agents_door_secret,
        ENV_AGENT_ASSERTION: assertion,
        ENV_AGENT_SIGNING_KEYS_JSON: json.dumps({agent_id: signing_key}),
        ENV_AGENT_GRANTS_JSON: json.dumps({agent_id: grant}),
        ENV_AGENT_ID: agent_id,
        ENV_IDENTITY_ASSERTION_JSON: json.dumps(
            sealed, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ),
        ENV_IDENTITY_ASSERTION_HMAC: identity_assertion_hmac(digest, signing_key),
    }


def env_from_local_secret_map(
    agent_id: str,
    secret_map_path: Path,
    grants_path: Path,
    identity_assertion: Mapping[str, Any],
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
        identity_assertion=identity_assertion,
        ttl_seconds=ttl_seconds,
    )

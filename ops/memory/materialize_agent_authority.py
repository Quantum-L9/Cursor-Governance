#!/usr/bin/env python3
"""Materialize ONE agent's signed memory authority for ONE MCP server process.

The environment supplies ``L9_MEMORY_AGENT_AUTHORITY_JSON`` — the shared agents
door and that agent's signing key, nothing else — and the MCP launcher
(``ops/memory/run_memory_mcp.sh``) pipes it here. This helper accepts only
those scoped fields, derives the agent's grants from the canonical registry
(``environment/agents/agent_registry.yaml`` via ``render_principals``) — never
from the secret, so grants stay reviewed repository policy — and writes both
maps into an already-private runtime directory. ``export_agent_assertion_env.sh``
then mints the signed assertion from them, so every memory the server admits
carries this agent as its author (ADR-0031).

It never prints authority values and refuses the human door. Same scoping rules
as the Manus connector's materializer, parameterized by agent id.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

import yaml

MIN_SECRET = 24


class AuthorityMaterializationError(ValueError):
    """The supplied authority is not scoped to exactly this agent."""


def _write_private_json(path: Path, payload: dict[str, Any]) -> None:
    encoded = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
        os.chmod(path, 0o600)
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def scoped_tokens(raw: object, agent_id: str) -> dict[str, object]:
    """Accept only {agents_door_secret, agent_signing_keys: {<agent_id>: key}}."""
    if not isinstance(raw, dict):
        raise AuthorityMaterializationError("agent authority must be a JSON object")
    if "human_door_secret" in raw:
        raise AuthorityMaterializationError("the human memory door is forbidden here")
    if set(raw) != {"agents_door_secret", "agent_signing_keys"}:
        raise AuthorityMaterializationError(
            "agent authority must contain only agents_door_secret and agent_signing_keys"
        )
    door = raw.get("agents_door_secret")
    keys = raw.get("agent_signing_keys")
    if not isinstance(door, str) or len(door) < MIN_SECRET:
        raise AuthorityMaterializationError("agents door is absent or too short")
    if not isinstance(keys, dict) or set(keys) != {agent_id}:
        raise AuthorityMaterializationError(
            f"agent authority must contain only the {agent_id} signing key"
        )
    key = keys.get(agent_id)
    if not isinstance(key, str) or len(key) < MIN_SECRET or key == door:
        raise AuthorityMaterializationError(
            f"{agent_id} signing key is absent, too short, or reused"
        )
    return {"agents_door_secret": door, "agent_signing_keys": {agent_id: key}}


def agent_grants(governance: Path, agent_id: str) -> dict[str, object]:
    """The agent's grants, rendered from the canonical registry (never the secret)."""
    registry_path = governance / "environment" / "agents" / "agent_registry.yaml"
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    if not isinstance(registry, dict):
        raise AuthorityMaterializationError("agent registry must be an object")
    agents = registry.get("agents")
    roles = registry.get("roles")
    if not isinstance(agents, dict) or not isinstance(roles, dict):
        raise AuthorityMaterializationError("agent registry is missing agents or roles")
    agent = agents.get(agent_id)
    if not isinstance(agent, dict) or agent.get("status") != "active":
        raise AuthorityMaterializationError(f"an active {agent_id} registry entry is required")
    role_definition = roles.get(agent.get("role"))
    if not isinstance(role_definition, dict):
        raise AuthorityMaterializationError(f"{agent_id} role definition is required")

    if str(governance) not in sys.path:
        sys.path.insert(0, str(governance))
    from environment.agents.tools.render_principals import build_principal  # noqa: PLC0415

    principal = build_principal(
        agent,
        role_definition,
        tenant="l9",
        organization="quantum-l9",
        workspace=str(registry.get("workspace_group", "igor-workspace")),
    )
    return {"grants": {agent_id: principal}}


def materialize(governance: Path, output_directory: Path, authority: object, agent_id: str) -> None:
    governance = governance.resolve()
    if not (governance / "CANONICAL_LAW.md").is_file():
        raise AuthorityMaterializationError("governance root is invalid")
    output_directory = output_directory.resolve()
    if not output_directory.is_dir() or stat.S_IMODE(output_directory.stat().st_mode) != 0o700:
        raise AuthorityMaterializationError("runtime authority directory must be mode 0700")
    tokens = scoped_tokens(authority, agent_id)
    grants = agent_grants(governance, agent_id)
    _write_private_json(output_directory / "agent_tokens.local.json", tokens)
    try:
        _write_private_json(output_directory / "agent_grants.json", grants)
    except BaseException:
        (output_directory / "agent_tokens.local.json").unlink(missing_ok=True)
        raise


def export_authority(secret_map: Path, agent_id: str, output: Path) -> None:
    """Write the scoped authority for ``agent_id`` from a full local token map.

    For the operator provisioning a hosted environment: the result is exactly
    what L9_MEMORY_AGENT_AUTHORITY_JSON must hold — the shared agents door and
    this agent's key, never a peer's key, never the human door — written to a
    new 0600 file. Values are never printed.
    """
    full = json.loads(secret_map.read_text(encoding="utf-8"))
    if not isinstance(full, dict):
        raise AuthorityMaterializationError("secret map must be a JSON object")
    keys = full.get("agent_signing_keys") or {}
    if not isinstance(keys, dict) or agent_id not in keys:
        raise AuthorityMaterializationError(f"secret map has no {agent_id} signing key")
    scoped = scoped_tokens(
        {
            "agents_door_secret": full.get("agents_door_secret"),
            "agent_signing_keys": {agent_id: keys[agent_id]},
        },
        agent_id,
    )
    _write_private_json(output, scoped)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-id", required=True)
    parser.add_argument("--governance", type=Path)
    parser.add_argument("--output-directory", type=Path)
    parser.add_argument(
        "--export-from",
        type=Path,
        help="operator: a full local token map (agent_tokens.local.json) to scope",
    )
    parser.add_argument("--output", type=Path, help="operator: new 0600 file for --export-from")
    args = parser.parse_args(argv)
    try:
        if args.export_from is not None:
            if args.output is None:
                raise AuthorityMaterializationError("--export-from needs --output")
            export_authority(args.export_from, args.agent_id, args.output)
            print(f"wrote scoped {args.agent_id} authority to {args.output} (0600, values hidden)")
            return 0
        if args.governance is None or args.output_directory is None:
            raise AuthorityMaterializationError("--governance and --output-directory are required")
        authority = json.load(sys.stdin)
        materialize(args.governance, args.output_directory, authority, args.agent_id)
    except (AuthorityMaterializationError, json.JSONDecodeError, OSError, yaml.YAMLError) as exc:
        print(f"agent-memory-authority ERROR ({args.agent_id}): {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

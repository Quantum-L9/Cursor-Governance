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


def allowed_peers(agent_id: str) -> frozenset[str]:
    """Identities whose keys may travel in ``agent_id``'s secret: only its own."""
    return frozenset({agent_id})


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
    """Accept {agents_door_secret, agent_signing_keys}; keep only ``agent_id``'s key."""
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
    if (
        not isinstance(keys, dict)
        or agent_id not in keys
        or not set(keys) <= allowed_peers(agent_id)
    ):
        allowed = ", ".join(sorted(allowed_peers(agent_id)))
        raise AuthorityMaterializationError(
            f"agent authority must hold the {agent_id} signing key and no key beyond {allowed}"
        )
    for peer, peer_key in keys.items():
        if not isinstance(peer_key, str) or len(peer_key) < MIN_SECRET or peer_key == door:
            raise AuthorityMaterializationError(
                f"{peer} signing key is absent, too short, or reused"
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


def export_authority(secret_map: Path, agent_ids: list[str], output: Path) -> None:
    """Write the scoped authority for ``agent_ids`` from a full local token map.

    For the operator provisioning a hosted environment: the result is exactly
    what L9_MEMORY_AGENT_AUTHORITY_JSON must hold — the shared agents door and
    this agent's key, never a peer's key, never the human door — written to a
    new 0600 file. Values are never printed.
    """
    full = json.loads(secret_map.read_text(encoding="utf-8"))
    if not isinstance(full, dict):
        raise AuthorityMaterializationError("secret map must be a JSON object")
    keys = full.get("agent_signing_keys") or {}
    missing = [a for a in agent_ids if not isinstance(keys, dict) or a not in keys]
    if missing:
        raise AuthorityMaterializationError(f"secret map has no signing key for {missing}")
    selected = {a: keys[a] for a in agent_ids}
    for agent_id in agent_ids:  # each must be a legal travelling set for every member
        scoped_tokens(
            {"agents_door_secret": full.get("agents_door_secret"), "agent_signing_keys": selected},
            agent_id,
        )
    _write_private_json(
        output,
        {"agents_door_secret": full.get("agents_door_secret"), "agent_signing_keys": selected},
    )


def add_missing_keys(secret_map: Path, agent_ids: list[str]) -> list[str]:
    """Give each named identity a signing key in the local map if it has none.

    For the operator adding a new identity on a workstation (e.g.
    claude-code-desktop after the one "claude-code" identity was split, or manus).
    Hosted containers need no operator step: see ``provision_local``. Existing keys are never
    replaced, the file stays 0600, and no value is printed. Returns the ids added.
    """
    import secrets  # noqa: PLC0415

    full = json.loads(secret_map.read_text(encoding="utf-8"))
    if not isinstance(full, dict) or not isinstance(full.get("agent_signing_keys"), dict):
        raise AuthorityMaterializationError("secret map must hold an agent_signing_keys object")
    keys = full["agent_signing_keys"]
    added = [a for a in agent_ids if a not in keys]
    for agent_id in added:
        keys[agent_id] = secrets.token_hex(32)
    if added:
        temporary = secret_map.with_name(secret_map.name + ".tmp")
        temporary.unlink(missing_ok=True)
        _write_private_json(temporary, full)
        os.replace(temporary, secret_map)
    return added


#: The container-local maps the launcher's exporter reads when the environment
#: carries no L9_MEMORY_AGENT_AUTHORITY_JSON (export_agent_assertion_env.sh).
LOCAL_DIR = Path.home() / ".config" / "l9-memory"


def hosted_identities() -> list[str]:
    """The identities a hosted (cloud) Claude Code container can run as.

    Derived from the one resolver's REMOTE_ENTRYPOINTS, never listed here, so a
    new hosted surface is provisioned the moment the resolver knows it.
    """
    from ops.memory.agent_identity import REMOTE_ENTRYPOINTS  # noqa: PLC0415

    return sorted(set(REMOTE_ENTRYPOINTS.values()))


def _replace_private_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.unlink(missing_ok=True)
    _write_private_json(temporary, payload)
    os.replace(temporary, path)


def provision_local(governance: Path, directory: Path, agent_ids: list[str]) -> list[str]:
    """Container-local signed authority for ``agent_ids``; returns the ids newly keyed.

    The package server verifies the agent's assertion against the door and
    signing keys handed to that same process (l9_graphite_memory/server.py), so a
    key minted inside a hosted container is exactly as valid as one exported from
    a workstation — and it never has to pass through the account environment
    variables field, which is plaintext and model-readable (and, by its own
    contract, carries no credentials).

    Additive and idempotent: an existing door or key is never replaced; grants
    are (re)rendered from the registry for ``agent_ids`` only, keeping any other
    entry. Directory 0700, files 0600, values never printed.
    """
    if not agent_ids:
        raise AuthorityMaterializationError("no identity to provision")
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    # Created private, never loosened or silently tightened: a directory that
    # is already more open than 0700 is refused, as materialize() refuses one.
    if stat.S_IMODE(directory.stat().st_mode) != 0o700:
        raise AuthorityMaterializationError(f"{directory} must be mode 0700")
    tokens = directory / "agent_tokens.local.json"
    if not tokens.exists():
        import secrets  # noqa: PLC0415

        _write_private_json(
            tokens, {"agents_door_secret": secrets.token_hex(32), "agent_signing_keys": {}}
        )
    added = add_missing_keys(tokens, agent_ids)
    grants_path = directory / "agent_grants.json"
    try:
        current = json.loads(grants_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        current = {}
    grants = current.get("grants") if isinstance(current, dict) else None
    if not isinstance(grants, dict):
        grants = {}
    for agent_id in agent_ids:
        grants.update(agent_grants(governance, agent_id)["grants"])
    _replace_private_json(grants_path, {**current, "grants": grants})
    return added


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--agent-id",
        action="append",
        default=[],
        help="the running identity; repeat with --export-from for a shared hosted environment",
    )
    parser.add_argument("--governance", type=Path)
    parser.add_argument("--output-directory", type=Path)
    parser.add_argument(
        "--export-from",
        type=Path,
        help="operator: a full local token map (agent_tokens.local.json) to scope",
    )
    parser.add_argument("--output", type=Path, help="operator: new 0600 file for --export-from")
    parser.add_argument(
        "--provision-hosted",
        action="store_true",
        help=(
            "hosted container: mint container-local authority for the hosted identities "
            "(or each --agent-id) into --config-dir; nothing is pasted anywhere"
        ),
    )
    parser.add_argument("--config-dir", type=Path, default=LOCAL_DIR)
    parser.add_argument(
        "--add-keys-to",
        type=Path,
        help="operator: add a signing key for each --agent-id missing from this local map",
    )
    args = parser.parse_args(argv)
    try:
        if args.provision_hosted:
            if args.governance is None:
                raise AuthorityMaterializationError("--provision-hosted needs --governance")
            ids = args.agent_id or hosted_identities()
            added = provision_local(args.governance.resolve(), args.config_dir, ids)
            print(
                f"hosted memory authority for {', '.join(ids)} in {args.config_dir} "
                f"(new keys: {', '.join(added) or 'none, all present'}; values hidden)"
            )
            return 0
        if not args.agent_id:
            raise AuthorityMaterializationError("--agent-id is required")
        if args.add_keys_to is not None:
            added = add_missing_keys(args.add_keys_to, args.agent_id)
            print(
                f"added signing keys for {', '.join(added) or 'none (all present)'} (values hidden)"
            )
            return 0
        if args.export_from is not None:
            if args.output is None:
                raise AuthorityMaterializationError("--export-from needs --output")
            export_authority(args.export_from, args.agent_id, args.output)
            names = ", ".join(args.agent_id)
            print(f"wrote scoped {names} authority to {args.output} (0600, values hidden)")
            return 0
        if args.governance is None or args.output_directory is None:
            raise AuthorityMaterializationError("--governance and --output-directory are required")
        if len(args.agent_id) != 1:
            raise AuthorityMaterializationError("materialize takes exactly one --agent-id")
        authority = json.load(sys.stdin)
        materialize(args.governance, args.output_directory, authority, args.agent_id[0])
    except (AuthorityMaterializationError, json.JSONDecodeError, OSError, yaml.YAMLError) as exc:
        print(f"agent-memory-authority ERROR ({', '.join(args.agent_id)}): {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

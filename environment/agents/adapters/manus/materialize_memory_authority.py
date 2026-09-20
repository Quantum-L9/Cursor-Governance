#!/usr/bin/env python3
"""Materialize one connector-scoped Manus memory authority for one child process.

The connector provides a JSON map through stdin.  This helper accepts only the
shared agents door and the Manus signing key, derives a public Manus-only grant
from the canonical registry, and writes both maps under an already private
runtime directory.  It never prints authority values or exports a human door.
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


class AuthorityMaterializationError(ValueError):
    """Raised when connector-provided authority is not scoped to Manus."""


def _mode_is_private(path: Path, expected: int) -> bool:
    return stat.S_IMODE(path.stat().st_mode) == expected


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


def scoped_tokens(raw: object) -> dict[str, object]:
    if not isinstance(raw, dict):
        raise AuthorityMaterializationError("connector authority must be a JSON object")
    if "human_door_secret" in raw:
        raise AuthorityMaterializationError("human memory door is forbidden")
    if set(raw) != {"agents_door_secret", "agent_signing_keys"}:
        raise AuthorityMaterializationError(
            "connector authority must contain only scoped agent fields"
        )
    door = raw.get("agents_door_secret")
    keys = raw.get("agent_signing_keys")
    if not isinstance(door, str) or len(door) < 24:
        raise AuthorityMaterializationError("agents door is absent or too short")
    if not isinstance(keys, dict) or set(keys) != {"manus"}:
        raise AuthorityMaterializationError(
            "connector authority must contain only the Manus signing key"
        )
    manus_key = keys.get("manus")
    if not isinstance(manus_key, str) or len(manus_key) < 24 or manus_key == door:
        raise AuthorityMaterializationError("Manus signing key is absent, too short, or reused")
    return {"agents_door_secret": door, "agent_signing_keys": {"manus": manus_key}}


def _manus_grants(governance: Path) -> dict[str, object]:
    registry_path = governance / "environment" / "agents" / "agent_registry.yaml"
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    if not isinstance(registry, dict):
        raise AuthorityMaterializationError("agent registry must be an object")
    agents = registry.get("agents")
    roles = registry.get("roles")
    if not isinstance(agents, dict) or not isinstance(roles, dict):
        raise AuthorityMaterializationError("agent registry is missing agents or roles")
    manus = agents.get("manus")
    if not isinstance(manus, dict) or manus.get("status") != "active":
        raise AuthorityMaterializationError("active Manus registry entry is required")
    role = manus.get("role")
    role_definition = roles.get(role)
    if not isinstance(role_definition, dict):
        raise AuthorityMaterializationError("Manus role definition is required")

    sys.path.insert(0, str(governance))
    from environment.agents.tools.render_principals import build_principal

    principal = build_principal(
        manus,
        role_definition,
        tenant="l9",
        organization="quantum-l9",
        workspace=str(registry.get("workspace_group", "igor-workspace")),
    )
    return {"grants": {"manus": principal}}


def materialize(governance: Path, output_directory: Path, authority: object) -> None:
    governance = governance.resolve()
    if not (governance / "CANONICAL_LAW.md").is_file():
        raise AuthorityMaterializationError("governance root is invalid")
    output_directory = output_directory.resolve()
    if not output_directory.is_dir() or not _mode_is_private(output_directory, 0o700):
        raise AuthorityMaterializationError("runtime authority directory must be mode 0700")
    tokens = scoped_tokens(authority)
    grants = _manus_grants(governance)
    _write_private_json(output_directory / "agent_tokens.local.json", tokens)
    try:
        _write_private_json(output_directory / "agent_grants.json", grants)
    except BaseException:
        (output_directory / "agent_tokens.local.json").unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--governance", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        authority = json.load(sys.stdin)
        materialize(args.governance, args.output_directory, authority)
    except (AuthorityMaterializationError, json.JSONDecodeError, OSError, yaml.YAMLError) as exc:
        print(f"manus-memory-authority ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

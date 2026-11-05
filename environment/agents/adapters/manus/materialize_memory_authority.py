#!/usr/bin/env python3
"""Retired Manus credential materializer; pure grant inspection is assurance only.

No production Memory 3.0 credential artifact may be created by this adapter.
The retained pure helper validates an operating v2 binding and delegates full
canonical assurance before deriving secret-free historical grant information.
That information is not native OAuth authorization or service-side admission.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

MANUS_ACTOR_REF = "l9.actor-registry/global@1#manus"
MANUS_SURFACE_REF = "l9.surface-registry/global@1#manus-cloud"
RETIRED_REASON = (
    "UPSTREAM_BLOCKED: stdio/HMAC authority materialization retired; native Manus client UNBOUND"
)


class AuthorityMaterializationError(ValueError):
    """Credential materialization is retired or canonical assurance failed."""


def scoped_tokens(raw: object) -> dict[str, object]:
    del raw
    raise AuthorityMaterializationError(RETIRED_REASON)


def _manus_grants(governance: Path) -> dict[str, object]:
    """Pure secret-free legacy grant inspection, never a credential path."""
    try:
        registry = yaml.safe_load(
            (governance / "environment/agents/agent_registry.yaml").read_text(encoding="utf-8")
        )
        if (
            not isinstance(registry, dict)
            or registry.get("schema") != "l9.cursor-governance.agent-bindings/v2"
        ):
            raise AuthorityMaterializationError("exact v2 operating binding schema is required")
        agents, roles = registry.get("agents"), registry.get("roles")
        if not isinstance(agents, dict) or not isinstance(roles, dict):
            raise AuthorityMaterializationError("agent registry is missing agents or roles")
        manus = agents.get("manus")
        if not isinstance(manus, dict) or manus.get("binding_status") != "active":
            raise AuthorityMaterializationError("binding_status must be exactly active")
        if {"agent_id", "source", "status"}.intersection(manus):
            raise AuthorityMaterializationError(
                "legacy agent_id/source/status overrides are forbidden"
            )
        saved = list(sys.path)
        try:
            source_root = Path(__file__).resolve().parents[4]
            sys.path.insert(0, str(source_root))
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from validate_manus_adapter import canonical_identity_errors

            from ops.memory.agent_identity import actor_ref_from_binding

            if actor_ref_from_binding("manus", manus) != MANUS_ACTOR_REF:
                raise AuthorityMaterializationError("actor_ref must name exact canonical Manus")
            if manus.get("surface_refs") != [MANUS_SURFACE_REF]:
                raise AuthorityMaterializationError("surface_refs must name current manus-cloud")
            failures = canonical_identity_errors(governance)
            if failures:
                raise AuthorityMaterializationError("; ".join(failures))
            role = manus.get("role")
            role_definition = roles.get(role)
            if not isinstance(role_definition, dict):
                raise AuthorityMaterializationError("Manus role definition is required")
            groups = manus.get("assigned_groups")
            if (
                not isinstance(groups, list)
                or not groups
                or any(not isinstance(group, str) or not group for group in groups)
            ):
                raise AuthorityMaterializationError(
                    "non-empty assigned namespace scope is required"
                )
            from environment.agents.tools.render_principals import build_principal
            from ops.memory.materialize_agent_authority import signed_door_grant

            principal = build_principal(
                dict(manus, agent_id="manus"),
                role_definition,
                tenant="l9",
                organization="quantum-l9",
                workspace=str(registry.get("workspace_group", "igor-workspace")),
            )
            return {"grants": {"manus": signed_door_grant(principal)}}
        finally:
            sys.path[:] = saved
    except (ImportError, OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as exc:
        raise AuthorityMaterializationError(str(exc)) from exc


def materialize(governance: Path, output_directory: Path, authority: object) -> None:
    """Refuse before filesystem resolution, authority inspection or output."""
    del governance, output_directory, authority
    raise AuthorityMaterializationError(RETIRED_REASON)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--governance", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.parse_args(argv)
    # stdin can contain stale authority: never read it, even for validation.
    print("manus-memory-authority " + RETIRED_REASON, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

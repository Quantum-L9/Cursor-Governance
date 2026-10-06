from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from environment.agents.tools.validate_agents import (
    FORBIDDEN_LOCAL_IDENTITY_FIELDS,
    Validator,
    derive_actor_id,
)
from tools.authority.project_canonical_identity import (
    ACTOR_ARTIFACT,
    ACTOR_PREFIX,
    PROFILE_REF,
    SURFACE_ARTIFACT,
    SURFACE_PREFIX,
    ProjectionError,
    _requested_identities,
    project,
)


def bindings() -> dict[str, Any]:
    return {
        "schema": "l9.cursor-governance.agent-bindings/v2",
        "agents": {
            "cursor": {
                "actor_ref": f"{ACTOR_PREFIX}cursor",
                "surface_refs": [
                    f"{SURFACE_PREFIX}cursor-ide",
                ],
            },
            "claude-code": {
                "actor_ref": f"{ACTOR_PREFIX}claude-code",
                "surface_refs": [
                    f"{SURFACE_PREFIX}claude-code-cli",
                    f"{SURFACE_PREFIX}claude-code-web",
                ],
            },
        },
    }


def actor_registry() -> dict[str, Any]:
    return {
        "schema": "l9.actor-registry/v1",
        "artifact_id": ACTOR_ARTIFACT,
        "canonical": True,
        "actors": [
            {
                "id": "cursor",
                "kind": "agent",
                "status": "current",
                "description": "The Cursor agent actor.",
            },
            {
                "id": "claude-code",
                "kind": "agent",
                "status": "current",
                "description": "The Claude Code actor.",
            },
        ],
        "aliases": [
            {
                "alias": "claude-code-desktop",
                "canonical": "claude-code",
                "alias_kind": "historical_actor_alias",
            },
        ],
    }


def surface_registry() -> dict[str, Any]:
    return {
        "schema": "l9.surface-registry/v1",
        "artifact_id": SURFACE_ARTIFACT,
        "canonical": True,
        "surfaces": [
            {
                "id": "cursor-ide",
                "status": "current",
                "description": "Cursor IDE",
            },
            {
                "id": "claude-code-cli",
                "status": "current",
                "description": "Claude CLI",
            },
            {
                "id": "claude-code-web",
                "status": "current",
                "description": "Claude Web",
            },
        ],
        "aliases": [
            {
                "alias": "claude-cli",
                "canonical": "claude-code-cli",
                "alias_kind": "historical_surface_alias",
            },
        ],
    }


def test_binding_requests_canonical_coordinates_only() -> None:
    actors, surfaces = _requested_identities(bindings())
    assert actors == {
        "cursor",
        "claude-code",
    }
    assert surfaces == {
        "cursor-ide",
        "claude-code-cli",
        "claude-code-web",
    }


def test_projection_contains_only_requested_canonical_identities() -> None:
    actors, surfaces = _requested_identities(bindings())
    result = project(
        actor_registry=actor_registry(),
        surface_registry=surface_registry(),
        actor_ids=actors,
        surface_ids=surfaces,
        source_revision="a" * 40,
        actor_digest="sha256:" + ("1" * 64),
        surface_digest="sha256:" + ("2" * 64),
        profile_digest="sha256:" + ("3" * 64),
    )
    assert result["canonical"] is False
    assert result["authority"]["authority_class"] == "derived"
    assert {item["id"] for item in result["actors"]} == {
        "cursor",
        "claude-code",
    }
    assert {item["id"] for item in result["surfaces"]} == {
        "cursor-ide",
        "claude-code-cli",
        "claude-code-web",
    }


def test_projection_preserves_relevant_aliases() -> None:
    actors, surfaces = _requested_identities(bindings())
    result = project(
        actor_registry=actor_registry(),
        surface_registry=surface_registry(),
        actor_ids=actors,
        surface_ids=surfaces,
        source_revision="a" * 40,
        actor_digest="sha256:" + ("1" * 64),
        surface_digest="sha256:" + ("2" * 64),
        profile_digest="sha256:" + ("3" * 64),
    )
    assert result["actor_aliases"] == [
        {
            "alias": "claude-code-desktop",
            "canonical": "claude-code",
            "alias_kind": "historical_actor_alias",
        }
    ]
    assert result["surface_aliases"] == [
        {
            "alias": "claude-cli",
            "canonical": "claude-code-cli",
            "alias_kind": "historical_surface_alias",
        }
    ]


def test_unknown_actor_fails_closed() -> None:
    document = bindings()
    document["agents"]["cursor"]["actor_ref"] = f"{ACTOR_PREFIX}not-a-real-actor"
    actors, surfaces = _requested_identities(document)
    with pytest.raises(
        ProjectionError,
        match="unresolved canonical actor identities",
    ):
        project(
            actor_registry=actor_registry(),
            surface_registry=surface_registry(),
            actor_ids=actors,
            surface_ids=surfaces,
            source_revision="a" * 40,
            actor_digest="sha256:" + ("1" * 64),
            surface_digest="sha256:" + ("2" * 64),
            profile_digest="sha256:" + ("3" * 64),
        )


def test_alias_cannot_be_used_as_canonical_surface_ref() -> None:
    document = bindings()
    document["agents"]["claude-code"]["surface_refs"] = [f"{SURFACE_PREFIX}claude-cli"]
    actors, surfaces = _requested_identities(document)
    with pytest.raises(
        ProjectionError,
        match="unresolved canonical surface identities",
    ):
        project(
            actor_registry=actor_registry(),
            surface_registry=surface_registry(),
            actor_ids=actors,
            surface_ids=surfaces,
            source_revision="a" * 40,
            actor_digest="sha256:" + ("1" * 64),
            surface_digest="sha256:" + ("2" * 64),
            profile_digest="sha256:" + ("3" * 64),
        )


def test_projection_profile_coordinate_is_stable() -> None:
    assert PROFILE_REF == "l9.projection/cursor-governance-identity@1"


# ---------------------------------------------------------------------------
# agent-bindings/v2 operating-plane validator seam (validate_agents.py)
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
ADAPTERS_MK = REPO_ROOT / "ops" / "make" / "adapters.mk"
PLACEHOLDER = "UNGENERATED"


def v2_registry() -> dict[str, Any]:
    """A complete v2 bindings registry around the shared canonical fixtures."""
    document = bindings()
    document["identity_authority"] = {
        "projection_ref": PROFILE_REF,
        "projection_path": "generated/governance/canonical_identity.yaml",
    }
    document["roles"] = {
        "orchestrator": {"write_namespaces": ["*"]},
        "implementer": {"write_namespaces": []},
    }
    document["agents"]["cursor"].update(
        {
            "user_id": "cursor_agent",
            "principal_id": "cursor-memory-client",
            "token_env": "L9_MEMORY_TOKEN__CURSOR",
            "role": "orchestrator",
            "assigned_groups": ["*"],
            "adapter": "cursor",
            "binding_status": "active",
        }
    )
    document["agents"]["claude-code"].update(
        {
            "user_id": "claude_code_agent",
            "principal_id": "claude-code-memory-client",
            "token_env": "L9_MEMORY_TOKEN__CLAUDE_CODE",
            "role": "implementer",
            "assigned_groups": ["cursor-governance"],
            "adapter": "claude-code",
            "binding_status": "active",
        }
    )
    document["memory"] = {
        "identity_env": {
            "user_id": "USER_ID",
            "agent_id": "L9_MEMORY_AGENT_ID",
            "source": "L9_MEMORY_SOURCE",
        }
    }
    document["forbidden_local_identity_fields"] = sorted(FORBIDDEN_LOCAL_IDENTITY_FIELDS)
    return document


def real_projection() -> dict[str, Any]:
    """The projector's own output for the fixture registries: the validator
    resolves references against exactly this shape."""
    actors, surfaces = _requested_identities(bindings())
    return project(
        actor_registry=actor_registry(),
        surface_registry=surface_registry(),
        actor_ids=actors,
        surface_ids=surfaces,
        source_revision="a" * 40,
        actor_digest="sha256:" + ("1" * 64),
        surface_digest="sha256:" + ("2" * 64),
        profile_digest="sha256:" + ("3" * 64),
    )


def placeholder_projection() -> dict[str, Any]:
    document = real_projection()
    document["projection"]["profile_digest"] = PLACEHOLDER
    document["projection"]["source_revision"] = PLACEHOLDER
    document["actors"] = []
    document["actor_aliases"] = []
    document["surfaces"] = []
    document["surface_aliases"] = []
    return document


def validate_bindings(
    registry: dict[str, Any],
    projection: dict[str, Any] | None,
    tmp_path: Path,
) -> list[str]:
    validator = Validator(tmp_path, tmp_path / "canonical_identity.yaml")
    validator.adopt_registry(registry)
    if projection is not None:
        validator.adopt_projection(projection)
    else:
        validator.load_projection()  # file absent: must fail closed, never "empty"
    validator.check_agents()
    return validator.errors


def test_v2_bindings_are_accepted(tmp_path: Path) -> None:
    assert validate_bindings(v2_registry(), real_projection(), tmp_path) == []


def test_registry_schema_must_be_agent_bindings_v2(tmp_path: Path) -> None:
    registry = v2_registry()
    registry["schema"] = "l9.cursor-governance.agent-registry/v1"
    registry["schema_version"] = "1.0.0"
    errors = validate_bindings(registry, real_projection(), tmp_path)
    assert any(error.startswith("[R1]") and "agent-bindings/v2" in error for error in errors)


def test_local_agent_id_is_rejected(tmp_path: Path) -> None:
    registry = v2_registry()
    registry["agents"]["cursor"]["agent_id"] = "cursor"
    errors = validate_bindings(registry, real_projection(), tmp_path)
    assert any(error.startswith("[R3]") and "'agent_id'" in error for error in errors)


def test_local_source_is_rejected(tmp_path: Path) -> None:
    registry = v2_registry()
    registry["agents"]["claude-code"]["source"] = "claude-code"
    errors = validate_bindings(registry, real_projection(), tmp_path)
    assert any(error.startswith("[R3]") and "'source'" in error for error in errors)


def test_every_forbidden_local_identity_field_is_rejected(tmp_path: Path) -> None:
    for field in FORBIDDEN_LOCAL_IDENTITY_FIELDS:
        registry = v2_registry()
        registry["agents"]["cursor"][field] = "redeclared"
        errors = validate_bindings(registry, real_projection(), tmp_path)
        assert any(error.startswith("[R3]") and f"'{field}'" in error for error in errors), field


def test_unresolved_actor_ref_fails(tmp_path: Path) -> None:
    registry = v2_registry()
    registry["agents"]["cursor"]["actor_ref"] = f"{ACTOR_PREFIX}cursor"
    projection = real_projection()
    projection["actors"] = [item for item in projection["actors"] if item["id"] != "cursor"]
    errors = validate_bindings(registry, projection, tmp_path)
    assert any(error.startswith("[R8]") and "does not resolve" in error for error in errors)


def test_actor_alias_is_not_a_canonical_ref(tmp_path: Path) -> None:
    registry = v2_registry()
    registry["agents"]["claude-code"]["actor_ref"] = f"{ACTOR_PREFIX}claude-code-desktop"
    errors = validate_bindings(registry, real_projection(), tmp_path)
    assert any(error.startswith("[R8]") and "alias" in error for error in errors)


def test_unresolved_surface_ref_fails(tmp_path: Path) -> None:
    registry = v2_registry()
    registry["agents"]["claude-code"]["surface_refs"].append(f"{SURFACE_PREFIX}claude-code-mobile")
    errors = validate_bindings(registry, real_projection(), tmp_path)
    assert any(
        error.startswith("[R9]") and "claude-code-mobile" in error and "does not resolve" in error
        for error in errors
    )


def test_surface_alias_is_not_a_canonical_ref(tmp_path: Path) -> None:
    registry = v2_registry()
    registry["agents"]["claude-code"]["surface_refs"] = [f"{SURFACE_PREFIX}claude-cli"]
    errors = validate_bindings(registry, real_projection(), tmp_path)
    assert any(error.startswith("[R9]") and "alias" in error for error in errors)


def test_non_canonical_reference_shapes_fail(tmp_path: Path) -> None:
    registry = v2_registry()
    registry["agents"]["cursor"]["actor_ref"] = "cursor"
    registry["agents"]["cursor"]["surface_refs"] = ["cursor-ide"]
    errors = validate_bindings(registry, real_projection(), tmp_path)
    assert any(error.startswith("[R2]") and ACTOR_PREFIX in error for error in errors)
    assert any(error.startswith("[R9]") and SURFACE_PREFIX in error for error in errors)


def test_adapter_agent_id_and_source_derive_from_actor_ref(tmp_path: Path) -> None:
    registry = v2_registry()
    validator = Validator(tmp_path, tmp_path / "canonical_identity.yaml")
    validator.adopt_registry(registry)
    agent = registry["agents"]["claude-code"]
    assert derive_actor_id(agent["actor_ref"]) == "claude-code"
    expected = validator.expected_env(agent)
    assert expected["USER_ID"] == "claude_code_agent"
    assert expected["L9_MEMORY_AGENT_ID"] == "claude-code"
    assert expected["L9_MEMORY_SOURCE"] == "claude-code"
    assert "agent_id" not in agent and "source" not in agent


def test_adapter_env_example_must_match_derived_identity(tmp_path: Path) -> None:
    registry = v2_registry()
    validator = Validator(tmp_path, tmp_path / "canonical_identity.yaml")
    validator.adopt_registry(registry)
    agent = registry["agents"]["claude-code"]
    good = (
        "USER_ID=claude_code_agent\nL9_MEMORY_AGENT_ID=claude-code\nL9_MEMORY_SOURCE=claude-code\n"
    )
    validator.check_env_example_text("good.env.example", good, agent)
    assert validator.errors == []
    drifted = (
        "USER_ID=claude_code_agent\n"
        "L9_MEMORY_AGENT_ID=claude-code-desktop\n"
        "L9_MEMORY_SOURCE=claude\n"
    )
    validator.check_env_example_text("drift.env.example", drifted, agent)
    assert any("L9_MEMORY_AGENT_ID='claude-code-desktop'" in error for error in validator.errors)
    assert any("L9_MEMORY_SOURCE='claude'" in error for error in validator.errors)
    retired = good + "GRAPHITI_MCP_URL=https://memory.example\nGRAPHITI_MCP_TOKEN=placeholder\n"
    validator.errors.clear()
    validator.check_env_example_text("retired.env.example", retired, agent)
    assert any("GRAPHITI_MCP_URL" in error for error in validator.errors)
    assert any("GRAPHITI_MCP_TOKEN" in error for error in validator.errors)


def test_placeholder_projection_cannot_resolve_identity(tmp_path: Path) -> None:
    errors = validate_bindings(v2_registry(), placeholder_projection(), tmp_path)
    assert any(error.startswith("[R7]") and PLACEHOLDER in error for error in errors)


def test_missing_projection_is_not_treated_as_empty(tmp_path: Path) -> None:
    errors = validate_bindings(v2_registry(), None, tmp_path)
    assert any(error.startswith("[R7]") and "missing" in error for error in errors)


def test_peer_surfaces_resolve_through_surface_refs(tmp_path: Path) -> None:
    registry = v2_registry()
    validator = Validator(tmp_path, tmp_path / "canonical_identity.yaml")
    validator.adopt_registry(registry)
    validator.adopt_projection(real_projection())
    peers = {
        "peers": {
            "claude-code": {
                "agent_ref": "claude-code",
                "execution": {
                    "bindings": [
                        {"surface": "claude-code-cli"},
                        {"surface": "cursor-ide"},
                        {"surface": "claude-cli"},
                    ]
                },
            }
        }
    }
    validator.check_peer_bindings(peers)
    errors = validator.errors
    assert any("'cursor-ide' not in agents.claude-code.surface_refs" in error for error in errors)
    assert any("'claude-cli' is not a projected canonical SurfaceIdentity" in e for e in errors)
    assert not any("claude-code-cli" in error for error in errors)


def test_agents_env_gate_composes_assurance_before_validation() -> None:
    """The composed gate: projection assurance runs first, validator second,
    one Make target. A placeholder projection fails the first step, so it can
    never produce a green `make agents-env`."""
    recipe = ADAPTERS_MK.read_text(encoding="utf-8")
    target = recipe.index("\nagents-env:\n")
    body = recipe[target:].split("\n", 1)[1].split("\nide-profile:", 1)[0]
    assurance = body.index("tools/assurance/check_canonical_identity_projection.py")
    validation = body.index("environment/agents/tools/validate_agents.py")
    assert assurance < validation
    dry_run = subprocess.run(
        ["make", "-n", "agents-env"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert dry_run.returncode == 0, dry_run.stderr
    assert dry_run.stdout.index("check_canonical_identity_projection.py") < dry_run.stdout.index(
        "validate_agents.py"
    )

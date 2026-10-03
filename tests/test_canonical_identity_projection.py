from __future__ import annotations
from typing import Any
import pytest
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
    assert {
        item["id"]
        for item in result["actors"]
    } == {
        "cursor",
        "claude-code",
    }
    assert {
        item["id"]
        for item in result["surfaces"]
    } == {
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
    document["agents"]["cursor"]["actor_ref"] = (
        f"{ACTOR_PREFIX}not-a-real-actor"
    )
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
    document["agents"]["claude-code"]["surface_refs"] = [
        f"{SURFACE_PREFIX}claude-cli"
    ]
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

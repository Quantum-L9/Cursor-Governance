"""ops/memory/agent_identity.py — the memory identity is DERIVED, never configured.

Two dimensions, never mixed: the ActorIdentity (who wrote the memory) and the
SurfaceIdentity (where that actor ran). Cursor is actor ``cursor`` on surface
``cursor-ide``; Claude Code is ONE actor, ``claude-code``, on several surfaces.
A configured L9_MEMORY_AGENT_ID can never relabel a write (no drift), and a
surface that cannot be identified gets no surface rather than a guessed one.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ops.memory import agent_identity as ai

CLAUDE = {"CLAUDECODE": "1"}
MOBILE = {**CLAUDE, "CLAUDE_CODE_REMOTE": "true", "CLAUDE_CODE_ENTRYPOINT": "remote_mobile"}
WEB = {**CLAUDE, "CLAUDE_CODE_REMOTE": "true", "CLAUDE_CODE_ENTRYPOINT": "remote_web"}
REGISTRY = Path(__file__).resolve().parents[3] / "environment/agents/agent_registry.yaml"


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        ({"CURSOR_AGENT": "1"}, "cursor"),
        (CLAUDE, "claude-code"),
        ({"CLAUDE_CODE_ENTRYPOINT": "cli"}, "claude-code"),
        (MOBILE, "claude-code"),
        # an unknown surface never makes the actor unknown
        (WEB, "claude-code"),
        ({**CLAUDE, "CLAUDE_CODE_REMOTE": "true"}, "claude-code"),
        # configured values never relabel a surface that has markers
        ({"CURSOR_AGENT": "1", "L9_MEMORY_AGENT_ID": "claude-code"}, "cursor"),
        ({**CLAUDE, "L9_MEMORY_AGENT_ID": "claude-code-mobile"}, "claude-code"),
        ({**MOBILE, "L9_MEMORY_AGENT_ID": "cursor"}, "claude-code"),
        # agents with no host markers are identified by their adapter's setting
        ({"L9_MEMORY_AGENT_ID": "manus"}, "manus"),
        ({"L9_MEMORY_AGENT_ID": "codex"}, "codex"),
        # ...and only when it is an active adapter identity
        ({"L9_MEMORY_AGENT_ID": "perplexity"}, ""),
        ({"L9_MEMORY_AGENT_ID": "igorbot"}, ""),
        ({"L9_MEMORY_AGENT_ID": "agent-b"}, ""),
        ({"L9_MEMORY_AGENT_ID": "IgorBot"}, ""),
        # no guessing: a derived actor or an alias is never configured
        ({"L9_MEMORY_AGENT_ID": "claude-code"}, ""),
        ({"L9_MEMORY_AGENT_ID": "claude-code-desktop"}, ""),
        ({}, ""),
    ],
)
def test_the_identity_is_derived_from_host_markers(env: dict[str, str], expected: str) -> None:
    assert ai.resolve_agent_id(env) == expected


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        ({"CURSOR_AGENT": "1"}, "cursor-ide"),
        (CLAUDE, "claude-code-desktop"),
        ({"CLAUDE_CODE_ENTRYPOINT": "cli"}, "claude-code-cli"),
        (MOBILE, "claude-code-mobile"),
        (WEB, ""),
        ({"L9_MEMORY_AGENT_ID": "manus"}, ""),
        ({}, ""),
    ],
)
def test_the_surface_is_derived_from_host_markers(env: dict[str, str], expected: str) -> None:
    assert ai.resolve_surface_id(env) == expected


def test_a_configured_value_that_disagrees_is_reported_as_drift() -> None:
    assert ai.static_drift({**MOBILE, "L9_MEMORY_AGENT_ID": "claude-code-mobile"}) == (
        "claude-code-mobile"
    )
    assert ai.static_drift({**MOBILE, "L9_MEMORY_AGENT_ID": "claude-code"}) == ""
    assert ai.static_drift({"L9_MEMORY_AGENT_ID": "manus"}) == "", (
        "no markers: nothing to drift from"
    )


def test_an_unidentifiable_surface_says_why() -> None:
    reason = ai.surface_unresolved_reason(WEB)
    assert "remote_web" in reason and "no admitted surface" in reason
    assert ai.surface_unresolved_reason(MOBILE) == ""
    assert "no host markers" in ai.surface_unresolved_reason({})


def test_historical_actor_aliases_fold_to_the_one_claude_actor() -> None:
    assert ai.HISTORICAL_ACTOR_ALIASES == {
        "claude-code-desktop": "claude-code",
        "claude-code-mobile": "claude-code",
    }
    assert ai.canonical_actor_id("claude-code-desktop") == "claude-code"
    assert ai.canonical_actor_id(" claude-code-mobile ") == "claude-code"
    assert ai.canonical_actor_id("cursor") == "cursor"
    assert ai.canonical_actor_id(None) == ""
    assert "historical ActorIdentity alias" in ai.unresolved_reason(
        {"L9_MEMORY_AGENT_ID": "claude-code-desktop"}
    )


def test_exactly_the_two_host_actors_are_derived() -> None:
    assert ai.DERIVED_IDENTITIES == {"cursor", "claude-code"}
    assert {
        "claude-code-desktop",
        "claude-code-cli",
        "claude-code-ide",
        "claude-code-mobile",
    } == ai.CLAUDE_SURFACES


def test_the_reserved_identities_exist_unwired() -> None:
    """Perplexity, Perplexity Computer, L CTO and IgorBot are reserved identities:
    registered, planned, no adapter, never a runtime writer until wired."""
    agents = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))["agents"]
    for agent_id in ("perplexity", "perplexity-computer", "l-cto", "igorbot"):
        entry = agents[agent_id]
        assert entry["status"] == "planned", agent_id
        assert entry["adapter"] == "none", agent_id
        assert entry["role"] == "observer" and entry["assigned_groups"] == [], agent_id
        assert "planned identity" in ai.unresolved_reason({"L9_MEMORY_AGENT_ID": agent_id})
    assert agents["manus"]["status"] == "active" and agents["manus"]["adapter"] == "manus"


def test_an_unregistered_identity_says_why() -> None:
    assert "not an active adapter identity" in ai.unresolved_reason(
        {"L9_MEMORY_AGENT_ID": "agent-b"}
    )
    assert "derived from host markers" in ai.unresolved_reason(
        {"L9_MEMORY_AGENT_ID": "claude-code"}
    )


def test_registry_and_resolver_cannot_drift_apart() -> None:
    """Every derived identity is an active registry agent with the derived USER_ID,
    Claude Code is one registry row carrying every Claude surface, and no
    historical actor alias is registered as an agent."""
    agents = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))["agents"]
    assert set(agents) == set(ai.ALL_IDENTITIES), (
        "the resolver and the registry must name the same agents"
    )
    for agent_id in ai.DERIVED_IDENTITIES | ai.ADAPTER_IDENTITIES:
        assert agents[agent_id]["status"] == "active", agent_id
    for agent_id in ai.DERIVED_IDENTITIES:
        assert agents[agent_id]["user_id"] == ai.user_id_for(agent_id), agent_id
    for agent_id in ai.PLANNED_IDENTITIES:
        assert agents[agent_id]["status"] == "planned", agent_id
    claude_agents = {a for a, v in agents.items() if v.get("adapter") == "claude-code"}
    assert claude_agents == {ai.CLAUDE_ACTOR}
    assert set(agents[ai.CLAUDE_ACTOR]["surfaces"]) == ai.CLAUDE_SURFACES
    assert not set(ai.HISTORICAL_ACTOR_ALIASES) & set(agents)


# --- pinned upstream authority (validate_agents.py R7-R9) ----------------------------

ROOT = REGISTRY.parents[2]
BINDINGS = ROOT / "environment/agents/PEER_RUNTIME_BINDINGS.yaml"
UPSTREAM_ACTORS = ("cursor", "claude-code", "codex", "gemini", "manus", "human")


def _validator():
    import importlib.util  # noqa: PLC0415

    path = ROOT / "environment/agents/tools/validate_agents.py"
    spec = importlib.util.spec_from_file_location("l9_validate_agents_ratchet", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _peer_surfaces() -> list[str]:
    peers = yaml.safe_load(BINDINGS.read_text(encoding="utf-8"))["peers"]
    return sorted({b["surface"] for p in peers.values() for b in p["execution"]["bindings"]})


def _upstream(actors=UPSTREAM_ACTORS, surfaces=None) -> dict[str, bytes]:
    surfaces = _peer_surfaces() if surfaces is None else surfaces
    actor_doc = {
        "artifact_id": "l9.actor-registry/global@1",
        "actors": [{"id": a, "status": "current"} for a in actors],
    }
    surface_doc = {
        "artifact_id": "l9.surface-registry/global@1",
        "surfaces": [{"id": s, "status": "current"} for s in surfaces],
    }
    return {
        "semantics/actor_registry.yaml": yaml.safe_dump(actor_doc).encode(),
        "semantics/surface_registry.yaml": yaml.safe_dump(surface_doc).encode(),
    }


def _pinned_to(bodies: dict[str, bytes]) -> dict:
    import copy  # noqa: PLC0415
    import hashlib  # noqa: PLC0415

    reg = copy.deepcopy(yaml.safe_load(REGISTRY.read_text(encoding="utf-8")))
    for name in ("actor_registry", "surface_registry"):
        pin = reg["identity_authority"][name]
        pin["sha256"] = hashlib.sha256(bodies[pin["path"]]).hexdigest()
    return reg


def _authority_errors(reg: dict, bodies: dict[str, bytes], root: Path | None = None) -> list[str]:
    module = _validator()
    module.errors.clear()
    module.check_identity_authority(
        reg, root or REGISTRY.parent, fetch=lambda _repo, _rev, path: bodies[path]
    )
    return list(module.errors)


def test_the_registry_pins_exact_upstream_coordinates() -> None:
    authority = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))["identity_authority"]
    assert authority["repository"] == "Quantum-L9/.github"
    assert len(authority["revision"]) == 40
    assert authority["actor_registry"]["artifact_id"] == "l9.actor-registry/global@1"
    assert authority["surface_registry"]["artifact_id"] == "l9.surface-registry/global@1"


def test_active_actors_and_peer_surfaces_validate_against_the_pin() -> None:
    bodies = _upstream()
    assert _authority_errors(_pinned_to(bodies), bodies) == []


@pytest.mark.parametrize(
    "path", ["semantics/actor_registry.yaml", "semantics/surface_registry.yaml"]
)
def test_an_upstream_digest_mismatch_fails(path: str) -> None:
    bodies = _upstream()
    reg = _pinned_to(bodies)
    tampered = {**bodies, path: bodies[path] + b"# drift\n"}
    errors = _authority_errors(reg, tampered)
    assert any(e.startswith("[R7]") and path in e and "sha256" in e for e in errors), errors


def test_an_active_local_actor_missing_upstream_fails() -> None:
    bodies = _upstream(actors=[a for a in UPSTREAM_ACTORS if a != "manus"])
    errors = _authority_errors(_pinned_to(bodies), bodies)
    assert any(e.startswith("[R8]") and "agents.manus" in e for e in errors), errors


def test_a_peer_without_a_local_active_actor_fails(tmp_path: Path) -> None:
    doc = yaml.safe_load(BINDINGS.read_text(encoding="utf-8"))
    doc["peers"]["ghost"] = {**doc["peers"]["cursor"], "agent_ref": "ghost"}
    (tmp_path / "PEER_RUNTIME_BINDINGS.yaml").write_text(yaml.safe_dump(doc), encoding="utf-8")
    bodies = _upstream()
    errors = _authority_errors(_pinned_to(bodies), bodies, root=tmp_path)
    assert any(e.startswith("[R9]") and "peers.ghost" in e for e in errors), errors


def test_a_peer_surface_missing_upstream_fails() -> None:
    bodies = _upstream(surfaces=[s for s in _peer_surfaces() if s != "claude-code-ide"])
    errors = _authority_errors(_pinned_to(bodies), bodies)
    assert any(
        e.startswith("[R9]") and "'claude-code-ide'" in e and "upstream" in e for e in errors
    ), errors


def test_a_historical_actor_alias_and_the_surface_of_the_same_name_stay_distinct() -> None:
    """canonical_actor_id folds the actor alias; the SurfaceIdentity is untouched."""
    assert ai.canonical_actor_id("claude-code-desktop") == "claude-code"
    assert ai.resolve_surface_id(CLAUDE) == "claude-code-desktop"
    assert "claude-code-desktop" in ai.CLAUDE_SURFACES

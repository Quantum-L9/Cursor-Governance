"""ops/memory/agent_identity.py — the memory identity is DERIVED, never configured.

Cursor and Claude Code each have one actor, derived from markers the host sets
on the running process. Desktop and mobile are surfaces of ``claude-code``,
not authors. A configured L9_MEMORY_AGENT_ID can never relabel a write.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ops.memory import agent_identity as ai

CLAUDE = {"CLAUDECODE": "1"}
MOBILE = {**CLAUDE, "CLAUDE_CODE_REMOTE": "true", "CLAUDE_CODE_ENTRYPOINT": "remote_mobile"}
REGISTRY = Path(__file__).resolve().parents[3] / "environment/agents/agent_registry.yaml"


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        ({"CURSOR_AGENT": "1"}, "cursor"),
        (CLAUDE, "claude-code"),
        ({"CLAUDE_CODE_ENTRYPOINT": "cli"}, "claude-code"),
        (MOBILE, "claude-code"),
        # configured values never relabel a surface that has markers
        ({"CURSOR_AGENT": "1", "L9_MEMORY_AGENT_ID": "claude-code"}, "cursor"),
        ({**CLAUDE, "L9_MEMORY_AGENT_ID": "claude-code-mobile"}, "claude-code"),
        ({**MOBILE, "L9_MEMORY_AGENT_ID": "claude-code-desktop"}, "claude-code"),
        # agents with no host markers are identified by their adapter's setting
        ({"L9_MEMORY_AGENT_ID": "manus"}, "manus"),
        ({"L9_MEMORY_AGENT_ID": "codex"}, "codex"),
        ({"L9_MEMORY_AGENT_ID": "gemini"}, "gemini"),
        ({"L9_MEMORY_AGENT_ID": "perplexity"}, ""),
        ({"L9_MEMORY_AGENT_ID": "perplexity-computer"}, ""),
        ({"L9_MEMORY_AGENT_ID": "l-cto"}, ""),
        ({"L9_MEMORY_AGENT_ID": "igorbot"}, ""),
        ({"L9_MEMORY_AGENT_ID": "human"}, ""),
        ({"L9_MEMORY_AGENT_ID": "claude-code-desktop"}, ""),
        # ...and only when it is a registered identity
        ({"L9_MEMORY_AGENT_ID": "agent-b"}, ""),
        ({"L9_MEMORY_AGENT_ID": "IgorBot"}, ""),
        # no guessing
        (
            {**CLAUDE, "CLAUDE_CODE_REMOTE": "true", "CLAUDE_CODE_ENTRYPOINT": "remote_web"},
            "claude-code",
        ),
        ({**CLAUDE, "CLAUDE_CODE_REMOTE": "true"}, "claude-code"),
        ({"L9_MEMORY_AGENT_ID": "claude-code"}, ""),
        ({}, ""),
    ],
)
def test_the_identity_is_derived_from_host_markers(env: dict[str, str], expected: str) -> None:
    assert ai.resolve_agent_id(env) == expected


def test_oauth_public_client_id_is_not_an_actor() -> None:
    assert ai.resolve_agent_id({"L9_MEMORY_OAUTH_CLIENT_ID": "public-client"}) == ""
    assert ai.resolve_agent_id({"AUTH0_CLIENT_ID": "public-client"}) == ""
    assert (
        ai.resolve_agent_id(
            {"L9_MEMORY_AGENT_ID": "public-client", "OAUTH_CLIENT_ID": "public-client"}
        )
        == ""
    )
    assert ai.resolve_agent_id({"L9_MEMORY_AGENT_ID": "manus", "OAUTH_CLIENT_ID": "other"}) == (
        "manus"
    )
    assert ai.resolve_surface_id({"L9_MEMORY_OAUTH_CLIENT_ID": "public-client"}) == ""


def test_a_configured_value_that_disagrees_is_reported_as_drift() -> None:
    assert ai.static_drift({**MOBILE, "L9_MEMORY_AGENT_ID": "claude-code"}) == ""
    assert ai.static_drift({**MOBILE, "L9_MEMORY_AGENT_ID": "claude-code-mobile"}) == (
        "claude-code-mobile"
    )
    assert ai.static_drift({"L9_MEMORY_AGENT_ID": "manus"}) == "", (
        "no markers: nothing to drift from"
    )


def test_an_unidentifiable_surface_says_why() -> None:
    env = {**CLAUDE, "CLAUDE_CODE_REMOTE": "true", "CLAUDE_CODE_ENTRYPOINT": "remote_web"}
    assert ai.resolve_agent_id(env) == "claude-code"
    assert ai.resolve_surface_id(env) == ""
    assert ai.resolve_surface_id(env) != "claude-code-mobile"
    assert ai.unresolved_reason(env) == ""
    assert "retired" in ai.unresolved_reason({"L9_MEMORY_AGENT_ID": "claude-code-desktop"})
    assert ai.unresolved_reason(MOBILE) == ""


def test_surface_follows_evidence_and_does_not_default() -> None:
    assert ai.resolve_agent_id(CLAUDE) == "claude-code"
    assert ai.resolve_surface_id(CLAUDE) == ""
    assert ai.resolve_surface_id({**CLAUDE, "CLAUDE_CODE_ENTRYPOINT": "cli"}) == "claude-code-cli"
    assert ai.resolve_surface_id(MOBILE) == "claude-code-mobile"
    assert ai.resolve_surface_id({"CURSOR_AGENT": "1"}) == "cursor-ide"
    assert ai.resolve_agent_id({"CURSOR_AGENT": "1", **CLAUDE}) == "cursor"
    assert ai.resolve_surface_id({"CURSOR_AGENT": "1", **CLAUDE}) == "cursor-ide"
    assert ai.resolve_surface_id({"L9_MEMORY_AGENT_ID": "codex"}) == ""
    assert ai.resolve_surface_id({"L9_MEMORY_AGENT_ID": "manus"}) == ""
    assert ai.resolve_surface_id({"L9_MEMORY_AGENT_ID": "gemini"}) == ""


def test_the_derived_authors_are_the_actors() -> None:
    assert ai.DERIVED_IDENTITIES == {"cursor", "claude-code"}
    assert ai.ADAPTER_IDENTITIES == {"manus", "codex", "gemini"}
    assert ai.RETIRED == {"claude-code-desktop", "claude-code-mobile"}


def test_retired_surface_authors_are_not_registry_agents() -> None:
    agents = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))["agents"]
    for agent_id in ("claude-code-desktop", "claude-code-mobile", "perplexity", "igorbot"):
        assert agent_id not in agents
    assert agents["claude-code"]["binding_status"] == "active"
    assert agents["cursor"]["binding_status"] == "active"


def test_an_unregistered_identity_says_why() -> None:
    assert "not a registered memory identity" in ai.unresolved_reason(
        {"L9_MEMORY_AGENT_ID": "agent-b"}
    )


def test_registry_and_resolver_cannot_drift_apart() -> None:
    """Every derived identity is an active registry agent with the derived USER_ID,
    and no retired or unrequested Claude identity is registered."""
    agents = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))["agents"]
    assert ai.DERIVED_IDENTITIES <= set(agents)
    assert ai.ADAPTER_IDENTITIES <= set(agents)
    for agent_id in ai.DERIVED_IDENTITIES:
        entry = agents[agent_id]
        assert entry.get("binding_status") == "active" or entry.get("status") == "active"
        assert entry["user_id"] == ai.user_id_for(agent_id), agent_id
    claude_agents = {a for a, v in agents.items() if v.get("adapter") == "claude-code"}
    assert claude_agents == set(ai.CLAUDE_IDENTITIES)
    assert not ai.RETIRED & set(agents)

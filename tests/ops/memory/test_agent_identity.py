"""ops/memory/agent_identity.py — the memory identity is DERIVED, never configured.

Cursor, Claude Code Desktop and Claude Code Mobile each have their own identity,
derived from markers the host sets on the running process. A configured
L9_MEMORY_AGENT_ID can never relabel a write (no drift), and a surface that
cannot be identified gets no identity rather than a guessed one.
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
        (CLAUDE, "claude-code-desktop"),
        ({"CLAUDE_CODE_ENTRYPOINT": "cli"}, "claude-code-desktop"),
        (MOBILE, "claude-code-mobile"),
        # configured values never relabel a surface that has markers
        ({"CURSOR_AGENT": "1", "L9_MEMORY_AGENT_ID": "claude-code"}, "cursor"),
        ({**CLAUDE, "L9_MEMORY_AGENT_ID": "claude-code-mobile"}, "claude-code-desktop"),
        ({**MOBILE, "L9_MEMORY_AGENT_ID": "claude-code-desktop"}, "claude-code-mobile"),
        # agents with no host markers are identified by their adapter's setting
        ({"L9_MEMORY_AGENT_ID": "manus"}, "manus"),
        ({"L9_MEMORY_AGENT_ID": "perplexity"}, "perplexity"),
        ({"L9_MEMORY_AGENT_ID": "perplexity-computer"}, "perplexity-computer"),
        ({"L9_MEMORY_AGENT_ID": "l-cto"}, "l-cto"),
        ({"L9_MEMORY_AGENT_ID": "igorbot"}, "igorbot"),
        # ...and only when it is a registered identity
        ({"L9_MEMORY_AGENT_ID": "agent-b"}, ""),
        ({"L9_MEMORY_AGENT_ID": "IgorBot"}, ""),
        # no guessing
        ({**CLAUDE, "CLAUDE_CODE_REMOTE": "true", "CLAUDE_CODE_ENTRYPOINT": "remote_web"}, ""),
        ({**CLAUDE, "CLAUDE_CODE_REMOTE": "true"}, ""),
        ({"L9_MEMORY_AGENT_ID": "claude-code"}, ""),
        ({}, ""),
    ],
)
def test_the_identity_is_derived_from_host_markers(env: dict[str, str], expected: str) -> None:
    assert ai.resolve_agent_id(env) == expected


def test_a_configured_value_that_disagrees_is_reported_as_drift() -> None:
    assert ai.static_drift({**MOBILE, "L9_MEMORY_AGENT_ID": "claude-code"}) == "claude-code"
    assert ai.static_drift({**MOBILE, "L9_MEMORY_AGENT_ID": "claude-code-mobile"}) == ""
    assert ai.static_drift({"L9_MEMORY_AGENT_ID": "manus"}) == "", (
        "no markers: nothing to drift from"
    )


def test_an_unidentifiable_surface_says_why() -> None:
    reason = ai.unresolved_reason(
        {**CLAUDE, "CLAUDE_CODE_REMOTE": "true", "CLAUDE_CODE_ENTRYPOINT": "remote_web"}
    )
    assert "remote_web" in reason and "no registered memory identity" in reason
    assert "retired" in ai.unresolved_reason({"L9_MEMORY_AGENT_ID": "claude-code"})
    assert ai.unresolved_reason(MOBILE) == ""


def test_exactly_the_three_requested_identities_are_derived() -> None:
    assert ai.DERIVED_IDENTITIES == {"cursor", "claude-code-desktop", "claude-code-mobile"}


def test_the_reserved_identities_exist_unwired() -> None:
    """Perplexity, Perplexity Computer, L CTO and IgorBot are reserved identities:
    registered, planned, no adapter, read-only until wired."""
    agents = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))["agents"]
    for agent_id in ("perplexity", "perplexity-computer", "l-cto", "igorbot"):
        entry = agents[agent_id]
        assert entry["status"] == "planned", agent_id
        assert entry["adapter"] == "none", agent_id
        assert entry["role"] == "observer" and entry["assigned_groups"] == [], agent_id
    assert agents["manus"]["status"] == "active" and agents["manus"]["adapter"] == "manus"


def test_an_unregistered_identity_says_why() -> None:
    assert "not a registered memory identity" in ai.unresolved_reason(
        {"L9_MEMORY_AGENT_ID": "agent-b"}
    )


def test_registry_and_resolver_cannot_drift_apart() -> None:
    """Every derived identity is an active registry agent with the derived USER_ID,
    and no retired or unrequested Claude identity is registered."""
    agents = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))["agents"]
    assert set(agents) == set(ai.ALL_IDENTITIES), (
        "the resolver and the registry must name the same agents"
    )
    for agent_id in ai.DERIVED_IDENTITIES:
        assert agents[agent_id]["status"] == "active", agent_id
        assert agents[agent_id]["user_id"] == ai.user_id_for(agent_id), agent_id
    claude_agents = {a for a, v in agents.items() if v.get("adapter") == "claude-code"}
    assert claude_agents == set(ai.CLAUDE_IDENTITIES)
    assert not ai.RETIRED & set(agents)

"""ops/memory/agent_identity.py — one memory identity per surface, never one Claude Code."""

from __future__ import annotations

import pytest

from ops.memory import agent_identity as ai

CLAUDE = {"CLAUDECODE": "1"}


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        ({"CURSOR_AGENT": "1"}, "cursor"),
        ({"CURSOR_AGENT": "1", "L9_MEMORY_AGENT_ID": "claude-code"}, "cursor"),
        (CLAUDE, "claude-code-desktop"),
        ({"L9_MEMORY_AGENT_ID": "claude-code"}, "claude-code-desktop"),
        ({**CLAUDE, "CLAUDE_CODE_ENTRYPOINT": "cli"}, "claude-code-desktop"),
        (
            {**CLAUDE, "CLAUDE_CODE_REMOTE": "true", "CLAUDE_CODE_ENTRYPOINT": "remote_mobile"},
            "claude-code-mobile",
        ),
        (
            {**CLAUDE, "CLAUDE_CODE_REMOTE": "true", "CLAUDE_CODE_ENTRYPOINT": "remote_web"},
            "claude-code-web",
        ),
        ({**CLAUDE, "CLAUDE_CODE_REMOTE": "true"}, "claude-code-web"),
        ({"L9_MEMORY_AGENT_ID": "manus"}, "manus"),
        (
            {"L9_MEMORY_AGENT_ID": "claude-code-mobile", "CLAUDE_CODE_REMOTE": "false"},
            "claude-code-mobile",
        ),
        ({}, ""),
    ],
)
def test_each_surface_resolves_to_its_own_identity(env: dict[str, str], expected: str) -> None:
    assert ai.resolve_agent_id(env) == expected


def test_the_family_marker_is_never_an_identity() -> None:
    for env in (
        {"L9_MEMORY_AGENT_ID": "claude-code"},
        CLAUDE,
        {**CLAUDE, "CLAUDE_CODE_REMOTE": "true"},
    ):
        assert ai.resolve_agent_id(env) != ai.CLAUDE_FAMILY


def test_every_claude_identity_is_a_registered_agent() -> None:
    from pathlib import Path  # noqa: PLC0415

    import yaml  # noqa: PLC0415

    registry = yaml.safe_load(
        (Path(__file__).resolve().parents[3] / "environment/agents/agent_registry.yaml").read_text()
    )
    agents = registry["agents"]
    assert "claude-code" not in agents, "one Claude Code identity for every surface is retired"
    for agent_id in (*ai.CLAUDE_IDENTITIES, ai.CURSOR):
        assert agents[agent_id]["status"] == "active"
        assert agents[agent_id]["user_id"] == ai.user_id_for(agent_id)

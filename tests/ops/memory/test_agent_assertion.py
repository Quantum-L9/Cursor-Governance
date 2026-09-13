"""ADR-0031 assertion mint helpers (ops/memory/agent_assertion.py)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ops.memory.agent_assertion import build_agent_mcp_env, env_from_local_secret_map


def test_build_agent_mcp_env_omits_human_secret() -> None:
    env = build_agent_mcp_env(
        agent_id="cursor",
        agents_door_secret="door-secret-at-least-24-chars!!",
        signing_key="cursor-signing-key-24chars!",
        grants={"cursor": {"role": "orchestrator"}},
    )
    assert env["L9_MEMORY_AGENT_ID"] == "cursor"
    assert "L9_MEMORY_AGENT_ASSERTION" in env
    assert "L9_MEMORY_HUMAN_DOOR_SECRET" not in env


def test_refuses_human_agent_id() -> None:
    with pytest.raises(ValueError, match="human"):
        build_agent_mcp_env(
            agent_id="human",
            agents_door_secret="door-secret-at-least-24-chars!!",
            signing_key="human-signing-key-24chars!!",
            grants={},
        )


def test_env_from_local_secret_map(tmp_path: Path) -> None:
    secrets = {
        "agents_door_secret": "door-secret-at-least-24-chars!!",
        "human_door_secret": "human-secret-at-least-24-chars!",
        "agent_signing_keys": {"cursor": "cursor-signing-key-24chars!"},
    }
    grants = {"cursor": {"role": "orchestrator", "can_write": True}}
    sp = tmp_path / "tokens.json"
    gp = tmp_path / "grants.json"
    sp.write_text(json.dumps(secrets))
    gp.write_text(json.dumps(grants))
    env = env_from_local_secret_map("cursor", sp, gp)
    assert env["L9_MEMORY_AGENTS_DOOR_SECRET"] == secrets["agents_door_secret"]
    assert "L9_MEMORY_HUMAN_DOOR_SECRET" not in env

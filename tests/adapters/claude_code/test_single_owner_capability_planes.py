"""Keep Claude platform helpers from duplicating L9-owned planes."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = ROOT / "environment/agents/adapters/claude-code/settings.template.json"


def test_governance_ssot_is_persistent_additional_directory() -> None:
    settings = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    assert settings["permissions"]["additionalDirectories"] == ["~/.cursor-governance"]


def test_claude_duplicate_memory_and_scheduler_planes_are_disabled() -> None:
    settings = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    env = settings["env"]
    assert env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] == "1"
    assert env["CLAUDE_CODE_DISABLE_CRON"] == "1"


def test_graphiti_mcp_is_read_only_from_model_tool_plane() -> None:
    settings = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    permissions = settings["permissions"]
    allow = set(permissions["allow"])
    deny = set(permissions["deny"])

    assert "mcp__graphiti-memory__search_memory_facts" in allow
    assert "mcp__graphiti-memory__group_ids" in allow
    assert "mcp__graphiti-memory__add_memory" in deny
    assert "mcp__graphiti-memory__add_memory" not in allow

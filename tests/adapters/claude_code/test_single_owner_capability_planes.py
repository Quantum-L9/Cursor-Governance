"""Keep Claude platform helpers from duplicating L9-owned capability planes."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = ROOT / "environment/agents/adapters/claude-code/settings.template.json"

CANONICAL_MEMORY_ALLOW = {
    "mcp__l9-graphite-memory__memory.health",
    "mcp__l9-graphite-memory__memory.search",
    "mcp__l9-graphite-memory__memory.hydrate",
    "mcp__l9-graphite-memory__memory.conflicts",
    "mcp__l9-graphite-memory__memory.phase_lock",
    "mcp__l9-graphite-memory__memory.write_governed",
}


def _permissions() -> tuple[set[str], set[str]]:
    settings = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    permissions = settings["permissions"]
    return set(permissions["allow"]), set(permissions["deny"])


def test_governance_ssot_is_persistent_additional_directory() -> None:
    settings = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    assert settings["permissions"]["additionalDirectories"] == ["~/.cursor-governance"]


def test_claude_duplicate_memory_and_scheduler_planes_are_disabled() -> None:
    settings = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    env = settings["env"]
    assert env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] == "1"
    assert env["CLAUDE_CODE_DISABLE_CRON"] == "1"


def test_canonical_memory_reads_and_governed_write_are_no_prompt() -> None:
    allow, deny = _permissions()
    assert CANONICAL_MEMORY_ALLOW <= allow
    assert CANONICAL_MEMORY_ALLOW.isdisjoint(deny)


def test_retired_provider_memory_plane_is_denied() -> None:
    allow, deny = _permissions()
    assert "mcp__graphiti-memory__*" in deny
    assert not any(item.startswith("mcp__graphiti-memory__") for item in allow)


def test_generic_and_admin_memory_writes_are_not_ambient_capabilities() -> None:
    allow, deny = _permissions()
    forbidden = {
        "mcp__l9-graphite-memory__memory.ingest",
        "mcp__l9-graphite-memory__memory.delete",
        "mcp__l9-graphite-memory__memory.promote",
        "mcp__l9-graphite-memory__memory.bootstrap",
        "mcp__l9-graphite-memory__memory.distill",
        "mcp__l9-graphite-memory__memory.synthesize_procedures",
        "mcp__l9-graphite-memory__memory.ingest_governed_candidate",
        "mcp__l9-graphite-memory__memory.record_reuse",
        "mcp__l9-graphite-memory__memory.invalidate_source",
        "mcp__l9-graphite-memory__write",
        "mcp__l9-graphite-memory__graphiti.write_governed",
    }
    assert forbidden <= deny
    assert allow.isdisjoint(forbidden)


def test_phase_lock_is_memory_write_precondition_not_repository_authority() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")
    assert "memory.phase_lock governs memory-write consistency only" in text
    assert "it is never repository-write" in text

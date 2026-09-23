"""Keep Claude platform helpers from duplicating L9-owned capability planes."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = ROOT / "environment/agents/adapters/claude-code/settings.template.json"

CANONICAL_MEMORY_ALLOW = {
    "mcp__l9-graphite-memory__memory_health",
    "mcp__l9-graphite-memory__memory_search",
    "mcp__l9-graphite-memory__memory_hydrate",
    "mcp__l9-graphite-memory__memory_conflicts",
    "mcp__l9-graphite-memory__memory_phase_lock",
    "mcp__l9-graphite-memory__memory_write_agent",
    "mcp__l9-graphite-memory__memory_write_governed",
    "mcp__l9-graphite-memory__memory_close",
}

MEMORY_PREFIX = "mcp__l9-graphite-memory__"

LEGACY_ALIASES = {
    "mcp__l9-graphite-memory__write",
    "mcp__l9-graphite-memory__search",
    "mcp__l9-graphite-memory__health",
    "mcp__l9-graphite-memory__bootstrap",
    "mcp__l9-graphite-memory__phase_lock",
    "mcp__l9-graphite-memory__verify_phase_lock",
    "mcp__l9-graphite-memory__conflicts",
    "mcp__l9-graphite-memory__graphiti_query",
    "mcp__l9-graphite-memory__graphiti_write_governed",
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


def test_canonical_memory_lifecycle_and_governed_write_are_no_prompt() -> None:
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
        "mcp__l9-graphite-memory__memory_ingest",
        "mcp__l9-graphite-memory__memory_delete",
        "mcp__l9-graphite-memory__memory_promote",
        "mcp__l9-graphite-memory__memory_bootstrap",
        "mcp__l9-graphite-memory__memory_distill",
        "mcp__l9-graphite-memory__memory_synthesize_procedures",
        "mcp__l9-graphite-memory__memory_ingest_governed_candidate",
        "mcp__l9-graphite-memory__memory_record_reuse",
        "mcp__l9-graphite-memory__memory_invalidate_source",
    }
    assert forbidden <= deny
    assert allow.isdisjoint(forbidden)


def test_legacy_aliases_cannot_become_a_second_agent_vocabulary() -> None:
    allow, deny = _permissions()
    assert LEGACY_ALIASES <= deny
    assert allow.isdisjoint(LEGACY_ALIASES)


def test_phase_lock_is_memory_write_precondition_not_repository_authority() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")
    assert "memory.phase_lock governs memory-write consistency only" in text
    assert "it is never repository-write" in text


def _exposed_memory_tools() -> set[str]:
    """Every tool the installed server registers, as Claude Code names it."""
    from l9_graphite_memory import mcp_tools  # noqa: PLC0415 - the locked, vendored package

    return {MEMORY_PREFIX + tool["name"].replace(".", "_") for tool in mcp_tools.tool_definitions()}


def test_every_memory_permission_names_a_tool_claude_code_can_match() -> None:
    """Regression: every entry was dotted (memory.write_agent), which Claude Code never
    emits — it maps '.' to '_' — so no allow matched (every write prompted) and no
    admin deny applied."""
    allow, deny = _permissions()
    exposed = _exposed_memory_tools()
    for entry in sorted((allow | deny)):
        if not entry.startswith(MEMORY_PREFIX):
            continue
        assert "." not in entry, f"{entry}: Claude Code tool names never contain '.'"
        assert entry in exposed, f"{entry}: not a tool the l9-graphite-memory server exposes"


def test_every_exposed_admin_or_alias_tool_is_decided() -> None:
    """No exposed memory tool is left to an ad-hoc prompt by omission, except the
    two read-only capability probes the package documents as operator-facing."""
    allow, deny = _permissions()
    undecided = _exposed_memory_tools() - allow - deny
    assert undecided <= {
        MEMORY_PREFIX + "memory_retention",
        MEMORY_PREFIX + "memory_generated_data_capabilities",
    }, sorted(undecided)

"""Agent-lane classification and the 24h hydrate prefetch (ADR-0034)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from memory_boundary_fixtures import (
    FakeMemoryCli,
    agent_lane_record,
    continuation_record,
    health_payload,
    hydration_payload,
    search_payload,
)

from ops.memory import hydration as hyd
from ops.memory.agent_lane import is_agent_lane_record
from ops.memory.control_plane_client import MemoryControlPlaneClient
from ops.memory.namespace_context import NamespaceContext
from ops.memory.session_contracts import session_task_objective

ROOT = Path(__file__).resolve().parents[3]
HEAD = "c" * 40
TASK = "Continue work in Cursor-Governance"


def _context():
    return NamespaceContext(
        workspace=str(ROOT),
        git_root=str(ROOT),
        repository_identity="Quantum-L9/Cursor-Governance",
        write_namespace_hint="cursor-governance",
        read_namespace_hints=("cursor-governance", "l9-workspace"),
        method="registry",
    )


def _hydrate(monkeypatch, fake: FakeMemoryCli, bound, *, task: str = TASK):
    monkeypatch.setattr(hyd, "resolve_namespace_context", lambda *_a, **_k: _context())
    monkeypatch.setattr(hyd, "repository_state_digest", lambda _p: HEAD)
    client = MemoryControlPlaneClient(bound, runner=fake.run, session_id="sess")
    return hyd.canonical_hydrate(ROOT, task=task, client=client, session_id="sess")


def test_session_task_objective_is_one_string() -> None:
    assert session_task_objective("Cursor-Governance") == "Continue work in Cursor-Governance"
    assert session_task_objective("  ") == "Continue work in project"


def test_continuation_is_not_agent_lane() -> None:
    record = SimpleNamespace(
        tags=("session_continuation",),
        metadata={"payload_schema": "cursor.continuation/v2", "producer": "Cursor-Governance"},
        memory_class="semantic",
        raw={},
    )
    assert is_agent_lane_record(record) is False


def test_write_agent_insight_is_agent_lane() -> None:
    raw = agent_lane_record()
    record = SimpleNamespace(
        tags=tuple(raw["tags"]),
        metadata=raw["metadata"],
        memory_class=raw["memory_class"],
        raw=raw,
    )
    assert is_agent_lane_record(record) is True


def test_meta_close_is_not_agent_lane() -> None:
    record = SimpleNamespace(
        tags=(),
        metadata={"producer": "Cursor-Governance"},
        memory_class="meta",
        raw={},
    )
    assert is_agent_lane_record(record) is False


def test_24h_prefetch_keeps_agent_writes_and_drops_capsules(
    monkeypatch, fake_cli: FakeMemoryCli, bound
) -> None:
    agent = agent_lane_record(content="issue 272 close write landed")
    capsule = continuation_record()

    def search(argv, _stdin):
        if "--recorded-after" in argv:
            return 0, search_payload(agent, capsule), ""
        return 0, search_payload(capsule), ""

    fake_cli.reply("health", 0, health_payload()).reply("hydrate", 0, hydration_payload()).on(
        "search", search
    )
    result = _hydrate(monkeypatch, fake_cli, bound)
    assert result.status == "OK"
    assert result.agent_lane_record_ids == (agent["record_id"],)
    assert any(content == agent["content"] for _cls, content in result.context_sections)
    assert "--recorded-after" in fake_cli.last("search")
    assert fake_cli.last("search").count("--namespace") == 1


def test_24h_prefetch_fail_open_does_not_degrade(
    monkeypatch, fake_cli: FakeMemoryCli, bound
) -> None:
    fake_cli.reply("health", 0, health_payload()).reply("hydrate", 0, hydration_payload()).on(
        "search",
        lambda argv, _stdin: (
            (1, None, '{"error":"SystemExit","message":"unrecognized arguments"}')
            if "--recorded-after" in argv
            else (0, search_payload(), "")
        ),
    )
    result = _hydrate(monkeypatch, fake_cli, bound)
    assert result.ok
    assert result.agent_lane_record_ids == ()
    assert any("24h agent-lane search" in warning for warning in result.warnings)


def test_agent_authored_meta_survives_the_hook_class_filter() -> None:
    """Provenance decides hook exclusion, not memory class (F613-3).

    ADR-0034 excludes hook capsules, META closes and Cursor-Governance
    producers — who wrote the record. Banning the `meta` class outright also
    dropped agent-authored meta/pickup writes, so legitimate content vanished
    from SessionStart recall and sessionEnd enrichment alike.
    """
    record = SimpleNamespace(
        tags=("agent:cursor",),
        metadata={
            "producer": "l9-graphite-memory",
            "provenance": {"producer": "l9-graphite-memory", "source_agent_id": "cursor"},
        },
        memory_class="meta",
        raw={},
    )
    assert is_agent_lane_record(record) is True


def test_unattributed_meta_is_still_excluded() -> None:
    """Fail closed: a meta record naming no author stays a hook artifact."""
    record = SimpleNamespace(tags=(), metadata={}, memory_class="meta", raw={})
    assert is_agent_lane_record(record) is False

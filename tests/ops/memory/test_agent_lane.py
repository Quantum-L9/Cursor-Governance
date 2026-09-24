"""Agent-lane classification and the 24h hydrate prefetch (ADR-0034)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
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


def _argparse_refusal(argv: list[str]) -> tuple[int, None, str]:
    """What the bound 2.4.0 parser prints for an option it does not define."""

    value = argv[argv.index("--recorded-after") + 1]
    return (
        2,
        None,
        "usage: l9-memory search [-h] [--group-id GROUP_ID] [--namespace NAMESPACE]\n"
        "                        [--recorded-before RECORDED_BEFORE] query\n"
        f"l9-memory: error: unrecognized arguments: --recorded-after {value}\n",
    )


def test_a_parser_without_recorded_after_falls_back_to_a_client_floor(
    monkeypatch, fake_cli: FakeMemoryCli, bound
) -> None:
    """The bound release refuses the selector; the 24h lane must still arrive.

    Observed on every hosted SessionStart: `l9-memory` 2.4.0 answers
    `--recorded-after` with argparse's exit 2, the search came back
    INVALID_RECEIPT, and the 24h agent-lane records never reached the packet.
    The client now re-asks without the selector and applies the floor itself.
    """
    from ops.memory import control_plane_client as cpc

    monkeypatch.setattr(cpc, "_RECORDED_AFTER_REFUSED", set())
    now = datetime.now(UTC)
    recent = agent_lane_record(
        record_id="aaaaaaaa-0000-0000-0000-000000000001",
        content="recent agent fact",
        created_at=(now - timedelta(hours=1)).isoformat(),
    )
    stale = agent_lane_record(
        record_id="aaaaaaaa-0000-0000-0000-000000000002",
        content="stale agent fact",
        created_at=(now - timedelta(hours=48)).isoformat(),
    )

    def search(argv, _stdin):
        if "--recorded-after" in argv:
            return _argparse_refusal(argv)
        if "session_continuation" in argv:
            return 0, search_payload(), ""
        return 0, search_payload(recent, stale), ""

    fake_cli.reply("health", 0, health_payload()).reply("hydrate", 0, hydration_payload()).on(
        "search", search
    )
    result = _hydrate(monkeypatch, fake_cli, bound)

    assert result.status == "OK"
    assert result.agent_lane_record_ids == (recent["record_id"],), "the floor drops the 48h record"
    assert not any("24h agent-lane search" in w for w in result.warnings), result.warnings
    assert cpc._RECORDED_AFTER_REFUSED, "the refusal is learned"

    # Learned once per process and CLI: the next hydrate never re-sends it.
    refused_before = sum("--recorded-after" in argv for argv, _c, _s in fake_cli.calls)
    _hydrate(monkeypatch, fake_cli, bound)
    refused_after = sum("--recorded-after" in argv for argv, _c, _s in fake_cli.calls)
    assert refused_before == refused_after == 1


def test_the_client_floor_excludes_a_record_it_cannot_date() -> None:
    from ops.memory.control_plane_client import _recorded_since

    floor = datetime.now(UTC) - timedelta(hours=24)
    assert _recorded_since(SimpleNamespace(recorded_at=None, created_at=None), floor) is False
    undated = SimpleNamespace(recorded_at="not a date", created_at=None)
    assert _recorded_since(undated, floor) is False
    inside = (datetime.now(UTC) - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    assert _recorded_since(SimpleNamespace(recorded_at=inside, created_at=None), floor) is True


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

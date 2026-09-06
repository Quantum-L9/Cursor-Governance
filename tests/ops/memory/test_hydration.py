"""Canonical hydration (plan §34 "Hydration tests") over a scripted memory CLI."""

from __future__ import annotations

import json
from pathlib import Path

from memory_boundary_fixtures import (
    FakeMemoryCli,
    continuation_record,
    error_stderr,
    health_payload,
    hydration_payload,
    search_payload,
)

from ops.memory import hydration as hyd
from ops.memory import session_state as ss
from ops.memory.control_plane_client import MemoryControlPlaneClient, OutcomeStatus
from ops.memory.namespace_context import NamespaceContext

ROOT = Path(__file__).resolve().parents[3]
RECORD = "66666666-6666-6666-6666-666666666666"
HEAD = "c" * 40


def _context(
    *, write: str | None = "cursor-governance", read=("cursor-governance", "l9-workspace")
):
    return NamespaceContext(
        workspace=str(ROOT),
        git_root=str(ROOT),
        repository_identity="Quantum-L9/Cursor-Governance",
        write_namespace_hint=write,
        read_namespace_hints=tuple(read),
        method="registry" if write else "unresolved",
    )


def _hydrate(monkeypatch, fake: FakeMemoryCli, bound, *, context=None, head=HEAD, **kwargs):
    monkeypatch.setattr(hyd, "resolve_namespace_context", lambda *_a, **_k: context or _context())
    monkeypatch.setattr(hyd, "repository_state_digest", lambda _p: head)
    client = MemoryControlPlaneClient(bound, runner=fake.run, session_id="sess")
    return hyd.canonical_hydrate(ROOT, task="resume", client=client, session_id="sess", **kwargs)


def _healthy(fake: FakeMemoryCli) -> FakeMemoryCli:
    return fake.reply("health", 0, health_payload())


def test_canonical_hit_with_typed_continuation(monkeypatch, fake_cli, bound) -> None:
    _healthy(fake_cli).reply("hydrate", 0, hydration_payload(RECORD)).reply(
        "search", 0, search_payload(continuation_record())
    )
    result = _hydrate(monkeypatch, fake_cli, bound)
    assert result.status == "OK" and result.ok
    assert result.record_ids == (RECORD,)
    assert result.continuation is not None
    assert result.continuation.record_id == RECORD
    assert result.continuation.capsule.next_action == "Wire runtime binding"
    assert result.continuation.stale is False
    assert result.calls == 3
    # The search asked memory for typed records by tag, on the primary namespace only.
    search_argv = fake_cli.last("search")
    assert "--tag" in search_argv and "session_continuation" in search_argv
    assert search_argv.count("--namespace") == 1
    # Hydrate requested the fan-in; memory authorized it.
    assert fake_cli.last("hydrate").count("--namespace") == 2
    assert result.requested_namespaces == ("cursor-governance", "l9-workspace")
    assert result.hydrate_receipt_digest


def test_canonical_no_hit_is_not_degraded(monkeypatch, fake_cli, bound) -> None:
    _healthy(fake_cli).reply("hydrate", 0, hydration_payload()).reply("search", 0, search_payload())
    result = _hydrate(monkeypatch, fake_cli, bound)
    assert result.status == "NO_HITS" and result.ok and not result.degraded
    assert result.continuation is None and result.record_ids == ()


def test_canonical_failure_is_named_not_empty(monkeypatch, fake_cli, bound) -> None:
    fake_cli.reply("health", 0, health_payload(store_healthy=False))
    result = _hydrate(monkeypatch, fake_cli, bound)
    assert result.status == "CANONICAL_UNAVAILABLE" and result.degraded
    assert not any(args[1] == "hydrate" for args, _c, _s in fake_cli.calls)


def test_hydrate_transport_failure_after_health(monkeypatch, fake_cli, bound) -> None:
    _healthy(fake_cli).reply("hydrate", 1, None, error_stderr("StoreError", "locked"))
    result = _hydrate(monkeypatch, fake_cli, bound)
    assert result.status == "CANONICAL_UNAVAILABLE"
    assert "locked" in (result.error or "")


def test_namespace_denied_fan_in_narrows_to_primary_and_stays_visible(
    monkeypatch, fake_cli, bound
) -> None:
    def hydrate(argv, _stdin):
        if argv.count("--namespace") > 1:
            return (
                1,
                None,
                error_stderr("AuthorizationError", "not authorized to read 'l9-workspace'"),
            )
        return 0, hydration_payload(RECORD), ""

    _healthy(fake_cli).on("hydrate", hydrate).reply("search", 0, search_payload())
    result = _hydrate(monkeypatch, fake_cli, bound)
    assert result.status == "OK"
    assert result.requested_namespaces == ("cursor-governance",)
    assert result.fan_in_denied and "l9-workspace" in result.fan_in_denied
    assert sum(1 for args, _c, _s in fake_cli.calls if args[1] == "hydrate") == 2


def test_unauthorized_primary_namespace_is_a_failure(monkeypatch, fake_cli, bound) -> None:
    _healthy(fake_cli).reply(
        "hydrate", 1, None, error_stderr("AuthorizationError", "not authorized to read 'x'")
    )
    result = _hydrate(monkeypatch, fake_cli, bound, context=_context(read=("cursor-governance",)))
    assert result.status == "UNAUTHORIZED_NAMESPACE" and result.degraded


def test_projection_failure_does_not_block_canonical_hydration(
    monkeypatch, fake_cli, bound
) -> None:
    fake_cli.reply(
        "health", 1, health_payload(projection="graphiti", projection_healthy=False)
    ).reply("hydrate", 0, hydration_payload(RECORD)).reply("search", 0, search_payload())
    result = _hydrate(monkeypatch, fake_cli, bound)
    assert result.status == "OK"
    assert result.projection_status == "unhealthy"
    assert any("projection degraded" in warning for warning in result.warnings)


def test_partial_canonical_result_keeps_hits_and_reports_status(
    monkeypatch, fake_cli, bound
) -> None:
    _healthy(fake_cli).reply("hydrate", 0, hydration_payload(RECORD, status="partial")).reply(
        "search", 0, search_payload()
    )
    result = _hydrate(monkeypatch, fake_cli, bound)
    assert result.status == "OK" and result.record_ids == (RECORD,)


def test_stale_continuation_versus_current_repository_state(monkeypatch, fake_cli, bound) -> None:
    _healthy(fake_cli).reply("hydrate", 0, hydration_payload()).reply(
        "search", 0, search_payload(continuation_record(repository_state_digest="b" * 40))
    )
    result = _hydrate(monkeypatch, fake_cli, bound, head=HEAD)
    assert result.continuation is not None and result.continuation.stale is True
    assert result.repository_state_digest == HEAD


def test_multiple_continuation_candidates_newest_wins(monkeypatch, fake_cli, bound) -> None:
    older = continuation_record(
        record_id="11111111-aaaa-aaaa-aaaa-111111111111",
        created_at="2026-09-01T00:00:00+00:00",
        next_action="older",
    )
    newer = continuation_record(
        record_id="22222222-bbbb-bbbb-bbbb-222222222222",
        created_at="2026-09-06T00:00:00+00:00",
        next_action="newer",
    )
    _healthy(fake_cli).reply("hydrate", 0, hydration_payload()).reply(
        "search", 0, search_payload(older, newer)
    )
    result = _hydrate(monkeypatch, fake_cli, bound)
    assert result.continuation is not None
    assert result.continuation.capsule.next_action == "newer"
    assert result.continuation_candidates == 2


def test_malformed_continuation_is_skipped_and_named(monkeypatch, fake_cli, bound) -> None:
    broken = continuation_record(
        record_id="33333333-cccc-cccc-cccc-333333333333",
        created_at="2026-09-07T00:00:00+00:00",
        payload_override={"schema": "cursor.continuation/v2", "session_id": "only"},
    )
    good = continuation_record()
    _healthy(fake_cli).reply("hydrate", 0, hydration_payload()).reply(
        "search", 0, search_payload(broken, good)
    )
    result = _hydrate(monkeypatch, fake_cli, bound)
    assert result.continuation is not None and result.continuation.record_id == RECORD
    assert any("33333333 malformed" in warning for warning in result.warnings)


def test_records_without_the_schema_are_never_treated_as_continuation(
    monkeypatch, fake_cli, bound
) -> None:
    plain = continuation_record()
    plain["metadata"] = {"producer": "someone"}
    _healthy(fake_cli).reply("hydrate", 0, hydration_payload()).reply(
        "search", 0, search_payload(plain)
    )
    result = _hydrate(monkeypatch, fake_cli, bound)
    assert result.continuation is None and result.continuation_candidates == 0


def test_unresolved_namespace_never_calls_memory(monkeypatch, fake_cli, bound) -> None:
    result = _hydrate(monkeypatch, fake_cli, bound, context=_context(write=None, read=()))
    assert result.status == hyd.STATUS_NAMESPACE_UNRESOLVED and result.degraded
    assert fake_cli.calls == []


def test_no_write_hint_skips_continuation_but_hydrates_shared_read(
    monkeypatch, fake_cli, bound
) -> None:
    _healthy(fake_cli).reply("hydrate", 0, hydration_payload(RECORD))
    result = _hydrate(
        monkeypatch, fake_cli, bound, context=_context(write=None, read=("l9-workspace",))
    )
    assert result.status == "OK" and result.continuation is None
    assert not any(args[1] == "search" for args, _c, _s in fake_cli.calls)


def test_binding_failure_is_named(monkeypatch, fake_cli) -> None:
    from ops.memory.runtime_binding import STATUS_UNBOUND, RuntimeBinding

    unbound = RuntimeBinding(
        status=STATUS_UNBOUND,
        runtime_mode="pinned_environment",
        memory_package="l9-graphite-memory",
        expected_version="x",
        expected_contract_version="memory-control-plane/v1",
        manifest_path="m",
        reasons=("not importable",),
    )
    result = _hydrate(monkeypatch, fake_cli, unbound)
    assert result.status == OutcomeStatus.BINDING_FAILED.value
    assert "not importable" in (result.error or "")


def test_session_state_is_local_and_non_authoritative(
    monkeypatch, fake_cli, bound, tmp_path
) -> None:
    _healthy(fake_cli).reply("hydrate", 0, hydration_payload(RECORD)).reply(
        "search", 0, search_payload(continuation_record())
    )
    result = _hydrate(monkeypatch, fake_cli, bound)
    path = ss.write_session_state("sess", result, directory=tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["authority"] == "none" and data["schema"] == ss.STATE_SCHEMA
    assert data["namespace_request"] == {
        "write": "cursor-governance",
        "read": ["cursor-governance", "l9-workspace"],
    }
    assert data["memory_status"] == "OK"
    assert "GRAPHITI" not in json.dumps(data).upper()
    assert ss.read_session_state("sess", directory=tmp_path) == data
    assert ss.read_session_state("other", directory=tmp_path) is None

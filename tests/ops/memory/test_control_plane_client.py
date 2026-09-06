"""MemoryControlPlaneClient: one CLI call per operation, exit code + receipt = verdict."""

from __future__ import annotations

import json

import pytest
from memory_boundary_fixtures import (
    FakeMemoryCli,
    close_payload,
    error_stderr,
    health_payload,
    hydration_payload,
)

from ops.memory.control_plane_client import MemoryControlPlaneClient, OutcomeStatus
from ops.memory.runtime_binding import STATUS_UNBOUND, RuntimeBinding

WS = "/tmp/workspace"


def client(bound: RuntimeBinding, cli: FakeMemoryCli) -> MemoryControlPlaneClient:
    return MemoryControlPlaneClient(bound, runner=cli.run, session_id="session-9")


# ---------------------------------------------------------------------------
# Hydration (S-07 failure taxonomy)
# ---------------------------------------------------------------------------


def test_hydrate_hit_requests_fan_in_and_reports_ok(bound, fake_cli) -> None:
    fake_cli.reply("hydrate", 0, hydration_payload("r1"))
    outcome = client(bound, fake_cli).hydrate(
        "resume task",
        workspace=WS,
        write_namespace_hint="cursor-governance",
        read_namespace_hints=("cursor-governance", "l9-workspace"),
        task_signature="sig",
    )
    assert outcome.status is OutcomeStatus.OK
    assert outcome.receipt.record_ids == ("r1",)
    argv = fake_cli.last("hydrate")
    assert argv[2] == "resume task"
    assert argv[argv.index("--group-id") + 1] == "cursor-governance"
    assert argv.count("--namespace") == 2
    assert fake_cli.calls[-1][1] == WS
    evidence = outcome.integration_receipt
    assert evidence["operation"] == "hydrate"
    assert evidence["transport"] == "cli"
    assert evidence["requested_namespaces"] == ["cursor-governance", "l9-workspace"]
    assert evidence["canonical_receipt_id"] == "11111111-1111-1111-1111-111111111111"
    assert evidence["task_signature"] == "sig"
    assert "content" not in json.dumps(evidence)


def test_hydrate_no_hits_is_not_an_error(bound, fake_cli) -> None:
    fake_cli.reply("hydrate", 0, hydration_payload())
    outcome = client(bound, fake_cli).hydrate(
        "t", workspace=WS, write_namespace_hint="ns", read_namespace_hints=("ns",)
    )
    assert outcome.status is OutcomeStatus.NO_HITS
    assert outcome.error is None


def test_hydrate_unauthorized_namespace_is_explicit(bound, fake_cli) -> None:
    fake_cli.reply(
        "hydrate", 1, None, error_stderr("AuthorizationError", "not authorized to read 'x'")
    )
    outcome = client(bound, fake_cli).hydrate(
        "t", workspace=WS, write_namespace_hint="ns", read_namespace_hints=("ns", "x")
    )
    assert outcome.status is OutcomeStatus.UNAUTHORIZED_NAMESPACE
    assert "not authorized" in (outcome.error or "")


def test_hydrate_store_failure_is_canonical_unavailable_not_empty(bound, fake_cli) -> None:
    fake_cli.reply("hydrate", 1, None, error_stderr("StoreError", "database locked"))
    outcome = client(bound, fake_cli).hydrate(
        "t", workspace=WS, write_namespace_hint="ns", read_namespace_hints=("ns",)
    )
    assert outcome.status is OutcomeStatus.CANONICAL_UNAVAILABLE


def test_hydrate_failed_receipt_is_canonical_unavailable(bound, fake_cli) -> None:
    fake_cli.reply("hydrate", 1, hydration_payload(status="failed"))
    outcome = client(bound, fake_cli).hydrate(
        "t", workspace=WS, write_namespace_hint="ns", read_namespace_hints=("ns",)
    )
    assert outcome.status is OutcomeStatus.CANONICAL_UNAVAILABLE


def test_hydrate_timeout_is_timeout(bound, fake_cli) -> None:
    fake_cli.timeout_on.add("hydrate")
    outcome = client(bound, fake_cli).hydrate(
        "t", workspace=WS, write_namespace_hint="ns", read_namespace_hints=("ns",)
    )
    assert outcome.status is OutcomeStatus.TIMEOUT


def test_hydrate_garbage_is_invalid_receipt(bound, fake_cli) -> None:
    fake_cli.on("hydrate", lambda _a, _s: (0, {"unexpected": True}, ""))
    outcome = client(bound, fake_cli).hydrate(
        "t", workspace=WS, write_namespace_hint="ns", read_namespace_hints=("ns",)
    )
    assert outcome.status is OutcomeStatus.INVALID_RECEIPT


# ---------------------------------------------------------------------------
# Health (INV-04 / INV-05)
# ---------------------------------------------------------------------------


def test_health_projection_down_does_not_erase_canonical_truth(bound, fake_cli) -> None:
    fake_cli.reply("health", 1, health_payload(projection="http", projection_healthy=False))
    outcome = client(bound, fake_cli).health()
    assert outcome.status is OutcomeStatus.PARTIAL_PROJECTION_DEGRADED
    assert outcome.receipt.canonical_ready is True
    assert outcome.integration_receipt["projection_status"] == "unhealthy"


def test_health_store_down_is_unavailable_whatever_projection_says(bound, fake_cli) -> None:
    fake_cli.reply(
        "health", 1, health_payload(store_healthy=False, projection="http", projection_healthy=True)
    )
    outcome = client(bound, fake_cli).health()
    assert outcome.status is OutcomeStatus.CANONICAL_UNAVAILABLE


# ---------------------------------------------------------------------------
# Candidate ingress (write taxonomy)
# ---------------------------------------------------------------------------


def candidate() -> dict[str, object]:
    return {"kind": "MemoryCandidate", "source": {"namespace": "cursor-governance"}}


def candidate_receipt(status: str, record_id: str | None = "r1") -> dict[str, object]:
    return {
        "status": status,
        "candidate_id": "c1",
        "namespace": "cursor-governance",
        "record_id": record_id,
        "write_receipt_id": "w1",
        "storage_committed": status != "rejected",
    }


def test_candidate_accepted_sends_payload_on_stdin(bound, fake_cli) -> None:
    fake_cli.reply("ingest-governed-candidate", 0, candidate_receipt("admitted"))
    outcome = client(bound, fake_cli).ingest_candidate(candidate(), workspace=WS)
    assert outcome.status is OutcomeStatus.OK
    _argv, _cwd, stdin = fake_cli.calls[-1]
    assert json.loads(stdin or "")["kind"] == "MemoryCandidate"
    assert outcome.integration_receipt["requested_namespaces"] == ["cursor-governance"]


def test_candidate_duplicate_retry_is_ok_with_same_record(bound, fake_cli) -> None:
    fake_cli.reply("ingest-governed-candidate", 0, candidate_receipt("duplicate"))
    outcome = client(bound, fake_cli).ingest_candidate(candidate(), workspace=WS)
    assert outcome.status is OutcomeStatus.OK
    assert outcome.receipt.record_id == "r1"


def test_candidate_rejected_and_quarantined_stay_visible(bound, fake_cli) -> None:
    fake_cli.reply("ingest-governed-candidate", 7, candidate_receipt("rejected", None))
    assert (
        client(bound, fake_cli).ingest_candidate(candidate(), workspace=WS).status
        is OutcomeStatus.REJECTED
    )
    fake_cli.reply("ingest-governed-candidate", 0, candidate_receipt("quarantined"))
    assert (
        client(bound, fake_cli).ingest_candidate(candidate(), workspace=WS).status
        is OutcomeStatus.QUARANTINED
    )


def test_candidate_exit_zero_without_record_is_invalid(bound, fake_cli) -> None:
    fake_cli.reply("ingest-governed-candidate", 0, candidate_receipt("admitted", None))
    outcome = client(bound, fake_cli).ingest_candidate(candidate(), workspace=WS)
    assert outcome.status is OutcomeStatus.INVALID_RECEIPT


# ---------------------------------------------------------------------------
# Close (INV-06: only a canonical receipt closes)
# ---------------------------------------------------------------------------


def test_close_committed_only_on_exit_zero_and_complete_receipt(bound, fake_cli) -> None:
    fake_cli.reply("close", 0, close_payload())
    outcome = client(bound, fake_cli).close(
        workspace=WS,
        namespace="cursor-governance",
        summary="done",
        capsule_digest="abc",
        idempotency_key="close:session-9",
    )
    assert outcome.status is OutcomeStatus.OK
    argv = fake_cli.last("close")
    assert argv[argv.index("--session-id") + 1] == "session-9"
    assert argv[argv.index("--idempotency-key") + 1] == "close:session-9"
    assert argv[argv.index("--capsule-digest") + 1] == "abc"


def test_close_replay_is_ok_and_marked(bound, fake_cli) -> None:
    fake_cli.reply("close", 0, close_payload(replayed=True))
    outcome = client(bound, fake_cli).close(
        workspace=WS, namespace="cursor-governance", summary="s"
    )
    assert outcome.ok and outcome.receipt.replayed is True


def test_close_dry_run_is_not_committed(bound, fake_cli) -> None:
    fake_cli.reply("close", 3, close_payload(status="partial", record_id=None))
    outcome = client(bound, fake_cli).close(
        workspace=WS, namespace="cursor-governance", summary="s", dry_run=True
    )
    assert outcome.status is OutcomeStatus.NOT_COMMITTED


def test_close_rejected_is_rejected(bound, fake_cli) -> None:
    fake_cli.reply("close", 2, close_payload(status="failed", record_id=None))
    outcome = client(bound, fake_cli).close(
        workspace=WS, namespace="cursor-governance", summary="s"
    )
    assert outcome.status is OutcomeStatus.REJECTED


def test_close_exit_zero_with_no_record_is_invalid_not_success(bound, fake_cli) -> None:
    fake_cli.reply("close", 0, close_payload(status="partial", record_id=None))
    outcome = client(bound, fake_cli).close(
        workspace=WS, namespace="cursor-governance", summary="s"
    )
    assert outcome.status is OutcomeStatus.INVALID_RECEIPT


def test_close_timeout_is_unknown_not_success(bound, fake_cli) -> None:
    fake_cli.timeout_on.add("close")
    outcome = client(bound, fake_cli).close(
        workspace=WS, namespace="cursor-governance", summary="s"
    )
    assert outcome.status is OutcomeStatus.TIMEOUT


# ---------------------------------------------------------------------------
# Conflicts / phase lock come from canonical receipts
# ---------------------------------------------------------------------------


def test_conflicts_and_phase_lock_are_canonical_receipts(bound, fake_cli) -> None:
    fake_cli.reply(
        "conflicts",
        2,
        {
            "namespace": "ns",
            "conflicts": [{"left_record_id": "a", "right_record_id": "b"}],
            "snapshot_digest": "f" * 64,
            "checked_record_count": 2,
        },
    )
    fake_cli.reply(
        "phase-lock",
        2,
        {
            "lock_id": "l",
            "namespace": "ns",
            "task_signature": "sig-0001",
            "granted": False,
            "expires_at": "2026-09-05T00:00:00+00:00",
            "snapshot_digest": "f" * 64,
        },
    )
    fake_cli.reply(
        "verify-phase-lock",
        0,
        {
            "namespace": "ns",
            "task_signature": "sig-0001",
            "valid": True,
            "reasons": ["phase lock is current and conflict-free"],
            "current_snapshot_digest": "f" * 64,
        },
    )
    c = client(bound, fake_cli)
    conflicts = c.conflicts(workspace=WS, namespace="ns")
    assert conflicts.ok and conflicts.receipt.has_conflicts is True
    lock = c.phase_lock(workspace=WS, namespace="ns", task_signature="sig-0001")
    assert lock.status is OutcomeStatus.REJECTED and lock.receipt.granted is False
    verify = c.verify_phase_lock(workspace=WS, namespace="ns", task_signature="sig-0001")
    assert verify.ok and verify.receipt.valid is True


# ---------------------------------------------------------------------------
# Binding guard and provider isolation
# ---------------------------------------------------------------------------


def test_unbound_runtime_never_spawns_anything(fake_cli) -> None:
    unbound = RuntimeBinding(
        status=STATUS_UNBOUND,
        runtime_mode="pinned_environment",
        memory_package="l9-graphite-memory",
        expected_version="2.2.0",
        expected_contract_version="memory-control-plane/v1",
        manifest_path="m",
        reasons=("package version 2.1.0 does not match expected 2.2.0",),
    )
    outcome = MemoryControlPlaneClient(unbound, runner=fake_cli.run).health()
    assert outcome.status is OutcomeStatus.BINDING_FAILED
    assert "2.1.0" in (outcome.error or "")
    assert fake_cli.calls == []


@pytest.mark.parametrize("variable", ["GRAPHITI_MCP_URL", "GRAPHITI_MCP_TOKEN"])
def test_client_ignores_provider_variables(bound, fake_cli, monkeypatch, variable) -> None:
    """Attack A: a fake provider in the environment changes nothing Cursor sends."""

    monkeypatch.setenv(variable, "http://fake-provider.invalid")
    fake_cli.reply("health", 0, health_payload())
    outcome = client(bound, fake_cli).health()
    assert outcome.ok
    assert "fake-provider" not in json.dumps(fake_cli.calls, default=str)


def test_cursor_client_lifecycle_is_memory_owned(bound, fake_cli) -> None:
    fake_cli.reply("client cursor status", 1, {"status": "unchanged", "reasons": ["not installed"]})
    fake_cli.reply("client cursor verify", 0, {"status": "complete", "tool_count": 30})
    c = client(bound, fake_cli)
    status = c.cursor_client_status(config_path="/tmp/mcp.json")
    assert status.status is OutcomeStatus.REJECTED and "not installed" in (status.error or "")
    assert c.cursor_client_verify(config_path="/tmp/mcp.json").ok
    argv = fake_cli.calls[-1][0]
    assert argv[1:4] == ["client", "cursor", "verify"] and "--path" in argv

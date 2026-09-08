"""The offline distill worker admits through the control plane (stage C10)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from memory_boundary_fixtures import FakeMemoryCli

from ops.graphiti.distill_queue import worker
from ops.memory.control_plane_client import MemoryControlPlaneClient

ROOT = Path(__file__).resolve().parents[3]


def _job() -> dict:
    return {
        "schema_version": worker.SCHEMA_VERSION,
        "session_id": "sess-42",
        "group_id": "cursor-governance",
        "agent_id": "gha-distill",
        "content_hash": "c" * 64,
        "transcript_excerpt": "user: finish the realignment",
    }


def _packet() -> dict:
    return {
        "packet_id": "pkt-1",
        "session_id": "sess-42",
        "pickup": {
            "active_objective": "Finish the realignment",
            "next_action": "Open the PR",
            "blockers": ["none"],
        },
        "promotion_decisions": [
            {
                "kind": "lesson",
                "body": "Guard nullable attrs.",
                "decision": "promote",
                "score": 0.9,
            },
            {
                "kind": "decision",
                "body": "Namespace is repo identity.",
                "decision": "promote",
                "score": 0.8,
            },
            {"kind": "insight", "body": "low", "decision": "promote", "score": 0.2},
            {"kind": "preference", "body": "tables", "decision": "promote", "score": 0.9},
        ],
    }


def _candidate_payload(status: str = "admitted") -> dict:
    return {
        "status": status,
        "candidate_id": "cursor-continuation:x",
        "namespace": "cursor-governance",
        "record_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "write_receipt_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        "storage_committed": True,
        "memory_state": "active",
        "reason": None,
    }


def _write_payload() -> dict:
    return {
        "receipt_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "status": "admitted",
        "namespace": "cursor-governance",
        "record_id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
        "idempotency_key": "k",
        "admission": {"reasons": ["ok"]},
        "warnings": [],
    }


def test_capsule_is_built_from_the_distilled_pickup() -> None:
    capsule = worker.build_continuation(_job(), _packet())
    assert capsule.session_id == "sess-42"
    assert capsule.repository_identity == "cursor-governance"
    assert capsule.objective == "Finish the realignment"
    assert capsule.next_action == "Open the PR"
    assert capsule.repository_state_digest == "unknown"
    assert capsule.producer_version == worker.DISTILL_PRODUCER_VERSION
    assert capsule.blockers == ("none",)


def test_ingest_admits_capsule_then_promotions_with_idempotency(
    bound, fake_cli: FakeMemoryCli
) -> None:
    fake_cli.reply("ingest-governed-candidate", 0, _candidate_payload())
    fake_cli.reply("write", 0, _write_payload())
    client = MemoryControlPlaneClient(bound, runner=fake_cli.run)
    writes = worker.ingest_to_memory(_job(), _packet(), client=client, workspace=str(ROOT))
    assert [w["kind"] for w in writes] == ["session_continuation", "lesson", "decision"]
    assert all(w["written"] for w in writes)
    candidate_call = next(c for c in fake_cli.calls if c[0][1] == "ingest-governed-candidate")
    candidate = json.loads(candidate_call[2] or "{}")
    assert candidate["source"]["namespace"] == "cursor-governance"
    assert candidate["provenance"]["source_agent_id"] == "gha-distill"
    write_argv = [c[0] for c in fake_cli.calls if c[0][1] == "write"]
    assert [argv[argv.index("--kind") + 1] for argv in write_argv] == ["insight", "decision"]
    keys = [argv[argv.index("--idempotency-key") + 1] for argv in write_argv]
    assert keys == [f"distill:{'c' * 64}:0", f"distill:{'c' * 64}:1"]
    assert all(c[1] == str(ROOT) for c in fake_cli.calls), "the CLI runs at the workspace"


def test_dry_run_calls_no_memory(bound, fake_cli: FakeMemoryCli) -> None:
    client = MemoryControlPlaneClient(bound, runner=fake_cli.run)
    writes = worker.ingest_to_memory(_job(), _packet(), dry_run=True, client=client, workspace="/x")
    assert fake_cli.calls == []
    assert all(w["dry_run"] for w in writes)


def test_rejected_verdict_is_recorded_not_raised(bound, fake_cli: FakeMemoryCli) -> None:
    fake_cli.reply(
        "ingest-governed-candidate",
        7,
        {
            **_candidate_payload("rejected"),
            "record_id": None,
            "storage_committed": False,
            "memory_state": "rejected",
            "reason": "no",
        },
    )
    fake_cli.reply("write", 0, _write_payload())
    client = MemoryControlPlaneClient(bound, runner=fake_cli.run)
    writes = worker.ingest_to_memory(_job(), _packet(), client=client, workspace=str(ROOT))
    assert writes[0]["written"] is False and writes[0]["status"] == "rejected"
    assert writes[1]["written"] is True


def test_memory_unavailable_raises_so_the_job_stays_pending(bound, fake_cli: FakeMemoryCli) -> None:
    fake_cli.timeout_on.add("ingest-governed-candidate")
    client = MemoryControlPlaneClient(bound, runner=fake_cli.run)
    with pytest.raises(RuntimeError, match="not admitted"):
        worker.ingest_to_memory(_job(), _packet(), client=client, workspace=str(ROOT))


def test_worker_source_has_no_provider_egress() -> None:
    src = (ROOT / "ops" / "graphiti" / "distill_queue" / "worker.py").read_text(encoding="utf-8")
    for forbidden in ("graphiti_memory_client", "add_memory", "call_tool", "GRAPHITI_MCP"):
        assert forbidden not in src

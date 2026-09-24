"""Harvest-plane receipt contract (law §36): schema/runtime parity and lifecycle.

The schema formalizes the receipt ``write_ingress`` already wrote. These tests
prove the file and the runtime agree, and drive the real ingress path to show
each harvest outcome is distinct and auditable. The memory owner is replaced
by a stub *command* only; the transport, processor, routing and receipt code
are the production modules. Nothing here tests memory semantics.
"""

from __future__ import annotations

import copy
import json
import sys
import textwrap
from pathlib import Path

import pytest

INGRESS = Path(__file__).resolve().parents[1]
GENERATED_DATA = INGRESS.parent
REPO = Path(__file__).resolve().parents[5]
SCHEMA_FILE = GENERATED_DATA / "schemas" / "generated-data-ingress-receipt.schema.json"
FIXTURE = GENERATED_DATA / "tests" / "fixtures" / "valid-recon-packet.json"
for entry in (str(INGRESS), str(REPO)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import ingest  # noqa: E402

receipts = ingest.ingress_receipts

MEMORY_STUB = textwrap.dedent(
    """
    import json, sys
    candidate = json.load(sys.stdin)
    if sys.argv[1] == "accept":
        print(json.dumps({"status": "accepted", "candidate_id": candidate["candidate_id"],
                          "memory_id": "rec-1", "write_receipt_id": "wr-1"}))
    else:
        print(json.dumps({"status": "rejected", "error": "namespace refused"}))
        sys.exit(1)
    """
)


@pytest.fixture(autouse=True)
def isolated_runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("L9_RUNTIME_ROOT", str(tmp_path / "runtime"))
    monkeypatch.delenv("L9_SGD_GRAPHITI_INGEST_COMMAND", raising=False)
    monkeypatch.delenv("L9_SGD_GRAPHITI_INGEST_ENDPOINT", raising=False)


def _memory_owner(tmp_path, monkeypatch, verdict: str) -> None:
    stub = tmp_path / "memory_stub.py"
    stub.write_text(MEMORY_STUB, encoding="utf-8")
    monkeypatch.setenv("L9_SGD_GRAPHITI_INGEST_COMMAND", f"{sys.executable} {stub} {verdict}")


def _packet() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _valid_body() -> dict:
    return {
        "schema": receipts.SCHEMA,
        "acceptance_receipt_digest": "acc-1",
        "source_kind": "accepted_subagent_result",
        "outcome": "NO_REUSABLE_DATA",
        "reason": "no generated-data packet",
        "processor_job_id": None,
        "processing_status": "NOT_STARTED",
        "observed_at": "2026-09-24T00:00:00+00:00",
        "receipt_digest": "a" * 64,
    }


def _on_disk(receipt: dict) -> dict:
    return receipts.load_ingress(receipt["acceptance_receipt_digest"])


# --- schema / runtime parity -------------------------------------------------


def test_schema_enums_equal_runtime_constants():
    schema = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
    props = schema["properties"]
    assert props["schema"]["const"] == receipts.SCHEMA
    assert set(props["outcome"]["enum"]) == receipts.OUTCOMES
    assert set(props["processing_status"]["enum"]) == receipts.PROCESSING_STATUSES
    assert receipts.SCHEMA_PATH == SCHEMA_FILE


def test_every_runtime_writer_key_is_declared():
    """The closed schema must name every key ingest.py hands write_ingress."""
    source = (INGRESS / "ingest.py").read_text(encoding="utf-8")
    declared = set(json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))["properties"])
    for key in (
        "acceptance_receipt_digest",
        "source_kind",
        "outcome",
        "reason",
        "processor_job_id",
        "processing_status",
        "packet_digest",
        "packet_evidence_path",
        "database_path",
        "delivery_count",
        "delivery",
        "processing_error",
    ):
        assert f'"{key}"' in source, key
        assert key in declared, key


def test_valid_body_passes():
    receipts._validate_receipt(_valid_body())


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(lambda b: b.pop("acceptance_receipt_digest"), id="missing-identity"),
        pytest.param(lambda b: b.pop("source_kind"), id="missing-source-type"),
        pytest.param(lambda b: b.update(unexpected="x"), id="unknown-top-level-key"),
        pytest.param(lambda b: b.update(source_kind="chat_dump"), id="invalid-source-type"),
        pytest.param(lambda b: b.update(outcome="ROUTED"), id="invalid-outcome"),
        pytest.param(lambda b: b.update(processing_status="DONE"), id="invalid-status"),
        pytest.param(lambda b: b.update(delivery="memory"), id="malformed-route-result"),
        pytest.param(
            lambda b: b.update(delivery={"accepted": 1}), id="nothing-to-preserve-with-routes"
        ),
        pytest.param(
            lambda b: b.update(processor_job_id="job-1"), id="nothing-to-preserve-with-job"
        ),
        pytest.param(
            lambda b: b.update(processing_error={"type": "X", "message": "m"}),
            id="error-reported-as-no-op",
        ),
        pytest.param(
            lambda b: b.update(outcome="CAPTURED", processor_job_id=None),
            id="captured-without-job",
        ),
        pytest.param(lambda b: b.update(outcome="QUARANTINED"), id="quarantined-without-evidence"),
    ],
)
def test_structural_violations_are_refused(mutate):
    body = copy.deepcopy(_valid_body())
    mutate(body)
    with pytest.raises(ValueError, match="violates"):
        receipts._validate_receipt(body)


def test_write_ingress_refuses_a_nonconforming_receipt_without_writing(tmp_path):
    with pytest.raises(ValueError):
        receipts.write_ingress(
            {
                "acceptance_receipt_digest": "acc-bad",
                "source_kind": "chat_dump",
                "outcome": "NO_REUSABLE_DATA",
                "reason": "x",
                "processor_job_id": None,
                "processing_status": "NOT_STARTED",
            }
        )
    assert receipts.load_ingress("acc-bad") is None


# --- lifecycle through the real ingress path ----------------------------------


def test_nothing_to_preserve_is_an_explicit_successful_no_op():
    out = ingest.ingest_accepted_result(
        accepted_result={},
        generated_data_packet=None,
        acceptance_receipt={"status": "ACCEPTED", "receipt_digest": "acc-empty"},
    )
    assert out["outcome"] == "NO_REUSABLE_DATA"
    assert out["processor_job_id"] is None
    assert "delivery" not in out
    assert _on_disk(out) == out


def test_failure_is_never_reported_as_nothing_to_preserve():
    out = ingest.ingest_packet(
        generated_data_packet={"not": "a packet"},
        source_receipt_digest="acc-broken",
        source_kind="program_execution_outcome",
        actor="test",
    )
    assert out["outcome"] == "FAILED"
    assert out["processing_status"] == "FAILED"
    assert Path(out["packet_evidence_path"]).is_file()
    assert _on_disk(out) == out


def test_unaccepted_source_is_surfaced_as_rejected():
    out = ingest.ingest_accepted_result(
        accepted_result={},
        generated_data_packet=_packet(),
        acceptance_receipt={"status": "REJECTED", "receipt_digest": "acc-refused"},
    )
    assert out["outcome"] == "REJECTED"
    assert out["processing_status"] == "NOT_STARTED"


def test_durable_finding_routes_through_memory_owner_with_downstream_receipt(tmp_path, monkeypatch):
    _memory_owner(tmp_path, monkeypatch, "accept")
    out = ingest.ingest_packet(
        generated_data_packet=_packet(),
        source_receipt_digest="acc-routed",
        source_kind="program_execution_outcome",
        actor="test",
        independent_validation_present=True,
    )
    assert out["outcome"] == "CAPTURED"
    delivery = out["delivery"]
    memory = [d for d in delivery["details"] if d["route"] == "memory"]
    assert len(memory) == 1
    response = memory[0]["response"]
    # The only path to memory is the configured canonical-owner command.
    assert response["transport"] == "CommandTransport"
    assert response["destination_reference"] == "rec-1"
    # Provenance survives: the candidate names the source packet/agent/action.
    source = response["candidate"]["source"]
    packet = _packet()
    assert source["packet_id"] == packet["packet_id"]
    assert source["agent_id"] == packet["identity"]["agent_id"]
    assert source["action_id"] == packet["identity"]["action_id"]
    assert _on_disk(out) == out


def test_downstream_memory_refusal_is_surfaced_not_hidden(tmp_path, monkeypatch):
    _memory_owner(tmp_path, monkeypatch, "reject")
    out = ingest.ingest_packet(
        generated_data_packet=_packet(),
        source_receipt_digest="acc-refused-downstream",
        source_kind="program_execution_outcome",
        actor="test",
        independent_validation_present=True,
    )
    assert out["outcome"] == "CAPTURED"
    assert out["processing_status"] == "DEAD_LETTERED"
    assert out["delivery"]["rejected"] >= 1
    assert out["delivery"]["accepted"] == 0


def test_replayed_source_is_not_reprocessed(tmp_path, monkeypatch):
    """Source-processing idempotency: keyed on the acceptance digest, not content."""
    _memory_owner(tmp_path, monkeypatch, "accept")
    acceptance = {"status": "ACCEPTED", "receipt_digest": "acc-replay"}
    first = ingest.ingest_accepted_result(
        accepted_result={},
        generated_data_packet=_packet(),
        acceptance_receipt=acceptance,
        independent_validation_present=True,
    )
    calls: list[object] = []
    monkeypatch.setattr(ingest, "ingest_packet", lambda **kw: calls.append(kw))
    second = ingest.ingest_accepted_result(
        accepted_result={},
        generated_data_packet=_packet(),
        acceptance_receipt=acceptance,
        independent_validation_present=True,
    )
    assert calls == []
    assert second == first
    ingress_dir = Path(receipts.generated_data_receipt_root()) / "ingress"
    assert sorted(p.name for p in ingress_dir.glob("*.json")) == ["acc-replay.json"]

"""Legacy reconciliation classifier A-G and canonical admission (stage C10)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from memory_boundary_fixtures import FakeMemoryCli

from ops.memory import legacy_reconciliation as lr
from ops.memory.control_plane_client import MemoryControlPlaneClient

ROOT = Path(__file__).resolve().parents[3]
EXPORT = ROOT / "tests" / "fixtures" / "memory" / "legacy_provider_export.json"


def _candidate_payload(status: str = "admitted") -> dict:
    return {
        "status": status,
        "candidate_id": "cursor-continuation:x",
        "namespace": "cursor-governance",
        "record_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa" if status != "rejected" else None,
        "write_receipt_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        "storage_committed": status != "rejected",
        "memory_state": "active" if status in {"admitted", "duplicate"} else status,
        "reason": None if status in {"admitted", "duplicate"} else f"admission {status}",
    }


def _write_payload(status: str = "admitted") -> dict:
    return {
        "receipt_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "status": status,
        "namespace": "cursor-governance",
        "record_id": "dddddddd-dddd-dddd-dddd-dddddddddddd" if status != "rejected" else None,
        "idempotency_key": "k",
        "admission": {"reasons": ["ok"]},
        "warnings": [],
    }


def test_export_fixture_classifies_into_every_expected_class() -> None:
    namespace, records = lr.load_export(EXPORT)
    assert namespace == "cursor-governance"
    classified = lr.classify(records, namespace=namespace, forbidden={"main", "igor-workspace"})
    by_id = {c.record.record_id: c for c in classified}
    assert by_id["prov-0001"].klass == lr.CLASS_CONTINUATION
    assert by_id["prov-0001"].objective == "Finish the memory realignment"
    assert by_id["prov-0001"].next_action == "Run the cross-repo proof"
    assert by_id["prov-0002"].klass == lr.CLASS_DURABLE
    assert by_id["prov-0002"].memory_class == "insight"
    assert by_id["prov-0003"].klass == lr.CLASS_DUPLICATE
    assert by_id["prov-0004"].klass == lr.CLASS_DURABLE
    assert by_id["prov-0004"].memory_class == "decision"
    assert by_id["prov-0005"].klass == lr.CLASS_MALFORMED
    assert by_id["prov-0006"].klass == lr.CLASS_MALFORMED
    assert by_id["prov-0007"].klass == lr.CLASS_MALFORMED  # unsupported kind
    assert lr.summary(classified)[lr.CLASS_DURABLE] == 2


def test_canonical_known_and_forbidden_namespace() -> None:
    _, records = lr.load_export(EXPORT)
    known = {records[1].digest}
    classified = lr.classify(records, namespace="cursor-governance", canonical_digests=known)
    assert classified[1].klass == lr.CLASS_CANONICAL_KNOWN
    # A known digest is not re-admitted, so its repeat is a duplicate of a known record.
    assert classified[2].klass == lr.CLASS_CANONICAL_KNOWN
    forbidden = lr.classify(records, namespace="main", forbidden={"main"})
    assert {c.klass for c in forbidden} == {lr.CLASS_FORBIDDEN}


def test_pickup_json_body_is_parsed() -> None:
    record = lr.LegacyRecord(
        record_id="j1",
        text='PICKUP|agent=cursor\n{"type": "PICKUP", "active_objective": "Ship it", '
        '"next_action_contract": {"next_action": "Open the PR"}}',
    )
    (item,) = lr.classify([record], namespace="cursor-governance")
    assert item.klass == lr.CLASS_CONTINUATION
    assert item.objective == "Ship it" and item.next_action == "Open the PR"


def test_dry_run_admits_nothing_and_names_what_it_would_do(bound, fake_cli: FakeMemoryCli) -> None:
    client = MemoryControlPlaneClient(bound, runner=fake_cli.run)
    _, records = lr.load_export(EXPORT)
    classified = lr.classify(records, namespace="cursor-governance")
    lr.apply(classified, client=client, workspace=str(ROOT), namespace="cursor-governance")
    assert fake_cli.calls == []
    admitted = [c for c in classified if c.admission.get("dry_run")]
    assert {c.klass for c in admitted} == {lr.CLASS_CONTINUATION, lr.CLASS_DURABLE}


def test_apply_admits_through_the_control_plane_with_legacy_provenance(
    bound, fake_cli: FakeMemoryCli
) -> None:
    fake_cli.reply("ingest-governed-candidate", 0, _candidate_payload())
    fake_cli.reply("write", 0, _write_payload())
    client = MemoryControlPlaneClient(bound, runner=fake_cli.run)
    _, records = lr.load_export(EXPORT)
    classified = lr.classify(records, namespace="cursor-governance")
    lr.apply(
        classified, client=client, workspace=str(ROOT), namespace="cursor-governance", dry_run=False
    )
    candidate_call = next(c for c in fake_cli.calls if c[0][1] == "ingest-governed-candidate")
    candidate = json.loads(candidate_call[2] or "{}")
    assert candidate["provenance"]["producer"] == lr.RECONCILIATION_PRODUCER
    assert candidate["source"]["namespace"] == "cursor-governance"
    assert lr.LEGACY_TAG in json.dumps(candidate["knowledge"]["structured_payload"])
    write_calls = [c[0] for c in fake_cli.calls if c[0][1] == "write"]
    assert len(write_calls) == 2
    for argv in write_calls:
        assert "--tag" in argv and lr.LEGACY_TAG in argv
        assert "--idempotency-key" in argv
        assert argv[argv.index("--idempotency-key") + 1].startswith("legacy:")
    by_id = {c.record.record_id: c for c in classified}
    assert by_id["prov-0001"].admission["receipt_status"] == "admitted"
    assert by_id["prov-0004"].admission["record_id"]


def test_memory_refusal_is_class_g_not_a_crash(bound, fake_cli: FakeMemoryCli) -> None:
    fake_cli.reply("ingest-governed-candidate", 7, _candidate_payload("rejected"))
    fake_cli.reply("write", 2, _write_payload("rejected"))
    client = MemoryControlPlaneClient(bound, runner=fake_cli.run)
    _, records = lr.load_export(EXPORT)
    classified = lr.classify(records, namespace="cursor-governance")
    lr.apply(
        classified, client=client, workspace=str(ROOT), namespace="cursor-governance", dry_run=False
    )
    refused = [c for c in classified if c.klass == lr.CLASS_REFUSED]
    assert len(refused) == 3


def test_memory_unavailable_aborts_rather_than_misclassifying(
    bound, fake_cli: FakeMemoryCli
) -> None:
    fake_cli.timeout_on.add("ingest-governed-candidate")
    client = MemoryControlPlaneClient(bound, runner=fake_cli.run)
    _, records = lr.load_export(EXPORT)
    classified = lr.classify(records, namespace="cursor-governance")
    with pytest.raises(RuntimeError, match="unavailable"):
        lr.apply(
            classified,
            client=client,
            workspace=str(ROOT),
            namespace="cursor-governance",
            dry_run=False,
        )


def test_export_schema_is_enforced(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"namespace": "x", "records": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="schema"):
        lr.load_export(bad)

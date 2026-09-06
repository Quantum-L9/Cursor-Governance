"""Receipt views are structural, never a forked schema."""

from __future__ import annotations

import pytest
from memory_boundary_fixtures import close_payload, health_payload, hydration_payload

from ops.memory import receipts


def test_hydration_receipt_collects_record_ids_across_sections() -> None:
    payload = hydration_payload("r1", "r2")
    payload["sections"].append(dict(payload["sections"][0], record_ids=["r2", "r3"]))
    receipt = receipts.HydrationReceipt.parse(payload)
    assert receipt.record_ids == ("r1", "r2", "r3")
    assert receipt.has_hits is True
    assert receipt.raw is payload


def test_hydration_receipt_without_sections_is_a_clean_no_hit() -> None:
    receipt = receipts.HydrationReceipt.parse(hydration_payload())
    assert receipt.has_hits is False
    assert receipt.status == "complete"


def test_missing_required_fields_raise_invalid_receipt() -> None:
    with pytest.raises(receipts.InvalidReceiptError, match="result_digest"):
        receipts.HydrationReceipt.parse({"receipt_id": "x", "status": "complete", "task": "t"})


def test_close_receipt_committed_requires_complete_and_record() -> None:
    assert receipts.CloseReceipt.parse(close_payload()).committed is True
    assert (
        receipts.CloseReceipt.parse(close_payload(status="partial", record_id=None)).committed
        is False
    )
    assert (
        receipts.CloseReceipt.parse(close_payload(status="failed", record_id=None)).committed
        is False
    )
    assert receipts.CloseReceipt.parse(close_payload(replayed=True)).replayed is True


def test_health_receipt_separates_store_from_projection() -> None:
    healthy = receipts.HealthReceipt.parse(health_payload())
    assert healthy.canonical_ready and healthy.projection_healthy is None
    degraded = receipts.HealthReceipt.parse(
        health_payload(projection="http", projection_healthy=False)
    )
    assert degraded.canonical_ready is True
    assert degraded.projection_healthy is False
    down = receipts.HealthReceipt.parse(health_payload(store_healthy=False))
    assert down.canonical_ready is False


def test_candidate_receipt_accepted_only_when_stored() -> None:
    base = {"status": "admitted", "candidate_id": "c", "namespace": "n", "record_id": "r"}
    assert receipts.CandidateReceipt.parse(base).accepted is True
    assert receipts.CandidateReceipt.parse({**base, "status": "duplicate"}).accepted is True
    assert (
        receipts.CandidateReceipt.parse({**base, "status": "rejected", "record_id": None}).accepted
        is False
    )
    assert receipts.CandidateReceipt.parse({**base, "status": "quarantined"}).accepted is False


def test_result_digest_is_content_independent_of_key_order() -> None:
    left = receipts.result_digest({"a": 1, "b": [1, 2]})
    right = receipts.result_digest({"b": [1, 2], "a": 1})
    assert left == right and len(left) == 64


def test_validate_against_contract_is_a_noop_without_the_package(monkeypatch) -> None:
    import builtins

    real_import = builtins.__import__

    def _block(name, *args, **kwargs):
        if name.startswith("l9_graphite_memory"):
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _block)
    assert receipts.validate_against_contract(close_payload(), "CloseReceipt") is False

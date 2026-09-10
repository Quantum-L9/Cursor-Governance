"""Checked-in V2 receipt contract is the consumer SSOT."""

from __future__ import annotations

import pytest
from memory_boundary_fixtures import EXPECTED_VERSION, health_payload

from ops.memory.canonical_validation import VALIDATION_CANONICAL, CanonicalValidator
from ops.memory.receipt_contract import (
    CONTRACT_SCHEMA,
    canonical_receipt_schemas,
    compatible_package_majors,
    load_receipt_contract,
    merge_receipt_schemas,
)
from ops.memory.receipts import InvalidReceiptError
from ops.memory.runtime_binding import CANONICAL_RECEIPT_MODELS


def test_checked_in_contract_covers_every_authoritative_model() -> None:
    raw = load_receipt_contract()
    assert raw["schema"] == CONTRACT_SCHEMA
    assert raw["contract_version"] == "memory-control-plane/v1"
    assert compatible_package_majors() == frozenset({2})
    models = canonical_receipt_schemas()
    assert tuple(sorted(models)) == tuple(sorted(CANONICAL_RECEIPT_MODELS))


def test_missing_probe_uses_canonical_file() -> None:
    schemas, source = merge_receipt_schemas(None)
    assert source == "canonical-file"
    assert "WriteReceipt" in schemas
    assert "HealthReceipt" in schemas


def test_probe_fills_over_canonical_file() -> None:
    probed = {"HealthReceipt": {"type": "object", "required": ["status"]}}
    schemas, source = merge_receipt_schemas(probed)
    assert source == "probed+canonical-file"
    assert schemas["HealthReceipt"]["required"] == ["status"]
    assert "WriteReceipt" in schemas


def test_v2_package_receipt_is_accepted_across_2_2_and_2_3() -> None:
    payload = health_payload()
    payload["package_version"] = "2.2.0"
    validator = CanonicalValidator(
        schemas=canonical_receipt_schemas(),
        expected_schema_version="2.2.0",
        expected_package_version=EXPECTED_VERSION,
    )
    assert validator.validate(payload, "HealthReceipt") == VALIDATION_CANONICAL


def test_other_major_package_receipt_is_rejected() -> None:
    payload = health_payload()
    payload["package_version"] = "9.9.9"
    validator = CanonicalValidator(
        schemas=canonical_receipt_schemas(),
        expected_schema_version="2.2.0",
        expected_package_version=EXPECTED_VERSION,
    )
    with pytest.raises(InvalidReceiptError, match="not the bound"):
        validator.validate(payload, "HealthReceipt")

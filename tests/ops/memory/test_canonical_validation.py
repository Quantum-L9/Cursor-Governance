"""Canonical receipt validation actually executes on the acceptance path.

Audit CG-P1-02. Before this, `validate_against_contract` existed in
`receipts.py` and had exactly two callers, both in its own unit test. The live
path — `MemoryControlPlaneClient` — accepted every receipt on the strength of
`XReceipt.parse`, a reduced structural view that checks the handful of fields
Cursor happens to read. A payload could satisfy that and violate the memory
contract in every other respect, and Cursor would call it authoritative.

The tests here assert the *path*, not just the helper: each one drives a real
client operation and checks the outcome status, so deleting the validation
call from `_checked` fails them.
"""

from __future__ import annotations

from typing import Any

import pytest
from memory_boundary_fixtures import (
    CANONICAL_SCHEMA_VERSION,
    EXPECTED_VERSION,
    FakeMemoryCli,
    canonical_schemas,
    close_payload,
    health_payload,
)

from ops.memory import canonical_validation as cv
from ops.memory.canonical_validation import (
    VALIDATION_CANONICAL,
    VALIDATION_UNAVAILABLE,
    CanonicalValidator,
    ValidationUnavailable,
)
from ops.memory.control_plane_client import MemoryControlPlaneClient, OutcomeStatus
from ops.memory.receipts import InvalidReceiptError


@pytest.fixture
def client(bound, fake_cli: FakeMemoryCli) -> MemoryControlPlaneClient:
    return MemoryControlPlaneClient(bound, runner=fake_cli.run, session_id="sess")


def _close(client: MemoryControlPlaneClient) -> Any:
    return client.close(
        workspace="/tmp", namespace="cursor-governance", summary="s", session_id="sess"
    )


def validator(**kwargs: Any) -> CanonicalValidator:
    defaults: dict[str, Any] = {
        "schemas": canonical_schemas(),
        "schema_digest": "d" * 64,
        "expected_schema_version": CANONICAL_SCHEMA_VERSION,
        "expected_package_version": EXPECTED_VERSION,
    }
    return CanonicalValidator(**{**defaults, **kwargs})


# 1. A valid canonical receipt is accepted, and the acceptance is *recorded*
#    as canonical rather than assumed.


def test_valid_canonical_receipt_is_accepted(client, fake_cli) -> None:
    fake_cli.reply("close", 0, close_payload())
    outcome = _close(client)
    assert outcome.status is OutcomeStatus.OK
    assert outcome.integration_receipt["canonical_validation"] == VALIDATION_CANONICAL
    assert outcome.integration_receipt["contract_schema_digest"]


# 2. Locally parseable but canonical-invalid: every field the Cursor view reads
#    is present and well-formed; the contract is violated elsewhere.


def test_locally_parseable_but_canonically_invalid_is_rejected(client, fake_cli) -> None:
    payload = close_payload()
    payload["warnings"] = "not a list"  # the view never reads its element type
    fake_cli.reply("close", 0, payload)
    outcome = _close(client)
    assert outcome.status is OutcomeStatus.INVALID_RECEIPT
    assert "violates the canonical contract" in (outcome.error or "")
    # The structural view alone would have taken it.
    from ops.memory.receipts import CloseReceipt

    assert CloseReceipt.parse(payload).committed is True


# 3. A canonical-required field the Cursor view does not read.


def test_missing_canonical_required_field_is_rejected(client, fake_cli) -> None:
    payload = close_payload()
    del payload["namespace"]
    fake_cli.reply("close", 0, payload)
    assert _close(client).status is OutcomeStatus.INVALID_RECEIPT


# 4. Wrong type / malformed identifier.


def test_malformed_uuid_is_rejected(client, fake_cli) -> None:
    payload = close_payload()
    payload["receipt_id"] = "not-a-uuid"
    fake_cli.reply("close", 0, payload)
    outcome = _close(client)
    assert outcome.status is OutcomeStatus.INVALID_RECEIPT
    assert "receipt_id" in (outcome.error or "")


def test_wrong_scalar_type_is_rejected(client, fake_cli) -> None:
    payload = close_payload()
    payload["replayed"] = "yes"
    fake_cli.reply("close", 0, payload)
    assert _close(client).status is OutcomeStatus.INVALID_RECEIPT


# 5/6. Contract lineage: an incompatible schema version, and a future major.


def test_incompatible_schema_version_is_rejected() -> None:
    payload = health_payload()
    payload["schema_version"] = "1.9.0"
    with pytest.raises(InvalidReceiptError, match="incompatible schema lineage"):
        validator().validate(payload, "HealthReceipt")


def test_unexpected_future_major_version_is_rejected() -> None:
    payload = health_payload()
    payload["schema_version"] = "9.0.0"
    with pytest.raises(InvalidReceiptError, match="later major"):
        validator().validate(payload, "HealthReceipt")


def test_matching_schema_version_passes() -> None:
    assert validator().validate(health_payload(), "HealthReceipt") == VALIDATION_CANONICAL


# 7. A malformed authorization receipt: the nested object Cursor does not read
#    field-by-field, and would otherwise wave through.


def test_malformed_authorization_receipt_is_rejected(client, fake_cli) -> None:
    payload = close_payload()
    payload["authorization"] = ["allowed"]
    schemas = canonical_schemas()
    schemas["CloseReceipt"]["properties"]["authorization"] = {"type": "object"}
    client.validator = validator(schemas=schemas)
    fake_cli.reply("close", 0, payload)
    assert _close(client).status is OutcomeStatus.INVALID_RECEIPT


# 8. When canonical validation cannot run, structural acceptance is not a
#    substitute — the operation is not a success.


def test_required_validation_without_schemas_is_not_success(client, fake_cli) -> None:
    client.validator = validator(schemas=None, required=True)
    fake_cli.reply("close", 0, close_payload())
    outcome = _close(client)
    assert outcome.status is OutcomeStatus.VALIDATION_UNAVAILABLE
    assert outcome.ok is False
    assert outcome.status is not OutcomeStatus.OK


def test_required_validation_missing_one_model_is_not_success(client, fake_cli) -> None:
    schemas = canonical_schemas()
    del schemas["CloseReceipt"]
    client.validator = validator(schemas=schemas, required=True)
    fake_cli.reply("close", 0, close_payload())
    assert _close(client).status is OutcomeStatus.VALIDATION_UNAVAILABLE


def test_unrequired_validation_without_schemas_degrades_visibly(client, fake_cli) -> None:
    """Not required: the operation proceeds, but the receipt says plainly that
    nothing canonical was checked. Silence is what the audit found."""
    client.validator = validator(schemas=None, required=False)
    fake_cli.reply("close", 0, close_payload())
    outcome = _close(client)
    assert outcome.status is OutcomeStatus.OK
    assert outcome.integration_receipt["canonical_validation"] == VALIDATION_UNAVAILABLE


def test_requirement_is_read_from_the_environment(monkeypatch) -> None:
    monkeypatch.delenv(cv.ENV_REQUIRE_VALIDATION, raising=False)
    assert cv.require_canonical_validation({}) is False
    assert cv.require_canonical_validation({cv.ENV_REQUIRE_VALIDATION: "1"}) is True
    assert cv.require_canonical_validation({cv.ENV_REQUIRE_VALIDATION: "0"}) is False


# 9. Provenance: a receipt that is shape-valid but written by another release.


def test_receipt_from_the_wrong_release_is_rejected() -> None:
    payload = health_payload()
    payload["package_version"] = "9.9.9"
    with pytest.raises(InvalidReceiptError, match="not the bound"):
        validator().validate(payload, "HealthReceipt")


def test_provenance_is_only_checked_when_the_receipt_carries_it() -> None:
    """A receipt with no provenance fields is not rejected for lacking them —
    the schema decides what is required, not this check."""
    assert validator().validate(close_payload(), "CloseReceipt") == VALIDATION_CANONICAL


# 10. The canonical path is asserted explicitly: not "a helper exists" but
#     "the client calls it, for every authoritative receipt".


def test_every_authoritative_operation_validates_canonically(bound, fake_cli) -> None:
    """The defect was a helper with no callers. This pins the wiring."""
    seen: list[str] = []

    class Recording(CanonicalValidator):
        def validate(self, raw: Any, model_name: str) -> str:
            seen.append(model_name)
            return super().validate(raw, model_name)

    client = MemoryControlPlaneClient(
        bound,
        runner=fake_cli.run,
        session_id="sess",
        validator=Recording(
            schemas=canonical_schemas(),
            expected_schema_version=CANONICAL_SCHEMA_VERSION,
            expected_package_version=EXPECTED_VERSION,
        ),
    )
    fake_cli.reply("close", 0, close_payload())
    fake_cli.reply("health", 0, health_payload())
    _close(client)
    client.health()
    assert seen == ["CloseReceipt", "HealthReceipt"]


def test_client_binds_its_validator_to_the_bound_release(bound, fake_cli) -> None:
    client = MemoryControlPlaneClient(bound, runner=fake_cli.run)
    assert client.validator.available is True
    assert client.validator.schema_digest == bound.schema_digest
    assert client.validator.expected_package_version == bound.memory_version


def test_validation_unavailable_is_not_an_invalid_receipt() -> None:
    """The two are different verdicts and must not be collapsed: one says the
    receipt is wrong, the other says nothing was checked."""
    assert not issubclass(ValidationUnavailable, InvalidReceiptError)
    with pytest.raises(ValidationUnavailable):
        validator(schemas=None, required=True).validate({}, "CloseReceipt")


def test_non_object_payload_is_an_invalid_receipt() -> None:
    with pytest.raises(InvalidReceiptError, match="not a JSON object"):
        validator().validate(["nope"], "CloseReceipt")

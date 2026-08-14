from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .digests import digest_object, normalize_digest
from .errors import AdapterFailure, CanonicalErrorCode

CANONICAL_RENDERED_SCHEMA = "program-execution-controller.rendered-contract.v2"
FORBIDDEN_ACTIONS = {
    "merge",
    "auto_merge",
    "admin_merge",
    "force_push",
    "test_weakening",
}


@dataclass(frozen=True)
class ContractBinding:
    task_id: str
    program_lock_digest: str
    rendered_contract_digest: str
    requested_actions: tuple[str, ...]
    allowed_actions: tuple[str, ...]
    raw: dict[str, Any]


def _allowed_actions(value: Any) -> set[str]:
    if isinstance(value, list):
        return {item for item in value if isinstance(item, str) and bool(item.strip())}
    if isinstance(value, Mapping):
        return {
            key
            for key, allowed in value.items()
            if isinstance(key, str) and bool(key.strip()) and allowed is True
        }
    return set()


def _require_field(
    raw: dict[str, Any],
    *keys: str,
    code: CanonicalErrorCode,
    detail: str,
    reason: str,
) -> str:
    for key in keys:
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return value
    raise AdapterFailure(code, detail, reason)


def _requested_actions(raw: Mapping[str, Any]) -> tuple[str, ...]:
    value = raw.get("requested_actions")
    if not isinstance(value, list) or not value:
        raise AdapterFailure(
            CanonicalErrorCode.VALIDATION_FAILURE,
            "Rendered Contract requires non-empty requested_actions",
            "REQUESTED_ACTIONS_MISSING_OR_INVALID",
        )
    requested: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise AdapterFailure(
                CanonicalErrorCode.VALIDATION_FAILURE,
                "Rendered Contract requested_actions must contain non-empty strings",
                "REQUESTED_ACTION_INVALID",
            )
        requested.append(item)
    if len(set(requested)) != len(requested):
        raise AdapterFailure(
            CanonicalErrorCode.VALIDATION_FAILURE,
            "Rendered Contract requested_actions must be unique",
            "REQUESTED_ACTION_DUPLICATE",
        )
    return tuple(requested)


def _authority_ceiling(raw: Mapping[str, Any], requested: tuple[str, ...]) -> set[str]:
    if raw.get("schema") == CANONICAL_RENDERED_SCHEMA:
        if raw.get("remote_mutation") != "denied":
            raise AdapterFailure(
                CanonicalErrorCode.AUTHORIZATION_INFLATION,
                "Canonical Rendered Contract must deny remote mutation",
                "CANONICAL_REMOTE_MUTATION_NOT_DENIED",
            )
        # The Controller already proves requested_actions against the Task Card
        # authorization ceiling before rendering v2. The rendered schema is closed
        # and deliberately does not duplicate authorization_ceiling/allowed_actions.
        return set(requested)
    ceiling = raw.get("authorization_ceiling") or raw.get("allowed_actions") or []
    return _allowed_actions(ceiling)


def validate_contract(
    contract: Mapping[str, Any],
    *,
    expected_program_lock_digest: str | None = None,
) -> ContractBinding:
    raw = dict(contract)
    task_id = _require_field(
        raw,
        "task_id",
        "id",
        code=CanonicalErrorCode.VALIDATION_FAILURE,
        detail="Rendered Contract is missing task_id",
        reason="CONTRACT_TASK_ID_MISSING",
    )
    program_digest = _require_field(
        raw,
        "program_lock_digest",
        "program_digest",
        code=CanonicalErrorCode.PROGRAM_LOCK_STALE,
        detail="Rendered Contract is missing Program Lock digest",
        reason="PROGRAM_DIGEST_MISSING",
    )
    normalized_program = normalize_digest(program_digest)
    if expected_program_lock_digest:
        expected = normalize_digest(expected_program_lock_digest)
        if normalized_program != expected:
            raise AdapterFailure(
                CanonicalErrorCode.PROGRAM_LOCK_STALE,
                "Rendered Contract does not match the active Program Lock",
                "PROGRAM_DIGEST_MISMATCH",
            )
    contract_digest = _require_field(
        raw,
        "rendered_contract_digest",
        "contract_digest",
        code=CanonicalErrorCode.VALIDATION_FAILURE,
        detail="Rendered Contract digest is missing",
        reason="CONTRACT_DIGEST_MISSING",
    )
    normalized_contract = normalize_digest(contract_digest)
    if "contract_digest" in raw:
        body = dict(raw)
        body.pop("contract_digest", None)
        calculated = digest_object(body)
        if calculated != normalized_contract:
            raise AdapterFailure(
                CanonicalErrorCode.EVIDENCE_INVALID_OR_STALE,
                "Rendered Contract digest does not match its body",
                "CONTRACT_DIGEST_MISMATCH",
            )

    requested = _requested_actions(raw)
    allowed = _authority_ceiling(raw, requested)
    if not set(requested) <= allowed:
        raise AdapterFailure(
            CanonicalErrorCode.AUTHORIZATION_INFLATION,
            "Requested actions exceed the Rendered Contract authority ceiling",
            "REQUESTED_ACTIONS_EXCEED_CEILING",
        )
    forbidden = set(requested) & FORBIDDEN_ACTIONS
    if forbidden:
        raise AdapterFailure(
            CanonicalErrorCode.AUTHORIZATION_INFLATION,
            f"Globally forbidden actions requested: {sorted(forbidden)}",
            "GLOBALLY_FORBIDDEN_ACTION",
        )
    return ContractBinding(
        task_id=task_id,
        program_lock_digest=normalized_program,
        rendered_contract_digest=normalized_contract,
        requested_actions=requested,
        allowed_actions=tuple(sorted(allowed)),
        raw=raw,
    )

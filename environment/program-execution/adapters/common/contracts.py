from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .digests import digest_object, normalize_digest
from .errors import AdapterFailure, CanonicalErrorCode

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
        return {str(item) for item in value}
    if isinstance(value, Mapping):
        return {str(key) for key, allowed in value.items() if bool(allowed)}
    return set()


def _require_field(
    raw: dict[str, Any], *keys: str, code: CanonicalErrorCode, detail: str, reason: str
) -> str:
    for key in keys:
        value = raw.get(key)
        if isinstance(value, str) and value:
            return value
    raise AdapterFailure(code, detail, reason)


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
    requested = tuple(str(item) for item in raw.get("requested_actions") or [])
    ceiling = raw.get("authorization_ceiling") or raw.get("allowed_actions") or []
    allowed = _allowed_actions(ceiling)
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

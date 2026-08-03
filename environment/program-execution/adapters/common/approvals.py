from __future__ import annotations

import datetime as dt
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .digests import normalize_digest
from .errors import AdapterFailure, CanonicalErrorCode


@dataclass(frozen=True)
class ExactApproval:
    approval_id: str
    action: str
    task_id: str
    program_lock_digest: str
    contract_digest: str
    approved_by: str
    expires_at: str


def require_exact_approval(
    contract: Mapping[str, Any],
    action: str,
) -> ExactApproval:
    value = contract.get("approval")
    if not isinstance(value, Mapping):
        raise AdapterFailure(
            CanonicalErrorCode.AUTHORIZATION_INFLATION,
            f"Exact approval required for {action}",
            "APPROVAL_MISSING",
        )
    required = {
        "approval_id",
        "action",
        "task_id",
        "program_lock_digest",
        "contract_digest",
        "approved_by",
        "expires_at",
    }
    missing = sorted(required - set(value))
    if missing:
        raise AdapterFailure(
            CanonicalErrorCode.AUTHORIZATION_INFLATION,
            f"Approval fields missing: {missing}",
            "APPROVAL_MALFORMED",
        )
    if value["action"] != action:
        raise AdapterFailure(
            CanonicalErrorCode.AUTHORIZATION_INFLATION,
            "Approval action does not match the requested action",
            "APPROVAL_ACTION_MISMATCH",
        )
    task_id = contract.get("task_id") or contract.get("id")
    if value["task_id"] != task_id:
        raise AdapterFailure(
            CanonicalErrorCode.AUTHORIZATION_INFLATION,
            "Approval task does not match the Rendered Contract",
            "APPROVAL_TASK_MISMATCH",
        )
    program_digest = contract.get("program_lock_digest") or contract.get("program_digest")
    contract_digest = contract.get("rendered_contract_digest") or contract.get("contract_digest")
    if normalize_digest(str(value["program_lock_digest"])) != normalize_digest(str(program_digest)):
        raise AdapterFailure(
            CanonicalErrorCode.PROGRAM_LOCK_STALE,
            "Approval Program Lock digest mismatch",
            "APPROVAL_PROGRAM_DIGEST_MISMATCH",
        )
    if normalize_digest(str(value["contract_digest"])) != normalize_digest(str(contract_digest)):
        raise AdapterFailure(
            CanonicalErrorCode.EVIDENCE_INVALID_OR_STALE,
            "Approval contract digest mismatch",
            "APPROVAL_CONTRACT_DIGEST_MISMATCH",
        )
    expires = dt.datetime.fromisoformat(str(value["expires_at"]).replace("Z", "+00:00"))
    if expires <= dt.datetime.now(dt.UTC):
        raise AdapterFailure(
            CanonicalErrorCode.EVIDENCE_INVALID_OR_STALE,
            "Approval has expired",
            "APPROVAL_EXPIRED",
        )
    return ExactApproval(
        approval_id=str(value["approval_id"]),
        action=action,
        task_id=str(task_id),
        program_lock_digest=normalize_digest(str(program_digest)),
        contract_digest=normalize_digest(str(contract_digest)),
        approved_by=str(value["approved_by"]),
        expires_at=str(value["expires_at"]),
    )

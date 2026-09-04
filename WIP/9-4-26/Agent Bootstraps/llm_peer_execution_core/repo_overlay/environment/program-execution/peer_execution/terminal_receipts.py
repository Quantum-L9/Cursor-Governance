from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .core_receipts import verification_receipt
from .digests import digest_object

_ZERO_DIGEST = "sha256:" + "0" * 64


def _required_string(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _string_list(name: str, value: object) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{name} must be an array of strings")
    return list(value)


def _mapping_list(name: str, value: object) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value):
        raise ValueError(f"{name} must be an array of objects")
    return [dict(item) for item in value]


def verification_from_payload(
    contract: Mapping[str, Any], payload: Mapping[str, Any]
) -> dict[str, Any]:
    gates_raw = payload.get("gates")
    if not isinstance(gates_raw, Mapping):
        raise ValueError("verification driver payload gates must be an object")
    gates = {
        _required_string("gate id", key): _required_string("gate status", value)
        for key, value in gates_raw.items()
    }
    candidate_sha = payload.get("candidate_sha")
    if candidate_sha is not None and not isinstance(candidate_sha, str):
        raise ValueError("candidate_sha must be a string or null")
    return verification_receipt(
        contract,
        candidate_sha=candidate_sha,
        declared_changed_files=_string_list(
            "declared_changed_files", payload.get("declared_changed_files")
        ),
        observed_changed_files=_string_list(
            "observed_changed_files", payload.get("observed_changed_files")
        ),
        validations=_mapping_list("validations", payload.get("validations")),
        gates=gates,
    )


def remote_action_from_payload(
    contract: Mapping[str, Any],
    payload: Mapping[str, Any],
    *,
    approval_id: str,
    evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    action = _required_string("remote action", payload.get("action"))
    result = payload.get("result")
    if not isinstance(result, Mapping):
        raise ValueError("remote action result must be an object")
    body = {
        "schema": "program-execution-adapter.remote-action-receipt.v1",
        "action": action,
        "repository": _required_string("repository", contract.get("repository")),
        "task_id": _required_string("task_id", contract.get("task_id") or contract.get("id")),
        "program_lock_digest": contract.get("program_lock_digest")
        or contract.get("program_digest"),
        "contract_digest": contract.get("contract_digest")
        or contract.get("rendered_contract_digest"),
        "approval_id": approval_id,
        "result": dict(result),
        "evidence": evidence,
    }
    body["receipt_digest"] = digest_object(body)
    return body


def deployment_from_payload(
    contract: Mapping[str, Any],
    payload: Mapping[str, Any],
    *,
    approval_id: str,
) -> dict[str, Any]:
    operation = _required_string("deployment operation", payload.get("operation"))
    result = payload.get("result")
    if not isinstance(result, Mapping):
        raise ValueError("deployment result must be an object")
    body = {
        "schema": "program-execution-adapter.deployment-receipt.v1",
        "operation": operation,
        "repository": _required_string("repository", contract.get("repository")),
        "environment": _required_string("environment", contract.get("environment")),
        "ref": _required_string(
            "deployment ref",
            contract.get("candidate_sha") or contract.get("ref") or "READ_ONLY",
        ),
        "artifact_digest": str(contract.get("artifact_digest") or _ZERO_DIGEST),
        "approval_id": approval_id,
        "rollback_plan_digest": str(
            contract.get("rollback_plan_digest") or _ZERO_DIGEST
        ),
        "result": dict(result),
    }
    body["receipt_digest"] = digest_object(body)
    return body

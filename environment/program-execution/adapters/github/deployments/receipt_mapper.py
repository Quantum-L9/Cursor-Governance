from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from adapters.common.digests import digest_object

_ZERO_DIGEST = "sha256:" + "0" * 64


def _receipt(
    contract: Mapping[str, Any],
    result: Mapping[str, Any],
    *,
    operation: str,
    approval_id: str,
) -> dict[str, Any]:
    body = {
        "schema": "program-execution-adapter.deployment-receipt.v1",
        "operation": operation,
        "repository": str(contract["repository"]),
        "environment": str(contract["environment"]),
        "ref": str(contract.get("candidate_sha") or contract.get("ref") or "READ_ONLY"),
        "artifact_digest": str(contract.get("artifact_digest") or _ZERO_DIGEST),
        "approval_id": approval_id,
        "rollback_plan_digest": str(contract.get("rollback_plan_digest") or _ZERO_DIGEST),
        "result": dict(result),
    }
    body["receipt_digest"] = digest_object(body)
    return body


def environment_read_receipt(
    contract: Mapping[str, Any],
    result: Mapping[str, Any],
) -> dict[str, Any]:
    return _receipt(
        contract,
        result,
        operation="read_environment",
        approval_id="READ_ONLY",
    )


def deployment_receipt(
    contract: Mapping[str, Any],
    result: Mapping[str, Any],
    approval_id: str,
) -> dict[str, Any]:
    return _receipt(
        contract,
        result,
        operation="create_deployment_record",
        approval_id=approval_id,
    )

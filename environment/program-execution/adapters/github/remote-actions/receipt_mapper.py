from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from adapters.common.digests import digest_object


def remote_receipt(
    contract: Mapping[str, Any],
    *,
    action: str,
    approval_id: str,
    result: Mapping[str, Any],
    evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    body = {
        "schema": "program-execution-adapter.remote-action-receipt.v1",
        "action": action,
        "repository": str(contract["repository"]),
        "task_id": str(contract.get("task_id") or contract.get("id")),
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

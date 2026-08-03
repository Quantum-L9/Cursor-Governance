from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from adapters.common.core_receipts import attempt_receipt


def map_result(contract: Mapping[str, Any], host: Mapping[str, Any]) -> dict[str, Any]:
    payload = host.get("result_payload")
    if not isinstance(payload, Mapping):
        payload = host
    return attempt_receipt(
        contract,
        candidate_sha=payload.get("candidate_sha"),
        changed_files=list(payload.get("changed_files") or []),
        validation_results=list(payload.get("validation_results") or []),
        produced_evidence=[
            {
                "type": "claude_code_result",
                "session_id": host.get("session_id"),
                "is_error": host.get("is_error"),
                "num_turns": host.get("num_turns"),
            }
        ],
        residual_unknowns=list(payload.get("residual_unknowns") or []),
        claimed_status="failed" if host.get("is_error") else "completed",
    )

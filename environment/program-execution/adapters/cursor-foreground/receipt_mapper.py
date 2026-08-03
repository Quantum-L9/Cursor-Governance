from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from adapters.common.core_receipts import attempt_receipt


def map_result(contract: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
    return attempt_receipt(
        contract,
        candidate_sha=result.get("candidate_sha"),
        changed_files=list(result.get("changed_files") or []),
        validation_results=list(result.get("validation_results") or []),
        produced_evidence=[dict(result)],
        residual_unknowns=list(result.get("residual_unknowns") or []),
        claimed_status=str(result.get("claimed_status") or "completed"),
    )

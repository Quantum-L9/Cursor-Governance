from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from adapters.common.core_receipts import attempt_receipt


def map_artifact(contract: Mapping[str, Any], value: Mapping[str, Any]) -> dict[str, Any]:
    return attempt_receipt(
        contract,
        candidate_sha=value.get("candidate_sha"),
        changed_files=list(value.get("changed_files") or []),
        validation_results=list(value.get("validation_results") or []),
        produced_evidence=[dict(value)],
        residual_unknowns=list(value.get("residual_unknowns") or []),
    )

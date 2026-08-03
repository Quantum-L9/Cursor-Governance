from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from adapters.common.core_receipts import attempt_receipt


def map_root_autonomy_artifact(
    contract: Mapping[str, Any],
    artifact: Mapping[str, Any],
) -> dict[str, Any]:
    return attempt_receipt(
        contract,
        candidate_sha=artifact.get("candidate_sha"),
        changed_files=list(artifact.get("changed_files") or []),
        validation_results=list(artifact.get("validation_results") or []),
        produced_evidence=[dict(artifact)],
        residual_unknowns=list(artifact.get("residual_unknowns") or []),
        claimed_status=str(artifact.get("claimed_status") or "completed"),
    )

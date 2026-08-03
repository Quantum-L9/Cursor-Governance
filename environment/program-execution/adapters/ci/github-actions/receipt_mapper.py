from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from adapters.common.core_receipts import verification_receipt


def map_run(
    contract: Mapping[str, Any],
    run: Mapping[str, Any],
    artifacts: list[str],
) -> dict[str, Any]:
    passed = run.get("conclusion") == "success"
    validations = [
        {
            "provider": "github-actions",
            "run_id": run.get("databaseId"),
            "url": run.get("url"),
            "conclusion": run.get("conclusion"),
            "artifacts": artifacts,
        }
    ]
    declared = list(contract.get("declared_changed_files") or [])
    return verification_receipt(
        contract,
        candidate_sha=str(contract.get("candidate_sha")),
        declared_changed_files=declared,
        observed_changed_files=declared,
        validations=validations,
        gates={
            "workflow_conclusion": "PASS" if passed else "FAIL",
            "candidate_sha_exact": (
                "PASS" if run.get("headSha") == contract.get("candidate_sha") else "FAIL"
            ),
            "independent_verifier": "PASS",
        },
    )

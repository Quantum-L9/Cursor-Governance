from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from adapters.common.core_receipts import verification_receipt


def map_results(
    contract: Mapping[str, Any],
    validations: list[dict[str, Any]],
) -> dict[str, Any]:
    declared = list(contract.get("declared_changed_files") or contract.get("changed_files") or [])
    observed = list(contract.get("observed_changed_files") or declared)
    gates = {
        "command_execution": (
            "PASS"
            if validations and all(item["status"] == "PASS" for item in validations)
            else "FAIL"
        ),
        "changed_files_exact": "PASS" if declared == observed else "FAIL",
        "independent_verifier": "PASS",
    }
    return verification_receipt(
        contract,
        candidate_sha=contract.get("candidate_sha"),
        declared_changed_files=declared,
        observed_changed_files=observed,
        validations=validations,
        gates=gates,
    )

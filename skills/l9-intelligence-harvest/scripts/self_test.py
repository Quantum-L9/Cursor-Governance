#!/usr/bin/env python3
from qualify_nuggets import qualify
from rank_nuggets import rank
from validate_harvest import validate


def portability(runtime_required=False, dependency=None):
    return {
        "donor_identity_independent": True,
        "donor_execution_authority_independent": True,
        "donor_infrastructure_independent": True,
        "incidental_implementation_independent": True,
        "donor_runtime_required": runtime_required,
        "external_dependency": dependency,
    }


def main():
    concept = {
        "id": "n1",
        "name": "x",
        "problem": "p",
        "semantic_contract": "portable behavior contract",
        "disposition": "PORT",
        "beneficiary_destination": "dest",
        "evidence_ids": ["e1"],
        "risks": ["r"],
        "acceptance_tests": [{"given": "g", "when": "w", "then": "t", "must_not": "m"}],
        "portability": portability(),
        "beneficiary_fit": {
            "comparison": "DONOR_STRONGER",
            "existing_owner": "dest",
            "merge_decision": "adopt semantics",
            "compatibility_risk": "low",
        },
        "leverage": 5,
        "compounding": 4,
        "rank_score": None,
    }
    qualified, _ = qualify(concept)
    assert qualified["nugget"]
    harvest = {
        "schema_version": "1.1.0",
        "request": {
            "request_id": "r",
            "donor": "d",
            "beneficiary": "b",
            "harvest_target": "t",
            "access_mode": "read-only",
            "depth": "exhaustive",
            "secrets_policy": "redact",
            "language": "as-donor",
            "brief": False,
        },
        "source_identity": {},
        "inventory": [],
        "system": {
            "identity": "self-test",
            "workflows": [],
            "control_flow": [],
            "ownership_boundaries": [],
            "dependencies": [],
            "must_not_own": [],
        },
        "surfaces": [],
        "drift": [],
        "evidence": [
            {
                "id": "e1",
                "epistemic": "CONFIRMED",
                "source": "s",
                "locator": {"kind": "symbol", "value": "x"},
                "claim": "Observed behavior exists.",
                "secret_redacted": False,
            }
        ],
        "concepts": [qualified],
        "safety": [],
        "unknowns": [],
        "highest_leverage_nugget": None,
        "status": "PASS",
    }
    assert rank(harvest)["highest_leverage_nugget"] == "n1"
    assert not validate(harvest)
    print("PASS")


if __name__ == "__main__":
    main()

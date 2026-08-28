import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from qualify_nuggets import qualify


def closed_fit(comparison="DONOR_STRONGER"):
    return {
        "comparison": comparison,
        "existing_owner": "b",
        "merge_decision": "bounded transfer",
        "compatibility_risk": "low",
    }


def closed_portability():
    return {
        "donor_identity_independent": True,
        "donor_execution_authority_independent": True,
        "donor_infrastructure_independent": True,
        "incidental_implementation_independent": True,
        "donor_runtime_required": False,
        "external_dependency": None,
    }


def test_requires_all_contract_fields():
    concept = {
        "id": "x",
        "name": "x",
        "problem": "p",
        "semantic_contract": "portable contract",
        "disposition": "PORT",
        "beneficiary_destination": "b",
        "evidence_ids": ["e"],
        "risks": ["r"],
        "acceptance_tests": [{"given": "g", "when": "w", "then": "t", "must_not": "m"}],
        "portability": closed_portability(),
        "beneficiary_fit": closed_fit(),
    }
    qualified, checks = qualify(concept)
    assert qualified["nugget"] is True
    assert all(checks.values())
    concept["evidence_ids"] = []
    qualified, _ = qualify(concept)
    assert qualified["nugget"] is False


def test_portability_is_part_of_qualification():
    concept = {
        "id": "x",
        "name": "x",
        "problem": "p",
        "semantic_contract": "portable contract",
        "disposition": "PORT",
        "beneficiary_destination": "b",
        "evidence_ids": ["e"],
        "risks": ["r"],
        "acceptance_tests": [{"given": "g", "when": "w", "then": "t", "must_not": "m"}],
        "portability": closed_portability(),
        "beneficiary_fit": closed_fit(),
    }
    concept["portability"]["donor_infrastructure_independent"] = False
    qualified, checks = qualify(concept)
    assert qualified["nugget"] is False
    assert checks["portability_closure"] is False

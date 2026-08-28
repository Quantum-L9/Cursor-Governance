import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from validate_harvest import validate


def base():
    return {
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
        "system": {},
        "surfaces": [],
        "drift": [],
        "evidence": [],
        "concepts": [],
        "safety": [],
        "unknowns": [],
        "highest_leverage_nugget": None,
        "status": "PASS",
    }


def test_unresolved_evidence_fails():
    harvest = base()
    harvest["concepts"] = [
        {
            "id": "c",
            "name": "n",
            "problem": "p",
            "disposition": "REJECT",
            "beneficiary_destination": None,
            "evidence_ids": ["missing"],
            "risks": [],
            "acceptance_tests": [],
            "nugget": False,
            "leverage": None,
            "compounding": None,
            "rank_score": None,
        }
    ]
    assert any("unresolved evidence" in error for error in validate(harvest))


def test_confirmed_claim_requires_resolvable_locator():
    harvest = base()
    harvest["evidence"] = [
        {
            "id": "e",
            "epistemic": "CONFIRMED",
            "source": "d",
            "locator": {"kind": "unknown", "value": ""},
            "claim": "Observed.",
        }
    ]
    assert any("lacks resolvable locator" in error for error in validate(harvest))

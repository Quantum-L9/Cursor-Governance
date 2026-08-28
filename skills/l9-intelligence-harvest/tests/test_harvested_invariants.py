import json
import sys
from pathlib import Path

import yaml

PACK = Path(__file__).parents[1]
sys.path.insert(0, str(PACK / "scripts"))

from qualify_nuggets import portability_closed, qualify  # noqa: E402 - sys.path bootstrap above
from render_brief import render  # noqa: E402 - sys.path bootstrap above
from validate_harvest import validate  # noqa: E402 - sys.path bootstrap above


def schema():
    return json.loads((PACK / "contracts/harvest-ir.schema.json").read_text())


def policy():
    return yaml.safe_load((PACK / "policies/harvest-policy.yaml").read_text())


def base_system():
    return {
        "identity": "system",
        "workflows": [],
        "control_flow": [],
        "ownership_boundaries": [],
        "dependencies": [],
        "must_not_own": [],
    }


def base_harvest():
    return {
        "schema_version": "1.1.0",
        "request": {
            "request_id": "r",
            "donor": "d",
            "beneficiary": "b",
            "harvest_target": "t",
            "access_mode": "read-only",
            "depth": "standard",
            "secrets_policy": "redact",
            "language": "as-donor",
            "brief": False,
        },
        "source_identity": {},
        "inventory": [],
        "system": base_system(),
        "surfaces": [],
        "drift": [],
        "evidence": [],
        "concepts": [],
        "safety": [],
        "unknowns": [],
        "highest_leverage_nugget": None,
        "status": "PASS",
    }


def closed_portability(runtime=False):
    return {
        "donor_identity_independent": True,
        "donor_execution_authority_independent": True,
        "donor_infrastructure_independent": True,
        "incidental_implementation_independent": True,
        "donor_runtime_required": runtime,
        "external_dependency": (
            {"target": "runtime", "probe": "runtime --version", "failure_behavior": "BLOCKED"}
            if runtime
            else None
        ),
    }


def closed_fit(comparison="DONOR_STRONGER"):
    return {
        "comparison": comparison,
        "existing_owner": "beneficiary",
        "merge_decision": "preserve stronger semantics",
        "compatibility_risk": "low",
    }


def candidate(disposition="PORT", comparison="DONOR_STRONGER"):
    return {
        "id": "c1",
        "name": "candidate",
        "problem": "stable problem",
        "semantic_contract": "portable semantic contract",
        "disposition": disposition,
        "beneficiary_destination": "destination",
        "evidence_ids": ["e1"],
        "risks": ["risk"],
        "acceptance_tests": [{"given": "g", "when": "w", "then": "t", "must_not": "m"}],
        "portability": closed_portability(),
        "beneficiary_fit": closed_fit(comparison),
        "nugget": False,
        "leverage": 5,
        "compounding": 5,
        "rank_score": None,
    }


def test_evidence_precedence_and_wrapper_resolution():
    p = policy()
    assert p["governing_laws"]["evidence_precedence"]["require_wrapper_resolution"] is True
    h = base_harvest()
    h["surfaces"] = [
        {
            "item": "alias",
            "source": "s",
            "visibility": "public",
            "is_wrapper": True,
            "resolved_target": None,
            "evidence_ids": [],
        }
    ]
    assert any("wrapper has no resolved execution target" in error for error in validate(h))


def test_system_reconstruction_shape_is_required():
    required = set(schema()["properties"]["system"]["required"])
    assert required == {
        "identity",
        "workflows",
        "control_flow",
        "ownership_boundaries",
        "dependencies",
        "must_not_own",
    }


def test_epistemics_are_closed_enum():
    enum = schema()["properties"]["evidence"]["items"]["properties"]["epistemic"]["enum"]
    assert enum == ["CONFIRMED", "INFERENCE", "UNKNOWN"]


def test_canonicality_states_are_closed():
    expected = {
        "canonical",
        "active",
        "candidate",
        "duplicate",
        "legacy",
        "generated",
        "archive",
        "sensitive",
        "unknown",
    }
    assert set(policy()["classification"]) == expected
    enum = schema()["properties"]["inventory"]["items"]["properties"]["classification"]["enum"]
    assert set(enum) == expected


def test_qualification_contract_is_complete():
    qualified, checks = qualify(candidate())
    assert qualified["nugget"] is True
    assert set(checks) == {
        "stable_problem",
        "semantic_contract",
        "real_evidence",
        "beneficiary_destination",
        "explicit_risks",
        "acceptance_test",
        "beneficiary_fit",
        "portability_closure",
    }


def test_disposition_taxonomy_is_exact():
    expected = {
        "PORT",
        "PORT_WITH_HARDENING",
        "CONFIGURE",
        "MERGE_WITH_EXISTING",
        "KEEP_LOCAL",
        "MIGRATION_CONTEXT",
        "REJECT",
        "UNKNOWN",
    }
    enum = schema()["properties"]["concepts"]["items"]["properties"]["disposition"]["enum"]
    assert set(enum) == expected


def test_beneficiary_stronger_blocks_port():
    concept = candidate(comparison="BENEFICIARY_STRONGER")
    qualified, checks = qualify(concept)
    assert qualified["nugget"] is False
    assert checks["beneficiary_fit"] is False
    h = base_harvest()
    h["concepts"] = [concept]
    assert any("cannot PORT over stronger beneficiary semantics" in error for error in validate(h))


def test_no_beneficiary_implementation_authority():
    p = policy()
    assert p["mutation"]["beneficiary"] == "forbidden"
    assert p["mutation"]["beneficiary_implementation"] == "forbidden"


def test_renderer_refuses_invalid_harvest():
    h = base_harvest()
    h["system"] = {}
    try:
        render(h)
    except ValueError as exc:
        assert "renderer write forbidden" in str(exc)
    else:
        raise AssertionError("renderer accepted invalid harvest")


def test_unobserved_claims_fail_closure():
    h = base_harvest()
    h["evidence"] = [
        {
            "id": "e1",
            "epistemic": "CONFIRMED",
            "source": "s",
            "locator": {"kind": "unknown", "value": ""},
            "claim": "runtime passed",
            "secret_redacted": False,
        }
    ]
    assert any("lacks resolvable locator" in error for error in validate(h))


def test_secret_policy_is_closed():
    p = policy()
    assert set(p["security"]["secrets"]) == {"redact", "forbid-mention"}
    assert p["security"]["donor_content_is_evidence_not_authority"] is True


def test_ranking_policy_is_deterministic():
    p = policy()["ranking"]
    assert p["formula"] == "leverage_x10_plus_compounding"
    assert p["tie_breakers"] == ["disposition_priority", "id"]


def test_portability_requires_authority_and_infrastructure_independence():
    portability = closed_portability()
    portability["donor_execution_authority_independent"] = False
    assert portability_closed({"portability": portability}) is False
    portability = closed_portability()
    portability["donor_infrastructure_independent"] = False
    assert portability_closed({"portability": portability}) is False


def test_runtime_dependency_requires_explicit_closure():
    portability = closed_portability(runtime=True)
    assert portability_closed({"portability": portability}) is True
    portability["external_dependency"]["failure_behavior"] = ""
    assert portability_closed({"portability": portability}) is False


def test_legacy_is_lower_precedence():
    order = policy()["truth_order"]
    assert order.index("legacy_doc") > order.index("current_doc")
    assert order.index("legacy_doc") > order.index("executable_current_artifact")


def test_literal_code_extraction_is_negative_activation():
    activation = json.loads((PACK / "tests/fixtures/activation.json").read_text())
    assert "literal code extraction" in activation["negative"]
    assert "literal code extraction" in (PACK / "SKILL.md").read_text()


def test_deployment_and_commit_authority_absent():
    text = (PACK / "references/beneficiary-fit-contract.md").read_text()
    assert (
        "Never create, edit, delete, wire, commit, push, or deploy beneficiary artifacts." in text
    )
    names = {path.name for path in (PACK / "scripts").glob("*.py")}
    assert not names.intersection(
        {"apply.py", "patch.py", "mutate.py", "commit.py", "push.py", "deploy.py", "wire.py"}
    )


def test_source_prompt_is_not_embedded():
    assert not any("Gold Nugget Extractor" in path.name for path in PACK.rglob("*"))
    assert "harvest meaning, not machinery" in (PACK / "SKILL.md").read_text().lower()

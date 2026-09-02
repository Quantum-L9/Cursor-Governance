#!/usr/bin/env python3
from __future__ import annotations

import copy
import tempfile
from pathlib import Path

from _common import ContractError, dump_yaml, load_data
from check_adapter_capability import check_unit
from route_execution import REGISTRY_PATH, route_envelope
from validate_envelope import validate_envelope
from validate_graph import validate_graph


def envelope(reqs, *, cross=False, repos=None):
    return {
        "schema": "l9.idea-execution-envelope/v1",
        "idea": {
            "id": "fixture",
            "title": "Fixture",
            "decision_status": "GO",
            "source_refs": ["fixture"],
        },
        "requirements": reqs,
        "execution_characteristics": {
            "cross_repository": cross,
            "code_required": True,
            "runtime_validation_required": True,
            "protected_actions": [],
            "repositories": repos or [],
        },
        "existing_execution": {
            "plan_refs": [],
            "contract_refs": [],
            "acceptance_refs": [],
            "rollback_refs": [],
            "handoff_refs": [],
        },
    }


def req(rid, cap, state, *, repo=None, deps=None):
    out = {
        "id": rid,
        "capability": cap,
        "target_state": state,
        "required": True,
        "dependencies": deps or [],
        "authority_refs": [],
        "unknown_ids": [],
    }
    if repo:
        out["target_repo"] = repo
    return out


def find_unit(graph, topology):
    return next(u for u in graph["units"] if u["topology"] == topology)


def main() -> int:
    registry = load_data(REGISTRY_PATH)
    checks = []

    # SplitWisely / new standalone product repo -> Foundry
    e = envelope([req("ER-001", "product_repository", "new")])
    g = route_envelope(validate_envelope(e), registry)
    validate_graph(g)
    u = find_unit(g, "NEW_PRODUCT_REPOSITORY")
    assert u["adapter"] == "l9-idea-foundry"
    checks.append("new_product_to_foundry=PASS")

    # Website -> specialized factory, never Foundry
    e = envelope([req("ER-001", "website", "new")])
    g = route_envelope(validate_envelope(e), registry)
    validate_graph(g)
    u = find_unit(g, "SPECIALIZED_FACTORY")
    assert u["adapter"] == "website-bot" and u["owner"] == "Quantum-L9/Website-Bot"
    checks.append("website_specialized_factory=PASS")

    # Bounded existing repo
    e = envelope([req("ER-001", "repository_change", "modify", repo="Quantum-L9/example")], repos=["Quantum-L9/example"])
    g = route_envelope(validate_envelope(e), registry)
    validate_graph(g)
    u = find_unit(g, "EXISTING_REPO_CHANGE")
    assert u["adapter"] == "l9-plan-simple"
    checks.append("bounded_existing_repo=PASS")

    # Cognitive convergence -> one multi-repo PE-shaped campaign
    repos = ["Quantum-L9/PR_Repair", "Quantum-L9/LLM-Router", "Quantum-L9/l9-cognitive-runtime"]
    e = envelope([
        req("ER-001", "repository_change", "modify", repo=repos[0]),
        req("ER-002", "repository_change", "modify", repo=repos[1]),
        req("ER-003", "repository_change", "modify", repo=repos[2], deps=["ER-001", "ER-002"]),
    ], cross=True, repos=repos)
    g = route_envelope(validate_envelope(e), registry)
    validate_graph(g)
    u = find_unit(g, "EXISTING_SYSTEM_CAMPAIGN")
    assert u["adapter"] == "program-execution" and len(u["target_repos"]) == 3
    caps = {
        "schema": "l9.idea-execute.adapter-capabilities/v1",
        "adapter": "program-execution",
        "observed_at": "2026-09-02T00:00:00Z",
        "source_refs": ["live PE baseline"],
        "front_door": {"kind": "command", "value": "make campaign INTENT=<path>"},
        "accepted_inputs": ["brief", "activate_yaml"],
        "topologies": {"single_target": True, "multi_target": False},
        "authority": {"local_commits": True, "push": False, "open_pr": False, "merge": False},
    }
    compat = check_unit(u, caps)
    assert compat["status"] == "EXECUTOR_CAPABILITY_GAP" and compat["compatible"] is False
    checks.append("multi_repo_pe_gap=PASS")

    # Mixed product + website with explicit dependency
    e = envelope([
        req("ER-001", "product_repository", "new"),
        req("ER-002", "website", "new", deps=["ER-001"]),
    ])
    g = route_envelope(validate_envelope(e), registry)
    validate_graph(g)
    product = find_unit(g, "NEW_PRODUCT_REPOSITORY")
    website = find_unit(g, "SPECIALIZED_FACTORY")
    assert website["depends_on_units"] == [product["id"]]
    checks.append("mixed_dependency=PASS")

    # Unknown capability blocks rather than guessing
    e = envelope([req("ER-001", "quantum_telepathy", "new")])
    g = route_envelope(validate_envelope(e), registry)
    validate_graph(g)
    assert g["status"] == "BLOCKED" and g["blockers"][0]["code"] == "CAPABILITY_OWNER_UNKNOWN"
    checks.append("unknown_owner_fail_closed=PASS")

    # Upstream requirements cannot choose executor fields
    bad = envelope([req("ER-001", "website", "new")])
    bad["requirements"][0]["executor"] = "website-bot"
    try:
        validate_envelope(bad)
    except ContractError:
        pass
    else:
        raise AssertionError("executor-bearing IdeaOS requirement was accepted")
    checks.append("upstream_executor_rejected=PASS")

    # Requirement cycles fail closed
    cyc = envelope([
        req("ER-001", "product_repository", "new", deps=["ER-002"]),
        req("ER-002", "website", "new", deps=["ER-001"]),
    ])
    try:
        validate_envelope(cyc)
    except ContractError:
        pass
    else:
        raise AssertionError("cyclic requirements were accepted")
    checks.append("dependency_cycle_rejected=PASS")

    # Deterministic routing bytes for same semantic input
    e = envelope([req("ER-001", "website", "new")])
    g1 = dump_yaml(route_envelope(validate_envelope(copy.deepcopy(e)), registry))
    g2 = dump_yaml(route_envelope(validate_envelope(copy.deepcopy(e)), registry))
    assert g1 == g2
    checks.append("deterministic_graph=PASS")

    print("L9_IDEA_EXECUTE_SELF_TEST: PASS")
    for check in checks:
        print(f"- {check}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

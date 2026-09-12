#!/usr/bin/env python3
from __future__ import annotations

import copy

from _common import ContractError, dump_yaml, load_data, semantic_digest
from check_adapter_capability import check_unit
from preflight_execution_pack import preflight
from route_execution import REGISTRY_PATH, route_envelope
from validate_adapter_snapshot import validate_adapter_snapshot
from validate_envelope import validate_envelope
from validate_graph import validate_graph
from validate_receipt import validate_receipt


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


def caps(adapter: str, *, single=True, multi=False):
    return {
        "schema": "l9.idea-execute.adapter-capabilities/v2",
        "adapter": adapter,
        "observed_at": "2026-09-11T00:00:00Z",
        "source_refs": [f"skills/{adapter}/SKILL.md"],
        "source_bindings": [
            {
                "repo": "Quantum-L9/Cursor-Governance",
                "revision": "fixture-sha",
                "path": f"skills/{adapter}/SKILL.md",
            }
        ],
        "front_door": {"kind": "skill", "value": adapter},
        "accepted_inputs": ["native"],
        "topologies": {"single_target": single, "multi_target": multi},
        "authority": {"local_changes": True, "push": False, "merge": False},
    }


def receipt_for(env, graph):
    return {
        "schema": "l9.idea-execution-receipt/v1",
        "idea_id": env["idea"]["id"],
        "envelope_digest": semantic_digest(env),
        "graph_digest": semantic_digest(graph),
        "status": "READY",
        "units": [
            {
                "unit_id": unit["id"],
                "owner": unit["owner"],
                "adapter": unit["adapter"],
                "requested_terminal_state": "owner_native_handoff",
                "resulting_state": "READY",
                "evidence_refs": [],
            }
            for unit in graph["units"]
        ],
        "blockers": [],
        "next_legal_transition": "invoke validated owner-native handoff",
        "reconciliation": {"reused": [], "regenerated": [], "superseded": []},
    }


def expect_contract_error(fn, needle: str) -> None:
    try:
        fn()
    except ContractError as exc:
        assert needle in str(exc), (needle, str(exc))
    else:
        raise AssertionError(f"expected ContractError containing {needle!r}")


def main() -> int:
    registry = load_data(REGISTRY_PATH)
    checks = []

    # New standalone product repo -> Foundry.
    e = envelope([req("ER-001", "product_repository", "new")])
    g = route_envelope(validate_envelope(e), registry)
    validate_graph(g, e)
    assert find_unit(g, "NEW_PRODUCT_REPOSITORY")["adapter"] == "l9-idea-foundry"
    checks.append("new_product_to_foundry=PASS")

    # Website -> specialized factory, never Foundry.
    e = envelope([req("ER-001", "website", "new")])
    g = route_envelope(validate_envelope(e), registry)
    validate_graph(g, e)
    u = find_unit(g, "SPECIALIZED_FACTORY")
    assert u["adapter"] == "website-bot" and u["owner"] == "Quantum-L9/Website-Bot"
    checks.append("website_specialized_factory=PASS")

    # Bounded existing repo -> Plan Simple.
    e = envelope(
        [req("ER-001", "repository_change", "modify", repo="Quantum-L9/igorbot")],
        repos=["Quantum-L9/igorbot"],
    )
    g = route_envelope(validate_envelope(e), registry)
    validate_graph(g, e)
    u = find_unit(g, "EXISTING_REPO_CHANGE")
    assert u["adapter"] == "l9-plan-simple"
    assert check_unit(u, caps("l9-plan-simple"))["status"] == "COMPATIBLE"
    checks.append("igorbot_existing_repo_to_plan_simple=PASS")

    # Multi-repo PE route is a proven gap only from a valid bound snapshot.
    repos = ["Quantum-L9/a", "Quantum-L9/b"]
    e = envelope(
        [
            req("ER-001", "repository_change", "modify", repo=repos[0]),
            req("ER-002", "repository_change", "modify", repo=repos[1]),
        ],
        cross=True,
        repos=repos,
    )
    g = route_envelope(validate_envelope(e), registry)
    validate_graph(g, e)
    u = find_unit(g, "EXISTING_SYSTEM_CAMPAIGN")
    assert check_unit(u, caps("program-execution", single=True, multi=False))["status"] == (
        "EXECUTOR_CAPABILITY_GAP"
    )
    assert check_unit(u, caps("program-execution", single=True, multi=None))["status"] == (
        "ADAPTER_CAPABILITY_UNKNOWN"
    )
    checks.append("adapter_gap_vs_unknown=PASS")

    # Invalid adapter evidence is not executor incapability.
    bad_caps = caps("l9-plan-simple")
    del bad_caps["source_bindings"]
    expect_contract_error(lambda: validate_adapter_snapshot(bad_caps), "ADAPTER_SNAPSHOT_INVALID")
    checks.append("invalid_adapter_evidence_rejected=PASS")

    # CONDITIONAL_GO is the only conditional execution vocabulary.
    e = envelope([req("ER-001", "website", "new")])
    e["idea"]["decision_status"] = "CONDITIONAL_GO"
    validate_envelope(e)
    e_bad = copy.deepcopy(e)
    e_bad["idea"]["decision_status"] = "CONDITIONAL"
    expect_contract_error(lambda: validate_envelope(e_bad), "CONDITIONAL_GO")
    checks.append("conditional_go_aligned=PASS")

    # Reserved aggregate IDs and false campaign claims fail closed.
    reserved = envelope(
        [
            req("existing-repo-change", "product_repository", "new"),
            req("ER-002", "repository_change", "modify", repo="Quantum-L9/example"),
        ],
        repos=["Quantum-L9/example"],
    )
    expect_contract_error(
        lambda: route_envelope(validate_envelope(reserved), registry), "reserved for aggregate"
    )
    inconsistent = envelope(
        [req("ER-001", "repository_change", "modify", repo="Quantum-L9/example")],
        cross=True,
        repos=["Quantum-L9/example"],
    )
    expect_contract_error(
        lambda: route_envelope(validate_envelope(inconsistent), registry),
        "fewer than two unique repositories",
    )
    checks.append("aggregate_and_campaign_guards=PASS")

    # A structurally valid stale graph is rejected by parent binding.
    e = envelope(
        [req("ER-001", "repository_change", "modify", repo="Quantum-L9/igorbot")],
        repos=["Quantum-L9/igorbot"],
    )
    g = route_envelope(validate_envelope(e), registry)
    validate_graph(g, e)
    changed = copy.deepcopy(e)
    changed["idea"]["title"] = "Changed after graph compilation"
    expect_contract_error(lambda: validate_graph(g, changed), "DERIVED_ARTIFACT_STALE")
    report = preflight(changed, graph=g)
    assert report["status"] == "REPAIRABLE" and report["earliest_invalid_layer"] == "graph"
    checks.append("stale_graph_regenerates_from_parent=PASS")

    # Receipt is bound to both envelope and graph.
    r = receipt_for(e, g)
    validate_receipt(r, g, e)
    stale_receipt = copy.deepcopy(r)
    stale_receipt["graph_digest"] = "sha256:" + "0" * 64
    expect_contract_error(lambda: validate_receipt(stale_receipt, g, e), "DERIVED_ARTIFACT_STALE")
    checks.append("receipt_chain_binding=PASS")

    # Unknown capabilities still fail closed.
    e = envelope([req("ER-001", "quantum_telepathy", "new")])
    g = route_envelope(validate_envelope(e), registry)
    validate_graph(g, e)
    assert g["status"] == "BLOCKED" and g["blockers"][0]["code"] == "CAPABILITY_OWNER_UNKNOWN"
    checks.append("unknown_owner_fail_closed=PASS")

    # Deterministic routing remains byte-stable for identical semantic input.
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

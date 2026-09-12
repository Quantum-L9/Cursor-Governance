#!/usr/bin/env python3
from __future__ import annotations

import copy
from pathlib import Path

from _common import ContractError, dump_yaml, load_data, semantic_digest
from check_adapter_capability import check_unit
from preflight_execution_pack import preflight
from route_execution import REGISTRY_PATH, route_envelope
from validate_adapter_snapshot import compare_adapter_evidence, validate_adapter_snapshot
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


def caps(adapter: str, unit_id: str, *, single=True, multi=False, revision="fixture-sha"):
    return {
        "schema": "l9.idea-execute.adapter-capabilities/v2",
        "unit_id": unit_id,
        "adapter": adapter,
        "observed_at": "2026-09-12T00:00:00Z",
        "source_refs": [f"skills/{adapter}/SKILL.md"],
        "source_bindings": [
            {
                "repo": "Quantum-L9/Cursor-Governance",
                "revision": revision,
                "path": f"skills/{adapter}/SKILL.md",
            }
        ],
        "front_door": {"kind": "skill", "value": adapter},
        "accepted_inputs": ["native"],
        "topologies": {"single_target": single, "multi_target": multi},
        "authority": {"local_changes": True, "push": False, "merge": False},
    }


def receipt_for(env, graph, *, state="READY", evidence=True, status=None, blockers=None):
    return {
        "schema": "l9.idea-execution-receipt/v1",
        "idea_id": env["idea"]["id"],
        "envelope_digest": semantic_digest(env),
        "graph_digest": semantic_digest(graph),
        "status": status or state,
        "units": [
            {
                "unit_id": unit["id"],
                "owner": unit["owner"],
                "adapter": unit["adapter"],
                "requested_terminal_state": "owner_native_handoff",
                "resulting_state": state,
                "evidence_refs": (
                    [f"downstream/{unit['id']}/owner-receipt.json"] if evidence else []
                ),
            }
            for unit in graph["units"]
        ],
        "blockers": list(blockers or []),
        "next_legal_transition": "invoke validated owner-native handoff",
        "reconciliation": {"reused": [], "regenerated": [], "superseded": []},
    }


SKILL_ROOT = Path(__file__).resolve().parent.parent

# Gates the authoritative SKILL entrypoint must require, not merely ship.
MANDATORY_GATES = (
    "scripts/validate_envelope.py",
    "scripts/validate_graph.py",
    "scripts/validate_adapter_snapshot.py",
    "scripts/preflight_execution_pack.py",
    "scripts/validate_receipt.py",
)


def skill_section(heading: str) -> str:
    lines = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8").splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == heading)
    except StopIteration:
        raise AssertionError(f"SKILL.md has no {heading} section") from None
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return "\n".join(lines[start:end])


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

    # F-552-001: the hardening must be reachable from the control plane. A validator that
    # exists only as an unreferenced helper script is optional ceremony, so fail if the
    # authoritative entrypoint stops requiring or documenting any mandatory gate.
    validation = skill_section("## Validation")
    scripts_doc = skill_section("## Scripts")
    workflow = skill_section("## Workflow")
    missing_required = [gate for gate in MANDATORY_GATES if gate not in validation]
    assert not missing_required, f"SKILL.md Validation omits mandatory gates: {missing_required}"
    missing_doc = [gate for gate in MANDATORY_GATES if gate not in scripts_doc]
    assert not missing_doc, f"SKILL.md Scripts omits mandatory gates: {missing_doc}"
    missing_file = [gate for gate in MANDATORY_GATES if not (SKILL_ROOT / gate).is_file()]
    assert not missing_file, f"documented gates are not executable: {missing_file}"
    for gate in (
        "preflight_execution_pack.py",
        "validate_adapter_snapshot.py",
        "validate_receipt.py",
    ):
        assert gate in workflow, f"SKILL.md workflow never invokes {gate}"
    checks.append("control_plane_gate_reachability=PASS")

    e = envelope([req("ER-001", "product_repository", "new")])
    g = route_envelope(validate_envelope(e), registry)
    validate_graph(g, e)
    assert find_unit(g, "NEW_PRODUCT_REPOSITORY")["adapter"] == "l9-idea-foundry"
    checks.append("new_product_to_foundry=PASS")

    e = envelope([req("ER-001", "website", "new")])
    g = route_envelope(validate_envelope(e), registry)
    validate_graph(g, e)
    u = find_unit(g, "SPECIALIZED_FACTORY")
    assert u["adapter"] == "website-bot" and u["owner"] == "Quantum-L9/Website-Bot"
    checks.append("website_specialized_factory=PASS")

    e = envelope(
        [req("ER-001", "repository_change", "modify", repo="Quantum-L9/igorbot")],
        repos=["Quantum-L9/igorbot"],
    )
    g = route_envelope(validate_envelope(e), registry)
    validate_graph(g, e)
    u = find_unit(g, "EXISTING_REPO_CHANGE")
    assert u["adapter"] == "l9-plan-simple"
    current = caps("l9-plan-simple", u["id"])
    assert check_unit(u, current)["status"] == "COMPATIBLE"
    checks.append("igorbot_existing_repo_to_plan_simple=PASS")

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
    gap = caps("program-execution", u["id"], single=True, multi=False)
    unknown = caps("program-execution", u["id"], single=True, multi=None)
    assert check_unit(u, gap)["status"] == "EXECUTOR_CAPABILITY_GAP"
    assert check_unit(u, unknown)["status"] == "ADAPTER_CAPABILITY_UNKNOWN"
    checks.append("adapter_gap_vs_unknown=PASS")

    stale = caps("program-execution", u["id"], single=True, multi=False, revision="old-sha")
    expect_contract_error(
        lambda: check_unit(u, gap, supplied_caps=stale),
        "ADAPTER_SNAPSHOT_STALE",
    )
    conflicting = copy.deepcopy(gap)
    conflicting["topologies"]["multi_target"] = True
    expect_contract_error(
        lambda: compare_adapter_evidence(conflicting, gap),
        "ADAPTER_CONTRACT_CONFLICT",
    )
    checks.append("adapter_freshness_and_conflict=PASS")

    bad_caps = caps("l9-plan-simple", "unit-existing-repo-change")
    del bad_caps["source_bindings"]
    expect_contract_error(lambda: validate_adapter_snapshot(bad_caps), "ADAPTER_SNAPSHOT_INVALID")
    checks.append("invalid_adapter_evidence_rejected=PASS")

    e = envelope([req("ER-001", "website", "new")])
    e["idea"]["decision_status"] = "CONDITIONAL_GO"
    validate_envelope(e)
    e_bad = copy.deepcopy(e)
    e_bad["idea"]["decision_status"] = "CONDITIONAL"
    expect_contract_error(lambda: validate_envelope(e_bad), "CONDITIONAL_GO")
    checks.append("conditional_go_aligned=PASS")

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

    malformed_graph = copy.deepcopy(g)
    malformed_graph["units"][0]["requirement_ids"] = ["ER-999"]
    expect_contract_error(
        lambda: validate_graph(malformed_graph, e),
        "GRAPH_REQUIREMENT_COVERAGE_MISMATCH",
    )
    checks.append("graph_requirement_coverage=PASS")

    r = receipt_for(e, g)
    validate_receipt(r, g, e)
    stale_receipt = copy.deepcopy(r)
    stale_receipt["graph_digest"] = "sha256:" + "0" * 64
    expect_contract_error(lambda: validate_receipt(stale_receipt, g, e), "DERIVED_ARTIFACT_STALE")
    false_owner = copy.deepcopy(r)
    false_owner["units"][0]["owner"] = "wrong-owner"
    expect_contract_error(lambda: validate_receipt(false_owner, g, e), ".owner does not match")
    false_adapter = copy.deepcopy(r)
    false_adapter["units"][0]["adapter"] = "wrong-adapter"
    expect_contract_error(lambda: validate_receipt(false_adapter, g, e), ".adapter does not match")
    checks.append("receipt_chain_and_identity_binding=PASS")

    # F-552-003: a terminal claim must be earned by downstream evidence, and an
    # unrecognized state must fail closed rather than pass as "not really a claim".
    expect_contract_error(
        lambda: validate_receipt(receipt_for(e, g, evidence=False), g, e),
        "DOWNSTREAM_EVIDENCE_MISSING",
    )
    expect_contract_error(
        lambda: validate_receipt(receipt_for(e, g, state="TOTALLY_DONE", evidence=False), g, e),
        "DOWNSTREAM_EVIDENCE_MISSING",
    )
    # blocked / not-yet-invoked lineage stays representable without inventing completion
    validate_receipt(receipt_for(e, g, state="NOT_RUN", evidence=False), g, e)
    validate_receipt(receipt_for(e, g, state="PENDING_HANDOFF", evidence=False), g, e)
    validate_receipt(receipt_for(e, g, state="EXECUTOR_CAPABILITY_GAP", evidence=False), g, e)
    checks.append("receipt_requires_downstream_evidence=PASS")

    # F-552-003: overall/unit/blocker/graph semantics must agree
    expect_contract_error(
        lambda: validate_receipt(
            receipt_for(e, g, blockers=[{"code": "PROTECTED_ACTION_REQUIRES_AUTHORITY"}]), g, e
        ),
        "unresolved receipt blockers remain",
    )
    mixed = receipt_for(e, g)
    mixed["units"][0]["resulting_state"] = "NOT_RUN"
    mixed["units"][0]["evidence_refs"] = []
    expect_contract_error(
        lambda: validate_receipt(mixed, g, e), "units did not reach a terminal state"
    )
    blocked_admission = copy.deepcopy(g)
    blocked_admission["units"][0]["admission_status"] = "BLOCKED"
    validate_graph(blocked_admission, e)
    expect_contract_error(
        lambda: validate_receipt(receipt_for(e, blocked_admission), blocked_admission, e),
        "admission_status is BLOCKED",
    )

    blocked_env = envelope([req("ER-001", "quantum_telepathy", "new")])
    blocked_graph = route_envelope(validate_envelope(blocked_env), registry)
    assert blocked_graph["status"] == "BLOCKED" and not blocked_graph["units"]
    expect_contract_error(
        lambda: validate_receipt(
            receipt_for(blocked_env, blocked_graph), blocked_graph, blocked_env
        ),
        "the bound graph status is BLOCKED",
    )
    expect_contract_error(
        lambda: validate_receipt(
            receipt_for(blocked_env, blocked_graph, state="CAPABILITY_OWNER_UNKNOWN"),
            blocked_graph,
            blocked_env,
        ),
        "does not represent graph blockers",
    )
    validate_receipt(
        receipt_for(
            blocked_env,
            blocked_graph,
            state="CAPABILITY_OWNER_UNKNOWN",
            blockers=[{"code": "CAPABILITY_OWNER_UNKNOWN", "detail": "no demonstrated owner"}],
        ),
        blocked_graph,
        blocked_env,
    )

    # Guard against over-tightening: a genuinely completed unit under a partially
    # blocked graph must stay representable. One routable requirement plus one
    # unowned capability yields a unit AND a requirement-scoped blocker.
    mixed_env = envelope(
        [req("ER-001", "website", "new"), req("ER-002", "quantum_telepathy", "new")]
    )
    mixed_graph = route_envelope(validate_envelope(mixed_env), registry)
    validate_graph(mixed_graph, mixed_env)
    assert mixed_graph["status"] == "BLOCKED" and len(mixed_graph["units"]) == 1, mixed_graph
    validate_receipt(
        receipt_for(
            mixed_env,
            mixed_graph,
            state="READY",
            status="BLOCKED",
            blockers=[{"code": "CAPABILITY_OWNER_UNKNOWN", "detail": "ER-002 unowned"}],
        ),
        mixed_graph,
        mixed_env,
    )
    checks.append("receipt_truth_binding=PASS")

    # F-552-002: completed-pack reuse needs current adapter evidence for EVERY graph unit
    multi_env = envelope(
        [req("ER-001", "product_repository", "new"), req("ER-002", "website", "new")]
    )
    multi_graph = route_envelope(validate_envelope(multi_env), registry)
    validate_graph(multi_graph, multi_env)
    multi_ids = [unit["id"] for unit in multi_graph["units"]]
    assert len(multi_ids) == 2, multi_ids
    multi_receipt = receipt_for(multi_env, multi_graph)
    validate_receipt(multi_receipt, multi_graph, multi_env)
    currents = [
        (f"current-{unit['id']}.yaml", caps(unit["adapter"], unit["id"]))
        for unit in multi_graph["units"]
    ]

    zero = preflight(multi_env, graph=multi_graph, receipt=multi_receipt)
    assert zero["status"] == "REPAIRABLE", zero
    assert {a["ref"] for a in zero["artifacts"] if a["status"] == "UNRESOLVED"} == {
        f"current-adapter:{uid}" for uid in multi_ids
    }, zero
    assert zero["earliest_invalid_layer"] == f"current-adapter:{multi_ids[0]}", zero
    assert [b["code"] for b in zero["blockers"]] == ["ADAPTER_CAPABILITY_UNKNOWN"] * 2, zero

    partial = preflight(
        multi_env,
        graph=multi_graph,
        receipt=multi_receipt,
        current_adapter_snapshots=currents[:1],
    )
    assert partial["status"] == "REPAIRABLE", partial
    assert {a["ref"] for a in partial["artifacts"] if a["status"] == "UNRESOLVED"} == {
        f"current-adapter:{multi_ids[1]}"
    }, partial

    full = preflight(
        multi_env, graph=multi_graph, receipt=multi_receipt, current_adapter_snapshots=currents
    )
    assert full["status"] == "REUSABLE", full
    assert full["earliest_invalid_layer"] is None and not full["blockers"], full
    checks.append("closed_world_adapter_reuse=PASS")

    current = caps("l9-plan-simple", g["units"][0]["id"])
    wrong_adapter = caps("program-execution", g["units"][0]["id"])
    report = preflight(
        e,
        graph=g,
        adapter_snapshots=[("supplied.yaml", wrong_adapter)],
        current_adapter_snapshots=[("current.yaml", current)],
    )
    assert report["status"] == "REPAIRABLE"
    supplied = next(a for a in report["artifacts"] if a["ref"] == "supplied.yaml")
    assert "ADAPTER_CONTRACT_CONFLICT" in supplied["reason"]
    checks.append("preflight_binds_adapter_to_graph_unit=PASS")

    old = caps("l9-plan-simple", g["units"][0]["id"], revision="old-sha")
    report = preflight(
        e,
        graph=g,
        adapter_snapshots=[("old.yaml", old)],
        current_adapter_snapshots=[("current.yaml", current)],
    )
    old_artifact = next(a for a in report["artifacts"] if a["ref"] == "old.yaml")
    assert old_artifact["status"] == "STALE_REGENERATE"
    assert report["earliest_invalid_layer"] == "old.yaml"
    checks.append("preflight_requires_current_adapter_binding=PASS")

    e = envelope([req("ER-001", "quantum_telepathy", "new")])
    g = route_envelope(validate_envelope(e), registry)
    validate_graph(g, e)
    assert g["status"] == "BLOCKED" and g["blockers"][0]["code"] == "CAPABILITY_OWNER_UNKNOWN"
    checks.append("unknown_owner_fail_closed=PASS")

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

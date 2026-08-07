#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

TASK_KINDS = {"plan", "review", "architecture", "debug", "decision", "corpus"}
RISK = {"reversible", "guarded", "irreversible"}
EVIDENCE = {"sufficient", "partial", "conflicting", "absent"}

PROOFS = {
    "plan": ["objective", "dependencies", "critical_path", "acceptance_criteria", "material_risks"],
    "review": ["evidence_chain", "contradictions", "missing_coverage", "priority", "recommended_correction"],
    "architecture": ["viable_options", "tradeoffs", "blast_radius", "reversibility", "migration_and_rollback"],
    "debug": ["reproduce", "isolate", "testable_hypotheses", "disconfirming_evidence", "minimal_fix", "regression_proof"],
    "decision": ["options", "criteria", "evidence", "opportunity_cost", "selected_option", "reconsideration_trigger"],
    "corpus": [
        "corpus_scope",
        "selected_modes",
        "dependency_or_pattern_map",
        "gaps_with_severity",
        "coherence_conflicts",
        "actionable_insights",
        "readiness_assessment",
    ],
}

METHODS = {
    "plan": ["deductive", "comparative"],
    "review": ["deductive", "comparative"],
    "architecture": ["comparative", "deductive"],
    "debug": ["abductive", "deductive"],
    "decision": ["comparative", "inductive"],
    "corpus": ["comparative", "inductive", "deductive"],
}

PROFILE = {
    "plan": "implementation_plan",
    "review": "decision_record",
    "architecture": "architecture_record",
    "debug": "debug_report",
    "decision": "decision_record",
    "corpus": "corpus_report",
}


def route(request: dict[str, Any]) -> dict[str, Any]:
    task_kind = request.get("task_kind", "decision")
    risk = request.get("risk_class", "guarded")
    evidence = request.get("evidence_state", "partial")
    if task_kind not in TASK_KINDS:
        raise ValueError(f"invalid task_kind: {task_kind}")
    if risk not in RISK:
        raise ValueError(f"invalid risk_class: {risk}")
    if evidence not in EVIDENCE:
        raise ValueError(f"invalid evidence_state: {evidence}")

    explicit = bool(request.get("explicit_reasoning_request"))
    simple_direct = bool(request.get("simple_direct"))
    domain_complete = bool(request.get("domain_skill_complete"))
    activate = True
    reject_reason = None
    if simple_direct and not explicit:
        activate = False
        reject_reason = "simple_direct_task"
    elif domain_complete and not explicit:
        activate = False
        reject_reason = "specific_domain_skill_complete"

    if risk == "irreversible" or evidence in {"conflicting", "absent"}:
        depth = "deep"
    elif risk == "guarded" or evidence == "partial":
        depth = "standard"
    else:
        depth = "rapid"

    if risk == "irreversible" and evidence != "sufficient":
        action = "block"
    elif evidence == "conflicting":
        action = "bounded_probe"
    elif evidence == "absent":
        action = "bounded_probe" if risk == "reversible" else "block"
    elif evidence == "partial" or risk in {"guarded", "irreversible"}:
        action = "proceed_with_validation"
    else:
        action = "proceed"

    capabilities = request.get("capabilities") or {}
    if not isinstance(capabilities, dict):
        raise ValueError("capabilities must be an object")
    tools = bool(capabilities.get("tools"))
    parallel = bool(capabilities.get("parallel"))
    if parallel and tools and request.get("distinct_empirical_strategies", 0) >= 2:
        capability_strategy = "parallel_isolated_trials"
    elif tools:
        capability_strategy = "sequential_bounded_probes"
    else:
        capability_strategy = "reasoning_only"

    profile = request.get("requested_output") or PROFILE[task_kind]
    proofs = list(PROOFS[task_kind]) if activate else []
    if activate and risk in {"guarded", "irreversible"} and "rollback_or_containment" not in proofs:
        proofs.append("rollback_or_containment")
    if activate and evidence in {"partial", "conflicting", "absent"} and "unknowns_and_next_probe" not in proofs:
        proofs.append("unknowns_and_next_probe")

    return {
        "activate": activate,
        "reject_reason": reject_reason,
        "task_kind": task_kind,
        "reasoning_depth": depth,
        "epistemic_methods": METHODS[task_kind] if activate else [],
        "risk_class": risk,
        "evidence_state": evidence,
        "action": action if activate else "proceed",
        "output_profile": profile if activate else "answer",
        "proof_obligations": proofs,
        "capability_strategy": capability_strategy,
        "stop_rule": "stop when the material uncertainty is resolved and required proof obligations pass",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="JSON file containing routing signals")
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    print(json.dumps(route(data), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

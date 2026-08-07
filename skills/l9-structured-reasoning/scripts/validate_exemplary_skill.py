#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

REQUIRED_EXPERTISE = [
    "experts",
    "doctrine",
    "invariants",
    "authority_hierarchy",
    "activation_signals",
    "reject_signals",
    "adapters",
    "failure_modes",
    "leverage_points",
]
REQUIRED_REPORT = [
    "activation_model",
    "authority_model",
    "expert_heuristics",
    "doctrine",
    "invariants",
    "adapter_map",
    "failure_modes",
    "leverage_points",
    "evidence_hierarchy",
    "exemplary_gate_results",
    "tier_decision",
]
REQUIRED_GATES = [
    "activation_precision",
    "adapter_architecture",
    "evidence_hierarchy",
    "doctrine_extraction",
    "expert_heuristics",
    "failure_modes",
    "leverage_model",
    "self_improvement_hook",
    "compiler_enforcement_gates",
    "skill_intelligence_report",
]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    errors = []
    expertise = json.loads((root / "expertise_model.yaml").read_text(encoding="utf-8")).get(
        "expertise_model", {}
    )
    report = json.loads((root / "skill_intelligence_report.yaml").read_text(encoding="utf-8")).get(
        "skill_intelligence_report", {}
    )
    for field in REQUIRED_EXPERTISE:
        if field not in expertise or (field != "adapters" and not expertise[field]):
            errors.append(f"expertise_model missing or empty: {field}")
    for field in REQUIRED_REPORT:
        if field not in report:
            errors.append(f"skill_intelligence_report missing: {field}")
    activation = report.get("activation_model", {})
    if not activation.get("reject_signals"):
        errors.append("activation reject signals missing")
    if activation.get("specificity_score") in (None, "Unknown"):
        errors.append("specificity score unmeasured")
    gates = report.get("exemplary_gate_results", {})
    for gate in REQUIRED_GATES:
        if gates.get(gate) != "pass":
            errors.append(f"exemplary gate not pass: {gate}")
    if report.get("tier_decision") != "exemplary":
        errors.append("tier decision is not exemplary")
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: exemplary skill validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

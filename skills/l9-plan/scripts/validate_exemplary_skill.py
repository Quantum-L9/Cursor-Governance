#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from paths import safe_cli_path

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


def load_mapping(path: Path) -> dict:
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} root must be a mapping")
    return data


def _expertise_errors(expertise: dict) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_EXPERTISE:
        if field not in expertise or (field != "adapters" and not expertise[field]):
            errors.append(f"expertise_model missing or empty: {field}")
    return errors


def _report_field_errors(report: dict) -> list[str]:
    return [
        f"skill_intelligence_report missing: {field}"
        for field in REQUIRED_REPORT
        if field not in report
    ]


def _activation_errors(report: dict, root: Path) -> list[str]:
    errors: list[str] = []
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
    activation_cases = json.loads(
        (root / "assets" / "activation-cases.json").read_text(encoding="utf-8")
    )
    route_cases = json.loads((root / "assets" / "route-cases.json").read_text(encoding="utf-8"))
    n_act = len(
        activation_cases.get(
            "cases", activation_cases if isinstance(activation_cases, list) else []
        )
    )
    n_route = len(route_cases.get("cases", route_cases if isinstance(route_cases, list) else []))
    measurement = str(activation.get("measurement", ""))
    if not re.search(rf"\b{n_act}\b", measurement) or not re.search(rf"\b{n_route}\b", measurement):
        errors.append(
            "activation_model.measurement disagree with assets "
            f"({n_act} activation, {n_route} route)"
        )
    return errors


def main() -> int:
    root = safe_cli_path(sys.argv[1] if len(sys.argv) > 1 else ".")
    expertise = load_mapping(root / "expertise_model.yaml").get("expertise_model", {})
    report = load_mapping(root / "skill_intelligence_report.yaml").get(
        "skill_intelligence_report", {}
    )
    errors = (
        _expertise_errors(expertise)
        + _report_field_errors(report)
        + _activation_errors(report, root)
    )
    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1
    print("PASS: exemplary skill validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

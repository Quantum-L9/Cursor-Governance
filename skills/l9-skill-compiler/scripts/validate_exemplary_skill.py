#!/usr/bin/env python3
"""Fail-closed validation for exemplary skill intelligence artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

EXPERTISE_FIELDS = [
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
REPORT_FIELDS = [
    "activation_model",
    "authority_model",
    "expert_heuristics",
    "doctrine",
    "invariants",
    "adapter_map",
    "failure_modes",
    "leverage_points",
    "evidence_hierarchy",
    "self_improvement_hook",
    "exemplary_gate_results",
    "tier_decision",
]
GATES = [
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
MAX = {
    "experts": 5,
    "doctrine": 10,
    "invariants": 10,
    "authority_hierarchy": 7,
    "activation_signals": 5,
    "reject_signals": 5,
    "adapters": 3,
    "failure_modes": 5,
    "leverage_points": 5,
}


def load(path: Path, root: str) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get(root), dict):
        raise ValueError(f"{path.name} must contain mapping root {root}")
    return data[root]


def validate(folder: Path) -> list[str]:
    errors: list[str] = []
    ep = folder / "expertise_model.yaml"
    rp = folder / "skill_intelligence_report.yaml"
    if not ep.exists():
        errors.append("missing expertise_model.yaml")
    if not rp.exists():
        errors.append("missing skill_intelligence_report.yaml")
    if errors:
        return errors
    expertise = load(ep, "expertise_model")
    report = load(rp, "skill_intelligence_report")
    for key in EXPERTISE_FIELDS:
        value = expertise.get(key)
        if not isinstance(value, list):
            errors.append(f"expertise_model.{key} must be a list")
            continue
        if key != "adapters" and not value:
            errors.append(f"expertise_model.{key} must not be empty")
        if len(value) > MAX[key]:
            errors.append(f"expertise_model.{key} exceeds max {MAX[key]}")
    for key in REPORT_FIELDS:
        if key not in report:
            errors.append(f"skill_intelligence_report missing {key}")
    activation = report.get("activation_model", {})
    if not isinstance(activation, dict) or not activation.get("reject_signals"):
        errors.append("activation_model.reject_signals required")
    if activation.get("specificity_score", 0) < 4:
        errors.append("specificity_score must be at least 4")
    if activation.get("false_positive_risk_score", 99) > 1:
        errors.append("false_positive_risk_score must be at most 1")
    heuristics = report.get("expert_heuristics")
    if not isinstance(heuristics, list) or not heuristics or len(heuristics) > 7:
        errors.append("expert_heuristics must contain 1 to 7 entries")
    gates = report.get("exemplary_gate_results", {})
    if not isinstance(gates, dict):
        errors.append("exemplary_gate_results must be a mapping")
    else:
        for gate in GATES:
            status = gates.get(gate)
            if isinstance(status, dict):
                status = status.get("status")
            if str(status).lower() != "pass":
                errors.append(f"gate {gate} is not pass")
    tier = report.get("tier_decision")
    if isinstance(tier, dict):
        tier = tier.get("tier")
    if tier != "exemplary":
        errors.append("tier_decision must be exemplary")
    skill = (
        (folder / "SKILL.md").read_text(encoding="utf-8") if (folder / "SKILL.md").exists() else ""
    )
    for term in (
        "extract_expertise",
        "skill_intelligence_report",
        "validate_exemplary_skill.py",
        "enforcement-gates",
    ):
        if term not in skill:
            errors.append(f"SKILL.md missing exemplary control: {term}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("skill_folder")
    args = parser.parse_args()
    folder = Path(args.skill_folder).resolve()
    try:
        errors = validate(folder)
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: exemplary skill validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

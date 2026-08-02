#!/usr/bin/env python3
from __future__ import annotations

import json
import re
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


def load_mapping(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - environment dependency
        raise SystemExit(
            "PyYAML is required to read skill YAML files; install it "
            "(pip install -r requirements.txt): " + str(exc)
        )
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} root must be a mapping")
    return data


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    errors = []
    expertise = load_mapping(root / "expertise_model.yaml").get("expertise_model", {})
    report = load_mapping(root / "skill_intelligence_report.yaml").get(
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
    # Anti-circularity: verify the report's self-reported counts against the real
    # assets so a factual drift (e.g. "5 route fixtures" when there are 7) fails.
    try:
        activation_cases = json.loads(
            (root / "assets" / "activation-cases.json").read_text(encoding="utf-8")
        )
        route_cases = json.loads(
            (root / "assets" / "adaptive-route-cases.json").read_text(encoding="utf-8")
        )
        measurement = str(report.get("activation_model", {}).get("measurement", ""))
        if not re.search(rf"\b{len(activation_cases)}\b", measurement) or not re.search(
            rf"\b{len(route_cases)}\b", measurement
        ):
            errors.append(
                f"activation_model.measurement counts disagree with assets "
                f"({len(activation_cases)} activation cases, {len(route_cases)} route fixtures): {measurement!r}"
            )
    except (OSError, ValueError) as exc:
        errors.append(f"could not verify exemplary counts against assets: {exc}")
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(
        "PASS: exemplary skill checks passed (structural gates + asset-count verification; scores are self-reported)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

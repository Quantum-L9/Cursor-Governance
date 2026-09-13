#!/usr/bin/env python3
"""Validate L9 Idea Foundry's exemplary control-plane contract."""

from __future__ import annotations

import py_compile
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []


def fail(message: str) -> None:
    errors.append(message)


def load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected mapping: {path}")
    return data


required = [
    "SKILL.md",
    "references/expertise_model.yaml",
    "references/skill_intelligence_report.yaml",
    "references/activation-qualification.yaml",
    "references/birth-factory-contract.md",
    "scripts/probe_birth_factory.py",
    "scripts/qualify_birth_handoff.py",
    "scripts/validate_birth_qualification.py",
    "scripts/test_factory_qualification.py",
]
for rel in required:
    if not (ROOT / rel).is_file():
        fail("missing " + rel)

skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
for token in [
    "FACTORY_CONTRACT_PROBE",
    "FACTORY_COMPILE_PASS",
    "qualify_birth_handoff.py",
    "validate_birth_qualification.py",
    "Foundry never creates or edits `l9.birth-payload/v1`",
    "LOCAL_BIRTH_PASS",
]:
    if token not in skill:
        fail("SKILL.md missing required behavior token: " + token)

for bad in [
    r"Foundry (?:authors|writes|creates) `?l9\.birth-payload/v1`?",
    r"remote birth .* before local",
]:
    if re.search(bad, skill, re.IGNORECASE):
        fail("SKILL.md contains forbidden authority statement matching: " + bad)

expertise = load_yaml(ROOT / "references/expertise_model.yaml").get("expertise_model", {})
limits = {
    "experts": 5,
    "doctrine": 10,
    "invariants": 10,
    "authority_hierarchy": 5,
    "activation_signals": 5,
    "reject_signals": 5,
    "adapters": 3,
    "failure_modes": 5,
    "leverage_points": 5,
}
for field, limit in limits.items():
    value = expertise.get(field)
    if not isinstance(value, list) or not value:
        fail(f"expertise field missing/empty: {field}")
    elif len(value) > limit:
        fail(f"expertise field exceeds cap {field}: {len(value)} > {limit}")

activation = load_yaml(ROOT / "references/activation-qualification.yaml")
cases = activation.get("cases", [])
if not isinstance(cases, list) or len(cases) != 10:
    fail("activation qualification must contain exactly 10 cases")
else:
    positive = [c for c in cases if c.get("expected") == "ACTIVATE"]
    negative = [c for c in cases if c.get("expected") == "REJECT"]
    if len(positive) != 5 or len(negative) != 5:
        fail("activation qualification must contain 5 ACTIVATE and 5 REJECT cases")
    signals = set(expertise.get("activation_signals", [])) | set(
        expertise.get("reject_signals", [])
    )
    for case in cases:
        if case.get("matched_signal") not in signals:
            fail(f"activation case {case.get('id')} references unknown signal")

report = load_yaml(ROOT / "references/skill_intelligence_report.yaml").get(
    "skill_intelligence_report", {}
)
if report.get("tier_decision") != "exemplary":
    fail("skill intelligence report does not claim exemplary")
gates = report.get("exemplary_gate_results", {})
for name, status in gates.items():
    if str(status).upper() != "PASS":
        fail(f"exemplary gate not PASS: {name}={status}")

# Every reference is reachable from the control plane (the intelligence files are
# also required above).
for ref in sorted((ROOT / "references").glob("*")):
    if not ref.is_file():
        continue
    token = f"references/{ref.name}"
    if token not in skill:
        fail("unlinked reference: " + token)

# Python files must parse/compile without creating cache in the skill tree.
for script in sorted((ROOT / "scripts").glob("*.py")):
    try:
        py_compile.compile(str(script), cfile="/tmp/foundry-skill-compile.pyc", doraise=True)
    except py_compile.PyCompileError as exc:
        fail(f"python compile failed {script.name}: {exc.msg}")

if errors:
    for error in errors:
        print("FAIL:", error, file=sys.stderr)
    print(f"FOUNDRY_SKILL_CONTRACT: FAIL ({len(errors)} errors)", file=sys.stderr)
    raise SystemExit(1)
print("FOUNDRY_SKILL_CONTRACT: PASS")
print("activation_cases=10 positive=5 reject=5")
print("birth_manifest_owner=l9-repo-template")
print("tier=exemplary")

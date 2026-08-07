#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

REQUIRED = [
    "SKILL.md",
    "agents/meta.yaml",
    "expertise_model.yaml",
    "skill_intelligence_report.yaml",
    "schemas/plan-document.schema.json",
    "references/planning-doctrine.md",
    "references/plan-quality-gates.md",
    "references/plan-router.yaml",
    "references/plan-workflow.md",
    "references/spec-workflow.md",
    "references/engineering-ticket-template.md",
    "references/plan-stress-test.md",
    "references/first-order-leverage.md",
    "references/convergence-block.md",
    "references/gmp-phase0-handoff.md",
    "references/validation-checklist.md",
    "references/plan-quality-rubric.md",
    "scripts/validate_plan_document.py",
    "scripts/validate_pack_structure.py",
    "scripts/validate_exemplary_skill.py",
    "scripts/route_plan.py",
    "scripts/render_plan_markdown.py",
    "scripts/emit_gmp_phase0.py",
    "scripts/self_test.py",
    "fixtures/plan_pass.json",
    "fixtures/plan_fail_format.json",
    "fixtures/plan_fail_shallow.json",
    "fixtures/plan_fail_ungrounded.json",
    "fixtures/plan_fail_quality.json",
    "assets/activation-cases.json",
    "assets/route-cases.json",
]

# Affirmative permission to skip depth — not the words "omit" in "do not omit".
FORBIDDEN_PHRASES = [
    "rapid may omit",
    "may omit ceremony",
    "may omit mandatory",
    "skip stress-test for efficiency",
    "omit ceremony that does not",
]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    errors = []
    for rel in REQUIRED:
        if not (root / rel).is_file():
            errors.append(f"missing required file: {rel}")
    skill = (root / "SKILL.md").read_text(encoding="utf-8") if (root / "SKILL.md").is_file() else ""
    for phrase in FORBIDDEN_PHRASES:
        if phrase in skill.lower():
            errors.append(f"forbidden doctrine phrase in SKILL.md: {phrase}")
    doctrine = root / "references/planning-doctrine.md"
    if doctrine.is_file():
        text = doctrine.read_text(encoding="utf-8").lower()
        if "fake optimization" not in text and "less rework" not in text:
            errors.append("planning-doctrine.md missing anti-rework doctrine")
    if "validate_plan_document.py" not in skill:
        errors.append("SKILL.md Validation must reference validate_plan_document.py")
    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1
    print("PASS: pack structure")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

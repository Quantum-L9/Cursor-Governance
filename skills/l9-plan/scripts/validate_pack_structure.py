#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from paths import safe_cli_path

SKILL_MD = "SKILL.md"

REQUIRED = [
    SKILL_MD,
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
    "scripts/paths.py",
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


def _missing_required(root: Path) -> list[str]:
    return [f"missing required file: {rel}" for rel in REQUIRED if not (root / rel).is_file()]


def _doctrine_errors(root: Path, skill: str) -> list[str]:
    errors: list[str] = []
    lowered = skill.lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase in lowered:
            errors.append(f"forbidden doctrine phrase in {SKILL_MD}: {phrase}")
    doctrine = root / "references/planning-doctrine.md"
    if doctrine.is_file():
        text = doctrine.read_text(encoding="utf-8").lower()
        if "fake optimization" not in text and "less rework" not in text:
            errors.append("planning-doctrine.md missing anti-rework doctrine")
    if "validate_plan_document.py" not in skill:
        errors.append(f"{SKILL_MD} Validation must reference validate_plan_document.py")
    return errors


def main() -> int:
    root = safe_cli_path(sys.argv[1] if len(sys.argv) > 1 else ".")
    skill_path = root / SKILL_MD
    skill = skill_path.read_text(encoding="utf-8") if skill_path.is_file() else ""
    errors = _missing_required(root) + _doctrine_errors(root, skill)
    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1
    print("PASS: pack structure")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

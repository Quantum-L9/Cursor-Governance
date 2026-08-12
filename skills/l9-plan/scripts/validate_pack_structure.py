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
    "references/plan-workflow-pe-autonomy.md",
    "references/executable-plan.pe-autonomy.template.md",
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
    "scripts/render_plan_pe_autonomy.py",
    "scripts/sync_cursor_plan_template.py",
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


def _skill_version(skill: str) -> tuple[int, ...] | None:
    for line in skill.splitlines():
        if line.startswith("version:"):
            raw = line.split(":", 1)[1].strip().strip("\"'")
            try:
                return tuple(int(part) for part in raw.split("."))
            except ValueError:
                return None
    return None


def _forbidden_phrase_errors(skill: str) -> list[str]:
    lowered = skill.lower()
    return [
        f"forbidden doctrine phrase in {SKILL_MD}: {phrase}"
        for phrase in FORBIDDEN_PHRASES
        if phrase in lowered
    ]


def _pe_marker_errors(skill: str) -> list[str]:
    required = (
        (
            "validate_plan_document.py",
            f"{SKILL_MD} Validation must reference validate_plan_document.py",
        ),
        (
            "plan-workflow-pe-autonomy.md",
            f"{SKILL_MD} must default plan mode to plan-workflow-pe-autonomy.md",
        ),
        (
            "executable-plan.pe-autonomy.template.md",
            f"{SKILL_MD} must reference executable-plan.pe-autonomy.template.md",
        ),
        ("render_plan_pe_autonomy.py", f"{SKILL_MD} must reference render_plan_pe_autonomy.py"),
    )
    errors = [msg for needle, msg in required if needle not in skill]
    version = _skill_version(skill)
    if version is None or version < (4, 0, 0):
        errors.append(f"{SKILL_MD} version must be >= 4.0.0 (PE+autonomy default)")
    return errors


def _doctrine_file_errors(root: Path) -> list[str]:
    doctrine = root / "references/planning-doctrine.md"
    if not doctrine.is_file():
        return []
    text = doctrine.read_text(encoding="utf-8").lower()
    errors: list[str] = []
    if "fake optimization" not in text and "less rework" not in text:
        errors.append("planning-doctrine.md missing anti-rework doctrine")
    if "program-execution" not in text and "@environment/program-execution" not in text:
        errors.append("planning-doctrine.md missing PE execute-path doctrine")
    return errors


def _doctrine_errors(root: Path, skill: str) -> list[str]:
    return _forbidden_phrase_errors(skill) + _doctrine_file_errors(root) + _pe_marker_errors(skill)


def _ssot_errors(root: Path) -> list[str]:
    """Require first-class executable plan template SSOT in the governance repo."""
    repo_root = root.resolve().parents[1] if root.name == "l9-plan" else root.resolve()
    # When invoked as `python3 scripts/validate_pack_structure.py .` from skill root:
    if (root / SKILL_MD).is_file():
        repo_root = root.resolve().parents[1]
    ssot = (
        repo_root
        / "environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md"
    )
    manifest = repo_root / "environment/contracts/execution/MANIFEST.yaml"
    errors: list[str] = []
    if not ssot.is_file():
        errors.append(f"missing first-class plan template SSOT: {ssot}")
    if not manifest.is_file():
        errors.append(f"missing execution contracts MANIFEST: {manifest}")
    link = root / "references/executable-plan.pe-autonomy.template.md"
    if link.is_symlink():
        try:
            if not link.resolve().is_file():
                errors.append("executable-plan.pe-autonomy.template.md symlink is dangling")
        except OSError as exc:
            errors.append(f"executable-plan.pe-autonomy.template.md symlink unreadable: {exc}")
    elif link.is_file():
        errors.append(
            "executable-plan.pe-autonomy.template.md must be a symlink to "
            "environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md"
        )
    return errors


def main() -> int:
    root = safe_cli_path(sys.argv[1] if len(sys.argv) > 1 else ".")
    skill_path = root / SKILL_MD
    skill = skill_path.read_text(encoding="utf-8") if skill_path.is_file() else ""
    errors = _missing_required(root) + _doctrine_errors(root, skill) + _ssot_errors(root)
    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1
    print("PASS: pack structure")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

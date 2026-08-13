#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import py_compile
import re
from pathlib import Path

REQUIRED_FILES = {
    "SKILL.md",
    "README.md",
    "VALIDATION.md",
    "expertise_model.yaml",
    "skill_intelligence_report.yaml",
    "scripts/audit_repository.py",
    "scripts/compile_contract.py",
    "scripts/validate_contract.py",
    "scripts/run_validation_matrix.py",
    "scripts/compare_audits.py",
    "scripts/validate_pr_pack.py",
    "scripts/render_pr_body.py",
    "scripts/self_test.py",
    "references/authority-and-scope.md",
    "references/findings-taxonomy.md",
    "references/renovation-method.md",
    "references/stack-adapters.md",
    "references/pr-lifecycle.md",
    "references/convergence-and-failure.md",
    "references/output-contract.md",
}

REQUIRED_EXPERTISE_KEYS = {
    "experts:",
    "doctrine:",
    "invariants:",
    "authority_hierarchy:",
    "activation_signals:",
    "reject_signals:",
    "adapters:",
    "failure_modes:",
    "leverage_points:",
}

REQUIRED_REPORT_GATES = {
    "activation_precision: PASS",
    "adapter_architecture: PASS",
    "evidence_hierarchy: PASS",
    "doctrine_extraction: PASS",
    "expert_heuristics: PASS",
    "failure_modes: PASS",
    "leverage_model: PASS",
    "self_improvement_hook: PASS",
    "compiler_enforcement_gates: PASS",
    "skill_intelligence_report: PASS",
    "tier_decision: exemplary",
}


def frontmatter(skill_text: str) -> tuple[dict[str, str], str | None]:
    if not skill_text.startswith("---\n"):
        return {}, "SKILL.md must begin with YAML frontmatter"
    end = skill_text.find("\n---\n", 4)
    if end < 0:
        return {}, "SKILL.md frontmatter is not closed"
    values: dict[str, str] = {}
    for raw in skill_text[4:end].splitlines():
        if not raw.strip():
            continue
        if raw.startswith((" ", "\t")):
            continue
        if ":" not in raw:
            return {}, f"invalid frontmatter line: {raw}"
        key, value = raw.split(":", 1)
        values[key.strip()] = value.strip()
    return values, None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the L9 repository renovation skill's exemplary gates."
    )
    parser.add_argument("skill", type=Path, nargs="?", default=Path("."))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = args.skill.resolve()
    errors: list[str] = []

    missing = sorted(path for path in REQUIRED_FILES if not (root / path).is_file())
    if missing:
        errors.append(f"missing required files: {', '.join(missing)}")

    skill_path = root / "SKILL.md"
    skill_text = skill_path.read_text(encoding="utf-8") if skill_path.exists() else ""
    metadata, metadata_error = frontmatter(skill_text)
    if metadata_error:
        errors.append(metadata_error)
    # name and description are required; disable-model-invocation is the optional
    # governance flag that marks a high-blast-radius skill explicit-only.
    allowed_keys = {"name", "description", "paths", "disable-model-invocation", "metadata"}
    if "name" not in metadata or "description" not in metadata or set(metadata) - allowed_keys:
        errors.append(
            "SKILL.md frontmatter must contain name, description, and only native Cursor keys"
        )
    if metadata.get("name") != root.name:
        errors.append("frontmatter name must match skill directory")
    if metadata.get("name", "") != metadata.get("name", "").lower():
        errors.append("skill name must be lowercase")
    if metadata.get("description", "") != metadata.get("description", "").lower():
        errors.append("description must be lowercase")
    if len(metadata.get("description", "")) < 120:
        errors.append("description is not specific enough to drive activation")

    for reference in (
        sorted((root / "references").glob("*.md")) if (root / "references").exists() else []
    ):
        relative = reference.relative_to(root).as_posix()
        if relative not in skill_text:
            errors.append(f"unlinked reference: {relative}")
    for script in sorted((root / "scripts").glob("*.py")) if (root / "scripts").exists() else []:
        if script.name in {"common.py", "validate_exemplary_skill.py"}:
            continue
        relative = script.relative_to(root).as_posix()
        if relative not in skill_text:
            errors.append(f"unlinked script: {relative}")

    expertise = (
        (root / "expertise_model.yaml").read_text(encoding="utf-8")
        if (root / "expertise_model.yaml").exists()
        else ""
    )
    for key in REQUIRED_EXPERTISE_KEYS:
        if key not in expertise:
            errors.append(f"expertise model missing {key}")
    report = (
        (root / "skill_intelligence_report.yaml").read_text(encoding="utf-8")
        if (root / "skill_intelligence_report.yaml").exists()
        else ""
    )
    for gate in REQUIRED_REPORT_GATES:
        if gate not in report:
            errors.append(f"intelligence report missing gate: {gate}")

    required_skill_phrases = [
        "## Authority order",
        "## Reject and reroute",
        "## Expert review rules",
        "## Failure boundaries",
        "## After-use improvement",
        "RENOVATE_TO_PR",
        "three implementation-validation cycles",
    ]
    for phrase in required_skill_phrases:
        if phrase not in skill_text:
            errors.append(f"SKILL.md missing behavioral control: {phrase}")

    forbidden_examples = [
        root / "scripts/example.py",
        root / "references/api_reference.md",
        root / "assets/example_asset.txt",
    ]
    if any(path.exists() for path in forbidden_examples):
        errors.append("initializer example files remain")

    scripts_dir = root / "scripts"
    if scripts_dir.is_dir():
        for script in sorted(scripts_dir.glob("*.py")):
            try:
                py_compile.compile(str(script), doraise=True)
            except py_compile.PyCompileError as exc:
                errors.append(f"script compilation failed: {exc}")

    placeholder_patterns = [
        re.compile(r"\[TODO[^\]]*\]", re.I),
        re.compile(r"REPLACE_ME", re.I),
        re.compile(r"example resource directories", re.I),
    ]
    for path in root.rglob("*"):
        if (
            not path.is_file()
            or "__pycache__" in path.parts
            or path.name == "validate_exemplary_skill.py"
        ):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in placeholder_patterns:
            if pattern.search(text):
                errors.append(
                    f"unfinished scaffold marker in {path.relative_to(root)}: {pattern.pattern}"
                )

    payload = {
        "valid": not errors,
        "tier": "exemplary" if not errors else "failed",
        "errors": errors,
        "skill": str(root),
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif errors:
        for error in errors:
            print(f"ERROR: {error}")
    else:
        print(
            "EXEMPLARY PASS: activation, authority, heuristics, adapters, failure controls, scripts, and packaging structure"
        )
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

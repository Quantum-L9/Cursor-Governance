#!/usr/bin/env python3
"""Validate docs-code divergence and leverage-based CLI revision synthesis integration."""

from __future__ import annotations

import json
from pathlib import Path
import sys

from build_commit_pack import calculate_leverage_score, leverage_decision

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    errors: list[str] = []
    required = [
        ROOT / "references" / "docs-code-capability-divergence.md",
        ROOT / "references" / "revision-synthesis-leverage-adapter.md",
        ROOT / "references" / "source-domain-agnostic-leverage.yaml",
    ]
    for path in required:
        if not path.is_file():
            errors.append(f"missing {path.relative_to(ROOT)}")
    if errors:  # do not attempt unconditional reads of files reported missing
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1

    source = (ROOT / "references" / "source-domain-agnostic-leverage.yaml").read_text(encoding="utf-8")
    for snippet in (
        "A move is high quality when it improves future moves.",
        "future_action_acceleration: 0.22",
        "existing_asset_amplification: 0.20",
        "reusable_system_value: 0.18",
        "reject_or_reframe_below: 2.5",
        "approve_minimum: 3.5",
        "prioritize_minimum: 4.0",
    ):
        if snippet not in source:
            errors.append(f"source leverage kernel missing doctrine: {snippet}")

    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    skill_lower = skill.lower()
    for snippet in (
        "docs-code-capability-divergence.md",
        "revision-synthesis-leverage-adapter.md",
        "CLI_REVISION_SYNTHESIS.json",
        "DOCS_CODE_DIVERGENCE_FINDINGS.md",
        "every finding must map to a target",
        "selected_option_ids",
    ):
        if snippet.lower() not in skill_lower:
            errors.append(f"SKILL.md missing revision-synthesis invariant: {snippet}")

    schema = json.loads((ROOT / "schemas" / "pack-spec.schema.json").read_text(encoding="utf-8"))
    if "revision_synthesis" not in schema.get("required", []):
        errors.append("pack spec schema does not require revision_synthesis")
    if not isinstance(schema.get("properties", {}).get("revision_synthesis"), dict):
        errors.append("pack spec schema missing revision_synthesis object")
    for name in ("revisionFinding", "revisionTarget", "revisionOption", "leverageDimensions"):
        if name not in schema.get("$defs", {}):
            errors.append(f"pack spec schema missing $defs.{name}")

    example = json.loads((ROOT / "assets" / "pack-spec.example.json").read_text(encoding="utf-8"))
    synthesis = example.get("revision_synthesis", {})
    findings = {item.get("id"): item for item in synthesis.get("findings", []) if isinstance(item, dict)}
    targets = {item.get("id"): item for item in synthesis.get("targets", []) if isinstance(item, dict)}
    options = {item.get("id"): item for item in synthesis.get("options", []) if isinstance(item, dict)}
    if not findings or not targets or not options:
        errors.append("example does not contain complete finding-target-option synthesis")
    if not any(item.get("kind") == "docs_code_divergence" for item in findings.values()):
        errors.append("example does not exercise docs-code divergence")
    if not synthesis.get("unresolved_divergence_ids"):
        errors.append("example does not preserve an out-of-scope docs-code divergence")
    finding_refs = {fid for target in targets.values() for fid in target.get("source_finding_ids", [])}
    if finding_refs != set(findings):
        errors.append("example does not map every finding to a target")
    target_refs = {tid for option in options.values() for tid in option.get("target_ids", [])}
    if target_refs != set(targets):
        errors.append("example does not map every target to an option")
    for option_id, option in options.items():
        try:
            calculated = calculate_leverage_score(option.get("leverage_dimensions", {}))
        except Exception as exc:
            errors.append(f"example option {option_id} has invalid dimensions: {exc}")
            continue
        if option.get("leverage_score") != calculated:
            errors.append(f"example option {option_id} leverage score mismatch")
        if option.get("decision") != leverage_decision(calculated):
            errors.append(f"example option {option_id} decision mismatch")

    builder = (ROOT / "scripts" / "build_commit_pack.py").read_text(encoding="utf-8")
    validator = (ROOT / "scripts" / "validate_commit_pack.py").read_text(encoding="utf-8")
    for snippet in (
        "CLI_REVISION_SYNTHESIS.json",
        "CLI_REVISION_PLAN.md",
        "DOCS_CODE_DIVERGENCE_FINDINGS.md",
        "calculate_leverage_score",
        "unresolved_divergence_ids",
        "selected_revision_option_ids",
    ):
        if snippet not in builder or snippet not in validator:
            errors.append(f"builder/validator missing revision-synthesis enforcement: {snippet}")

    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: docs-code divergence and leverage synthesis integration is locked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

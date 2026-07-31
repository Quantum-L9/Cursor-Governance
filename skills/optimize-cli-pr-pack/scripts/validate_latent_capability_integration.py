#!/usr/bin/env python3
"""Validate latent-capability reachability integration across the Skill pack."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    errors: list[str] = []
    required = [
        ROOT / "references" / "latent-capability-activation.md",
        ROOT / "references" / "source-dead-wiring-latent-capability-audit.md",
    ]
    for path in required:
        if not path.is_file():
            errors.append(f"missing {path.relative_to(ROOT)}")

    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    for snippet in (
        "latent-capability-activation.md",
        "bidirectional evidence",
        "dynamic dispatch",
        "WIRING_MAP.md",
        "LATENT_CAPABILITY_FINDINGS.json",
        "dormant_by_design",
    ):
        if snippet not in skill:
            errors.append(f"SKILL.md missing latent-capability invariant: {snippet}")

    schema = json.loads((ROOT / "schemas" / "pack-spec.schema.json").read_text(encoding="utf-8"))
    wiring = schema.get("properties", {}).get("wiring")
    if not isinstance(wiring, dict):
        errors.append("pack spec schema missing wiring object")
    defs = schema.get("$defs", {})
    for name in ("wiringFinding", "wiringEdge"):
        if name not in defs:
            errors.append(f"pack spec schema missing $defs.{name}")

    example = json.loads((ROOT / "assets" / "pack-spec.example.json").read_text(encoding="utf-8"))
    if example.get("optimization", {}).get("strategy") != "activate_latent_capability":
        errors.append("example does not exercise latent-capability activation")
    record = example.get("wiring", {})
    if record.get("convergence_status") != "converged":
        errors.append("example wiring is not converged")
    selected = set(record.get("selected_finding_ids", []))
    findings = {
        item.get("id"): item for item in record.get("findings", []) if isinstance(item, dict)
    }
    for finding_id in selected:
        finding = findings.get(finding_id)
        if not finding:
            errors.append(f"selected finding missing: {finding_id}")
            continue
        if finding.get("verdict") != "activate":
            errors.append(f"selected finding is not activate: {finding_id}")
        if not finding.get("definition_evidence") or not finding.get("consumer_evidence"):
            errors.append(f"selected finding lacks bidirectional evidence: {finding_id}")
        if finding.get("dynamic_dispatch_checked") is not True:
            errors.append(f"selected finding lacks dynamic-dispatch proof: {finding_id}")
        if finding.get("dormant_by_design") is not False:
            errors.append(f"selected finding is dormant by design or unclassified: {finding_id}")

    builder = (ROOT / "scripts" / "build_commit_pack.py").read_text(encoding="utf-8")
    pack_validator = (ROOT / "scripts" / "validate_commit_pack.py").read_text(encoding="utf-8")
    for snippet in ("WIRING_MAP.md", "LATENT_CAPABILITY_FINDINGS.json", "selected_wiring_findings"):
        if snippet not in builder or snippet not in pack_validator:
            errors.append(f"builder/validator missing wiring artifact enforcement: {snippet}")

    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: latent-capability reachability integration is locked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Static contract checks for the Repository Documentation Obligation Compiler skill."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

PACK = Path(__file__).resolve().parents[1]
SKILL = PACK / "SKILL.md"
POLICY = PACK / "references/doc-surface-policy.yaml"
OBLIGATION = PACK / "contracts/documentation-obligation.schema.json"
RECEIPT = PACK / "contracts/repo-docs-receipt.schema.json"
ANALYSIS = PACK / "scripts/doc_surface_analysis.py"


def main() -> int:
    errors: list[str] = []
    text = SKILL.read_text(encoding="utf-8") if SKILL.is_file() else ""
    required_tokens = [
        "Repository Documentation Obligation Compiler",
        "documentation-obligation.schema.json",
        "repo-docs-receipt.schema.json",
        "l9-intelligence-harvest",
        "readme-pipeline-v1",
        "doc_surface_analysis.py",
        "makefile-contract-v1",
        "python-project-contract-v1",
        "root-file-protection.json",
        "kernels/Recursive Alignment.md",
        "kernels/Validate & Repair.md",
        "Passed",
        "Failed",
        "Skipped",
        "Unknown",
        "NotApplicable",
    ]
    for token in required_tokens:
        if token not in text:
            errors.append(f"SKILL.md missing {token!r}")
    if POLICY.is_file():
        policy = yaml.safe_load(POLICY.read_text(encoding="utf-8"))
        if policy.get("owner") != "l9-update-agent-docs":
            errors.append("policy owner drift")
        if policy.get("schema") != "l9.repo-docs.surface-policy.v3":
            errors.append("policy schema drift")
        if policy.get("semantic_harvest", {}).get("owner") != "l9-intelligence-harvest":
            errors.append("Harvest ownership drift")
        for surface, analyzer in (
            ("makefile_contract", "makefile-contract-v1"),
            ("python_project_contract", "python-project-contract-v1"),
        ):
            actual = (
                policy.get("surfaces", {})
                .get(surface, {})
                .get("analysis", {})
                .get("analyzer")
            )
            if actual != analyzer:
                errors.append(
                    f"{surface} analyzer drift: expected {analyzer!r}, got {actual!r}"
                )
    else:
        errors.append("missing doc-surface-policy.yaml")
    if not ANALYSIS.is_file():
        errors.append("missing doc_surface_analysis.py")
    for path, expected in (
        (OBLIGATION, "l9.repo-docs.obligation.v1"),
        (RECEIPT, "l9.repo-docs.receipt.v3"),
    ):
        if not path.is_file():
            errors.append(f"missing {path.name}")
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if expected not in json.dumps(data):
            errors.append(f"{path.name} missing schema identity {expected}")
    if errors:
        print("FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Validate cross-file wiring for the L9 Coding Agent skill pack."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except Exception as exc:
    raise SystemExit(f"PyYAML is required: {exc}")


def flatten(groups: dict) -> set[str]:
    out: set[str] = set()
    for values in groups.values():
        if isinstance(values, list):
            out.update(str(x) for x in values)
    return out


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]).resolve()
    manifest_path = root / "runtime" / "MANIFEST.yaml"
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest = data["manifest"]
    errors: list[str] = []
    if manifest.get("name") != "l9-coding-agent":
        errors.append("manifest name mismatch")
    if manifest.get("context_policy") != "lazy_by_stage":
        errors.append("manifest context_policy must be lazy_by_stage")
    if manifest.get("bootstrap_router") != "runtime/BOOTSTRAP.yaml":
        errors.append("manifest bootstrap_router mismatch")

    refs = (
        set(data.get("bootstrap_load", []))
        | flatten(data.get("load_groups", {}))
        | flatten(data.get("conditional_load_groups", {}))
    )
    for rel in sorted(refs):
        if not (root / rel).is_file():
            errors.append(f"missing routed artifact: {rel}")
    for key, item in data.get("semantic_owners", {}).items():
        rel = item.get("owner")
        if rel and not (root / rel).is_file():
            errors.append(f"missing semantic owner {key}: {rel}")

    for rel in ["schemas/execution-contract.schema.json", "schemas/execution-receipt.schema.json"]:
        try:
            json.loads((root / rel).read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"invalid json {rel}: {exc}")

    evals = yaml.safe_load(
        (root / "evals" / "BEHAVIOR_CONFORMANCE.yaml").read_text(encoding="utf-8")
    )
    cases = evals.get("eval_suite", {}).get("cases", [])
    if len(cases) < 40:
        errors.append("behavior conformance suite is too small for v1.3 repaired runtime")

    skill = (root / "SKILL.md").read_text(encoding="utf-8")
    for required in [
        "runtime/BOOTSTRAP.yaml",
        "runtime/RUN_STATE.yaml",
        "runtime/STATE_MACHINE.yaml",
        "contracts/CONVERGENCE.yaml",
    ]:
        if required not in skill:
            errors.append(f"SKILL.md does not route to {required}")

    for required_term in ["inspection scope", "dependency-aware target graph", "delivered state"]:
        if required_term.lower() not in skill.lower():
            errors.append(f"SKILL.md missing v1.3 readiness control: {required_term}")

    lazy_script = root / "scripts" / "validate_lazy_bootstrap.py"
    result = subprocess.run(
        [sys.executable, str(lazy_script), str(root)], text=True, capture_output=True
    )
    if result.returncode != 0:
        errors.append(
            "lazy bootstrap validation failed: "
            + (result.stdout + result.stderr).strip().replace("\n", " | ")
        )

    if errors:
        for error in errors:
            print("FAIL:", error)
        return 1
    print(
        f"PASS: {manifest['name']} {manifest['version']} runtime alignment; "
        + f"{len(cases)} behavior cases; lazy bootstrap closed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

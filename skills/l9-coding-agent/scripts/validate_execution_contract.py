#!/usr/bin/env python3
"""Validate minimum L9 Coding Agent execution-contract structure."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REQUIRED = {
    "contract_id",
    "objective",
    "target",
    "in_scope",
    "out_of_scope",
    "locked_invariants",
    "acceptance_criteria",
    "forbidden_actions",
    "validation_obligations",
    "delivery_mode",
    "authority_refs",
}

LIST_FIELDS = (
    "authority_refs",
    "in_scope",
    "out_of_scope",
    "locked_invariants",
    "acceptance_criteria",
    "forbidden_actions",
    "validation_obligations",
)


def load(path: Path):
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    try:
        import yaml
    except Exception as exc:
        raise SystemExit(f"YAML input requires PyYAML: {exc}")
    return yaml.safe_load(text)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_execution_contract.py <contract.json|yaml>", file=sys.stderr)
        return 2
    data = load(Path(sys.argv[1]))
    if not isinstance(data, dict):
        print("FAIL: contract must be an object")
        return 1
    missing = sorted(REQUIRED - set(data))
    if missing:
        print("FAIL: missing required fields: " + ", ".join(missing))
        return 1
    if not isinstance(data.get("target"), dict) or not data["target"].get("repository_or_artifact"):
        print("FAIL: target.repository_or_artifact is required")
        return 1
    for name in LIST_FIELDS:
        value = data.get(name)
        if not isinstance(value, list):
            print(f"FAIL: {name} must be an array")
            return 1
    if not data["acceptance_criteria"]:
        print("FAIL: acceptance_criteria must not be empty")
        return 1
    if not data["validation_obligations"]:
        print("FAIL: validation_obligations must not be empty")
        return 1
    inspection = data.get("inspection_scope")
    modification = data.get("modification_scope")
    if inspection is not None and not isinstance(inspection, list):
        print("FAIL: inspection_scope must be an array when present")
        return 1
    if modification is not None and not isinstance(modification, list):
        print("FAIL: modification_scope must be an array when present")
        return 1
    unknowns = data.get("unresolved_unknowns", [])
    if unknowns:
        print(
            "WARN: unresolved_unknowns present; runtime must classify materiality before mutation"
        )
    print("PASS: execution contract minimum structure is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

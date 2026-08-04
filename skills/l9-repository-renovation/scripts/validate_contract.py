#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from common import load_json

REQUIRED_TOP_LEVEL = {
    "schema_version",
    "contract_id",
    "objective",
    "repository",
    "mode",
    "authority_decisions",
    "scope",
    "phases",
    "validation_matrix",
    "acceptance_criteria",
    "rollback",
    "pr_policy",
    "unknowns",
}

PLACEHOLDER_PATTERNS = [
    re.compile(r"\bTBD\b", re.I),
    re.compile(r"\bTO_BE_DECIDED\b", re.I),
    re.compile(r"\bINSERT_HERE\b", re.I),
    re.compile(r"<[^>]+>"),
]


def validate(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_TOP_LEVEL - set(contract))
    if missing:
        errors.append(f"missing top-level keys: {', '.join(missing)}")
    if contract.get("schema_version") != "renovation-contract-1.0":
        errors.append("schema_version must be renovation-contract-1.0")
    repository = contract.get("repository", {})
    for key in ("name", "path", "base_ref", "target_branch"):
        if not repository.get(key):
            errors.append(f"repository.{key} is required")
    if not repository.get("base_commit"):
        errors.append("repository.base_commit is required for an immutable renovation baseline")
    scope = contract.get("scope", {})
    allowed = scope.get("allowed_paths", [])
    forbidden = scope.get("forbidden_paths", [])
    if not isinstance(allowed, list) or not allowed:
        errors.append("scope.allowed_paths must be a non-empty list")
    if "**/*" in allowed or "*" in allowed:
        errors.append("scope.allowed_paths may not grant the entire repository")
    overlap = sorted(set(allowed) & set(forbidden))
    if overlap:
        errors.append(f"paths are both allowed and forbidden: {', '.join(overlap)}")
    if not scope.get("preserved_behavior"):
        errors.append("scope.preserved_behavior is required")
    if not scope.get("forbidden_capabilities"):
        errors.append("scope.forbidden_capabilities is required")

    phases = contract.get("phases", [])
    if not isinstance(phases, list) or not phases:
        errors.append("at least one implementation phase is required")
    phase_names: set[str] = set()
    for index, phase in enumerate(phases):
        name = phase.get("name") if isinstance(phase, dict) else None
        if not name:
            errors.append(f"phases[{index}].name is required")
            continue
        if name in phase_names:
            errors.append(f"duplicate phase name: {name}")
        phase_names.add(name)
        if not phase.get("objective"):
            errors.append(f"phase {name} requires an objective")
        if not phase.get("checkpoint_requires_green"):
            errors.append(f"phase {name} must require a green checkpoint")

    commands = contract.get("validation_matrix", [])
    command_ids: set[str] = set()
    if not commands:
        errors.append("validation_matrix must not be empty")
    for index, item in enumerate(commands):
        if not isinstance(item, dict):
            errors.append(f"validation_matrix[{index}] must be an object")
            continue
        command_id = item.get("id")
        if not command_id:
            errors.append(f"validation_matrix[{index}].id is required")
        elif command_id in command_ids:
            errors.append(f"duplicate validation id: {command_id}")
        command_ids.add(command_id)
        if not isinstance(item.get("command"), list) or not item.get("command"):
            errors.append(f"validation command {command_id or index} must be a non-empty argv list")
        if int(item.get("timeout_seconds", 0)) <= 0:
            errors.append(f"validation command {command_id or index} requires a positive timeout")

    pr_policy = contract.get("pr_policy", {})
    if pr_policy.get("max_pull_requests") != 1:
        errors.append("pr_policy.max_pull_requests must equal 1")
    if pr_policy.get("merge_authorized") is not False:
        errors.append("merge must remain unauthorized in the generated contract")
    required_authorizations = set(pr_policy.get("separate_authorization_required", []))
    expected_authorizations = {"stage", "commit", "push", "create_pr", "remediation_push", "merge"}
    if not expected_authorizations.issubset(required_authorizations):
        errors.append("pr_policy must name every independent GitHub write authorization")

    unknowns = contract.get("unknowns", [])
    if unknowns:
        errors.append("unresolved contract unknowns block implementation")

    serialized = json.dumps(contract, sort_keys=True)
    for pattern in PLACEHOLDER_PATTERNS:
        if pattern.search(serialized):
            errors.append(f"placeholder pattern found: {pattern.pattern}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a repository renovation contract.")
    parser.add_argument("contract", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    contract = load_json(args.contract)
    errors = validate(contract)
    payload = {"valid": not errors, "errors": errors, "contract": str(args.contract)}
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif errors:
        for error in errors:
            print(f"ERROR: {error}")
    else:
        print("VALID: renovation contract")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

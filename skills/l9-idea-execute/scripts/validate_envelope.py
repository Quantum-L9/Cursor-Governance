#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from _common import ContractError, assert_acyclic, load_data, nonempty_string, require_list, require_mapping

SCHEMA = "l9.idea-execution-envelope/v1"
DECISIONS = {"GO", "CONDITIONAL"}
FORBIDDEN_REQUIREMENT_KEYS = {"owner", "adapter", "executor", "skill", "provider", "model"}


def validate_envelope(data: Any) -> dict[str, Any]:
    root = require_mapping(data, "envelope")
    errors: list[str] = []

    if root.get("schema") != SCHEMA:
        errors.append(f"schema must equal {SCHEMA}")

    idea = root.get("idea")
    if not isinstance(idea, dict):
        errors.append("idea must be a mapping")
    else:
        for key in ("id", "title"):
            if not nonempty_string(idea.get(key)):
                errors.append(f"idea.{key} must be a non-empty string")
        if idea.get("decision_status") not in DECISIONS:
            errors.append("idea.decision_status must be GO or CONDITIONAL")
        refs = idea.get("source_refs", [])
        if not isinstance(refs, list) or not all(nonempty_string(x) for x in refs):
            errors.append("idea.source_refs must be a list of non-empty strings")

    reqs = root.get("requirements")
    if not isinstance(reqs, list) or not reqs:
        errors.append("requirements must be a non-empty list")
        reqs = []

    ids: set[str] = set()
    dep_edges: dict[str, set[str]] = {}
    for idx, req in enumerate(reqs):
        label = f"requirements[{idx}]"
        if not isinstance(req, dict):
            errors.append(f"{label} must be a mapping")
            continue
        forbidden = FORBIDDEN_REQUIREMENT_KEYS.intersection(req)
        if forbidden:
            errors.append(f"{label} must declare capabilities/outcomes, not executor fields: {sorted(forbidden)}")
        rid = req.get("id")
        if not nonempty_string(rid):
            errors.append(f"{label}.id must be a non-empty string")
            continue
        if rid in ids:
            errors.append(f"duplicate requirement id {rid}")
        ids.add(rid)
        if not nonempty_string(req.get("capability")):
            errors.append(f"{label}.capability must be a non-empty string")
        if not nonempty_string(req.get("target_state")):
            errors.append(f"{label}.target_state must be a non-empty string")
        if not isinstance(req.get("required"), bool):
            errors.append(f"{label}.required must be boolean")
        if req.get("capability") == "repository_change" and not nonempty_string(req.get("target_repo")):
            errors.append(f"{label}.target_repo is required for repository_change")
        deps = req.get("dependencies", [])
        if not isinstance(deps, list) or not all(nonempty_string(x) for x in deps):
            errors.append(f"{label}.dependencies must be a list of requirement ids")
            deps = []
        if rid in deps:
            errors.append(f"{label} cannot depend on itself")
        dep_edges[rid] = set(deps)
        for list_key in ("authority_refs", "unknown_ids"):
            value = req.get(list_key, [])
            if not isinstance(value, list) or not all(nonempty_string(x) for x in value):
                errors.append(f"{label}.{list_key} must be a list of non-empty strings")

    for rid, deps in dep_edges.items():
        for dep in deps:
            if dep not in ids:
                errors.append(f"requirement {rid} depends on unknown requirement {dep}")
    if not errors and ids:
        try:
            assert_acyclic(ids, dep_edges, "requirement graph")
        except ContractError as exc:
            errors.append(str(exc))

    chars = root.get("execution_characteristics", {})
    if not isinstance(chars, dict):
        errors.append("execution_characteristics must be a mapping")
    else:
        for key in ("cross_repository", "code_required", "runtime_validation_required"):
            if key in chars and not isinstance(chars[key], bool):
                errors.append(f"execution_characteristics.{key} must be boolean")
        for key in ("protected_actions", "repositories"):
            value = chars.get(key, [])
            if not isinstance(value, list) or not all(nonempty_string(x) for x in value):
                errors.append(f"execution_characteristics.{key} must be a list of non-empty strings")

    existing = root.get("existing_execution", {})
    if not isinstance(existing, dict):
        errors.append("existing_execution must be a mapping")
    else:
        for key in ("plan_refs", "contract_refs", "acceptance_refs", "rollback_refs", "handoff_refs"):
            value = existing.get(key, [])
            if not isinstance(value, list) or not all(nonempty_string(x) for x in value):
                errors.append(f"existing_execution.{key} must be a list of non-empty strings")

    if errors:
        raise ContractError("; ".join(errors))
    return root


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_envelope.py <IDEA_EXECUTION_ENVELOPE.yaml|json>", file=sys.stderr)
        return 2
    try:
        validate_envelope(load_data(Path(sys.argv[1])))
    except ContractError as exc:
        print(f"IDEA_EXECUTION_ENVELOPE: FAIL\n- {exc}", file=sys.stderr)
        return 1
    print("IDEA_EXECUTION_ENVELOPE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

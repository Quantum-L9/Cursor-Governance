#!/usr/bin/env python3
from __future__ import annotations

import sys
from typing import Any

from _common import ContractError, assert_acyclic, load_data, nonempty_string

SCHEMA = "l9.idea-execution-graph/v1"
TOPOLOGIES = {
    "NEW_PRODUCT_REPOSITORY",
    "SPECIALIZED_FACTORY",
    "EXISTING_REPO_CHANGE",
    "EXISTING_SYSTEM_CAMPAIGN",
}
ADMISSION = {"UNCHECKED", "COMPATIBLE", "BLOCKED"}


def validate_graph(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ContractError("graph must be a mapping")
    errors: list[str] = []
    if data.get("schema") != SCHEMA:
        errors.append(f"schema must equal {SCHEMA}")
    blockers = data.get("blockers")
    if not isinstance(blockers, list):
        errors.append("blockers must be a list")
        blockers = []
    expected_status = "BLOCKED" if blockers else "READY"
    if data.get("status") != expected_status:
        errors.append(f"status must be {expected_status} for current blockers")
    units = data.get("units")
    if not isinstance(units, list):
        errors.append("units must be a list")
        units = []

    ids: set[str] = set()
    req_ids: set[str] = set()
    edges: dict[str, set[str]] = {}
    for idx, unit in enumerate(units):
        label = f"units[{idx}]"
        if not isinstance(unit, dict):
            errors.append(f"{label} must be a mapping")
            continue
        uid = unit.get("id")
        if not nonempty_string(uid):
            errors.append(f"{label}.id must be a non-empty string")
            continue
        if uid in ids:
            errors.append(f"duplicate unit id {uid}")
        ids.add(uid)
        topology = unit.get("topology")
        if topology not in TOPOLOGIES:
            errors.append(f"{label}.topology is invalid")
        if not nonempty_string(unit.get("owner")) or not nonempty_string(unit.get("adapter")):
            errors.append(f"{label} must name owner and adapter")
        rids = unit.get("requirement_ids")
        if not isinstance(rids, list) or not rids or not all(nonempty_string(x) for x in rids):
            errors.append(f"{label}.requirement_ids must be a non-empty string list")
            rids = []
        for rid in rids:
            if rid in req_ids:
                errors.append(f"requirement {rid} appears in multiple units")
            req_ids.add(rid)
        repos = unit.get("target_repos")
        if not isinstance(repos, list) or not all(nonempty_string(x) for x in repos):
            errors.append(f"{label}.target_repos must be a string list")
            repos = []
        deps = unit.get("depends_on_units")
        if not isinstance(deps, list) or not all(nonempty_string(x) for x in deps):
            errors.append(f"{label}.depends_on_units must be a string list")
            deps = []
        if uid in deps:
            errors.append(f"{label} cannot depend on itself")
        edges[uid] = set(deps)
        if unit.get("admission_status") not in ADMISSION:
            errors.append(f"{label}.admission_status is invalid")

        if topology == "SPECIALIZED_FACTORY" and unit.get("adapter") == "l9-idea-foundry":
            errors.append(f"{label}: specialized factory cannot route through Foundry")
        if topology == "NEW_PRODUCT_REPOSITORY" and unit.get("adapter") != "l9-idea-foundry":
            errors.append(f"{label}: new product repository must use Foundry in registry v1")
        if topology == "EXISTING_REPO_CHANGE" and len(set(repos)) != 1:
            errors.append(f"{label}: bounded existing-repo unit must target exactly one repo")
        if topology == "EXISTING_SYSTEM_CAMPAIGN" and len(set(repos)) < 2:
            errors.append(f"{label}: campaign unit must target at least two repos in registry v1")

    for blocker in blockers:
        if not isinstance(blocker, dict) or not nonempty_string(blocker.get("code")):
            errors.append("each blocker must be a mapping with non-empty code")

    if not errors and ids:
        try:
            assert_acyclic(ids, edges, "execution graph")
        except ContractError as exc:
            errors.append(str(exc))

    if errors:
        raise ContractError("; ".join(errors))
    return data


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_graph.py <EXECUTION_GRAPH.yaml|json>", file=sys.stderr)
        return 2
    try:
        validate_graph(load_data(sys.argv[1]))
    except ContractError as exc:
        print(f"IDEA_EXECUTION_GRAPH: FAIL\n- {exc}", file=sys.stderr)
        return 1
    print("IDEA_EXECUTION_GRAPH: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

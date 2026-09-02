#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from _common import ContractError, dump_yaml, load_data, semantic_digest
from validate_envelope import validate_envelope

REGISTRY_PATH = Path(__file__).resolve().parent.parent / "references" / "capability-registry.yaml"


def _unit_for_req(req: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    rid = req["id"]
    return {
        "id": f"unit-{rid.lower()}",
        "topology": spec["topology"],
        "owner": spec["owner"],
        "adapter": spec["adapter"],
        "requirement_ids": [rid],
        "target_repos": [req["target_repo"]] if req.get("target_repo") else [],
        "depends_on_units": [],
        "admission_status": "UNCHECKED",
    }


def route_envelope(envelope: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    validate_envelope(envelope)
    special = registry.get("specialized_factories", {})
    generic = registry.get("generic_routes", {})
    requirements: list[dict[str, Any]] = envelope["requirements"]
    chars = envelope.get("execution_characteristics", {})

    units: list[dict[str, Any]] = []
    blockers: list[dict[str, str]] = []
    req_to_unit: dict[str, str] = {}
    repo_changes: list[dict[str, Any]] = []

    for req in requirements:
        cap = req["capability"]
        rid = req["id"]
        if cap in special:
            unit = _unit_for_req(req, special[cap])
            units.append(unit)
            req_to_unit[rid] = unit["id"]
        elif cap == "product_repository" and req.get("target_state") == "new":
            unit = _unit_for_req(req, generic["new_product_repository"])
            units.append(unit)
            req_to_unit[rid] = unit["id"]
        elif cap == "repository_change":
            repo_changes.append(req)
        else:
            blockers.append(
                {
                    "code": "CAPABILITY_OWNER_UNKNOWN",
                    "requirement_id": rid,
                    "detail": f"no demonstrated owner route for capability {cap}",
                }
            )

    if repo_changes:
        repos = sorted({req["target_repo"] for req in repo_changes})
        campaign = bool(chars.get("cross_repository")) or len(repos) > 1
        spec = generic["existing_system_campaign" if campaign else "bounded_existing_repo"]
        unit_id = "unit-existing-system-campaign" if campaign else "unit-existing-repo-change"
        unit = {
            "id": unit_id,
            "topology": spec["topology"],
            "owner": spec["owner"],
            "adapter": spec["adapter"],
            "requirement_ids": [r["id"] for r in repo_changes],
            "target_repos": repos,
            "depends_on_units": [],
            "admission_status": "UNCHECKED",
        }
        units.append(unit)
        for req in repo_changes:
            req_to_unit[req["id"]] = unit_id

    req_by_id = {req["id"]: req for req in requirements}
    for unit in units:
        deps: set[str] = set()
        for rid in unit["requirement_ids"]:
            for dep_rid in req_by_id[rid].get("dependencies", []):
                dep_unit = req_to_unit.get(dep_rid)
                if dep_unit and dep_unit != unit["id"]:
                    deps.add(dep_unit)
        unit["depends_on_units"] = sorted(deps)

    graph = {
        "schema": "l9.idea-execution-graph/v1",
        "source_envelope_digest": semantic_digest(envelope),
        "status": "BLOCKED" if blockers else "READY",
        "units": sorted(units, key=lambda x: x["id"]),
        "blockers": blockers,
    }
    return graph


def main() -> int:
    if len(sys.argv) not in (2, 3):
        print(
            "usage: route_execution.py <envelope.yaml|json> [capability-registry.yaml]",
            file=sys.stderr,
        )
        return 2
    try:
        envelope = validate_envelope(load_data(sys.argv[1]))
        registry_path = Path(sys.argv[2]) if len(sys.argv) == 3 else REGISTRY_PATH
        registry = load_data(registry_path)
        if not isinstance(registry, dict):
            raise ContractError("capability registry must be a mapping")
        print(dump_yaml(route_envelope(envelope, registry)), end="")
    except ContractError as exc:
        print(f"ROUTE_EXECUTION: FAIL\n- {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

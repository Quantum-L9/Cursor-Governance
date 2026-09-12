#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from _common import ContractError, assert_acyclic, load_data, nonempty_string, semantic_digest
from validate_envelope import validate_envelope

SCHEMA = "l9.idea-execution-graph/v1"
TOPOLOGIES = {
    "NEW_PRODUCT_REPOSITORY",
    "SPECIALIZED_FACTORY",
    "EXISTING_REPO_CHANGE",
    "EXISTING_SYSTEM_CAMPAIGN",
}
ADMISSION = {"UNCHECKED", "COMPATIBLE", "BLOCKED"}


def validate_graph(data: Any, envelope: Any | None = None) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ContractError("graph must be a mapping")
    errors: list[str] = []
    if data.get("schema") != SCHEMA:
        errors.append(f"schema must equal {SCHEMA}")
    if not nonempty_string(data.get("source_envelope_digest")):
        errors.append("source_envelope_digest must be a non-empty string")
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

    blocker_req_ids: set[str] = set()
    for idx, blocker in enumerate(blockers):
        if not isinstance(blocker, dict) or not nonempty_string(blocker.get("code")):
            errors.append("each blocker must be a mapping with non-empty code")
            continue
        rid = blocker.get("requirement_id")
        if rid is not None:
            if not nonempty_string(rid):
                errors.append(f"blockers[{idx}].requirement_id must be a non-empty string")
            elif rid in blocker_req_ids:
                errors.append(
                    f"requirement {rid} appears in multiple "
                    "requirement-scoped blockers"
                )
            else:
                blocker_req_ids.add(rid)

    if req_ids & blocker_req_ids:
        errors.append(
            "requirements cannot be represented by both execution units and "
            "requirement-scoped blockers: "
            f"{sorted(req_ids & blocker_req_ids)}"
        )

    if not errors and ids:
        try:
            assert_acyclic(ids, edges, "execution graph")
        except ContractError as exc:
            errors.append(str(exc))

    if errors:
        raise ContractError("; ".join(errors))

    if envelope is not None:
        validated_envelope = validate_envelope(envelope)
        expected_digest = semantic_digest(validated_envelope)
        observed_digest = data.get("source_envelope_digest")
        if observed_digest != expected_digest:
            raise ContractError(
                "DERIVED_ARTIFACT_STALE: graph source_envelope_digest does not match "
                f"current envelope digest (observed={observed_digest}, expected={expected_digest})"
            )

        expected_req_ids = {req["id"] for req in validated_envelope["requirements"]}
        covered_req_ids = req_ids | blocker_req_ids
        missing = sorted(expected_req_ids - covered_req_ids)
        unexpected = sorted(covered_req_ids - expected_req_ids)
        if missing or unexpected:
            raise ContractError(
                "GRAPH_REQUIREMENT_COVERAGE_MISMATCH: graph must cover every envelope requirement "
                "exactly once via an execution unit or requirement-scoped blocker "
                f"(missing={missing}, unexpected={unexpected})"
            )
    return data


def _resolve_envelope_path(graph_path: Path, explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    for name in (
        "IDEA_EXECUTION_ENVELOPE.yaml",
        "IDEA_EXECUTION_ENVELOPE.yml",
        "IDEA_EXECUTION_ENVELOPE.json",
    ):
        candidate = graph_path.with_name(name)
        if candidate.is_file():
            return candidate
    raise ContractError(
        "full graph validation requires the current Idea Execution Envelope; "
        "pass it as the second argument or place IDEA_EXECUTION_ENVELOPE.yaml beside the graph"
    )


def main() -> int:
    if len(sys.argv) not in (2, 3):
        print(
            "usage: validate_graph.py <EXECUTION_GRAPH.yaml|json> "
            "[IDEA_EXECUTION_ENVELOPE.yaml|json]",
            file=sys.stderr,
        )
        return 2
    try:
        graph_path = Path(sys.argv[1])
        envelope_path = _resolve_envelope_path(
            graph_path,
            sys.argv[2] if len(sys.argv) == 3 else None,
        )
        validate_graph(load_data(graph_path), load_data(envelope_path))
    except ContractError as exc:
        print(f"IDEA_EXECUTION_GRAPH: FAIL\n- {exc}", file=sys.stderr)
        return 1
    print("IDEA_EXECUTION_GRAPH: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

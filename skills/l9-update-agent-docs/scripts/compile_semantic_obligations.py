#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

PACK = Path(__file__).resolve().parents[1]
OBLIGATION_SCHEMA = PACK / "contracts" / "semantic-obligations.schema.json"
SCHEMA_ID = "l9.repo-docs.semantic-obligations.v1"


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def schema_errors(data: dict[str, Any], schema_path: Path) -> list[str]:
    schema = load_json(schema_path)
    validator = Draft202012Validator(schema)
    return [f"{'.'.join(map(str, e.path)) or '$'}: {e.message}" for e in validator.iter_errors(data)]


def validate_harvest(harvest: dict[str, Any], schema_path: Path) -> list[str]:
    if not schema_path.is_file():
        return [f"harvest schema unavailable: {schema_path}"]
    return schema_errors(harvest, schema_path)


def action_for(concept: dict[str, Any]) -> str:
    disposition = concept.get("disposition")
    comparison = (concept.get("beneficiary_fit") or {}).get("comparison")
    if disposition == "PORT":
        return "ADD_OR_REFRESH"
    if disposition == "PORT_WITH_HARDENING":
        return "HARDEN"
    if disposition == "MERGE_WITH_EXISTING":
        return "PRESERVE" if comparison == "BENEFICIARY_STRONGER" else "RECONCILE"
    if disposition == "CONFIGURE":
        return "HANDOFF"
    return "IGNORE"


def compile_obligations(
    harvest: dict[str, Any],
    required_surfaces: list[str],
    destinations: dict[str, str],
    harvest_schema: Path,
) -> dict[str, Any]:
    required = sorted(set(required_surfaces))
    errors = validate_harvest(harvest, harvest_schema)
    if errors:
        return {"schema": SCHEMA_ID, "status": "FAIL", "required_surfaces": required, "obligations": [], "resolved_surfaces": [], "unresolved_surfaces": required, "blockers": errors}
    if harvest.get("status") in {"BLOCKED", "FAIL"}:
        return {"schema": SCHEMA_ID, "status": "BLOCKED", "required_surfaces": required, "obligations": [], "resolved_surfaces": [], "unresolved_surfaces": required, "blockers": [f"harvest status is {harvest.get('status')}"]}

    evidence = {e.get("id"): e for e in harvest.get("evidence", []) if isinstance(e, dict)}
    reverse = {destinations[s]: s for s in required if s in destinations}
    obligations: list[dict[str, Any]] = []
    resolved: set[str] = set()
    for concept in harvest.get("concepts", []):
        if not isinstance(concept, dict) or not concept.get("nugget"):
            continue
        surface = reverse.get(concept.get("beneficiary_destination"))
        if not surface:
            continue
        action = action_for(concept)
        if action == "IGNORE":
            continue
        confirmed = []
        for evidence_id in concept.get("evidence_ids", []):
            item = evidence.get(evidence_id)
            locator = (item or {}).get("locator") or {}
            if not item or item.get("epistemic") != "CONFIRMED":
                continue
            if locator.get("kind") == "unknown" or not str(locator.get("value") or "").strip():
                continue
            confirmed.append({"id": evidence_id, "source": item.get("source"), "locator": locator, "claim": item.get("claim")})
        if not confirmed:
            continue
        if action not in {"PRESERVE", "HANDOFF"} and not concept.get("semantic_contract"):
            continue
        obligations.append({
            "surface": surface,
            "concept_id": concept["id"],
            "name": concept.get("name", ""),
            "action": action,
            "disposition": concept["disposition"],
            "semantic_contract": concept.get("semantic_contract"),
            "problem": concept.get("problem", ""),
            "risks": concept.get("risks", []),
            "acceptance_tests": concept.get("acceptance_tests", []),
            "beneficiary_fit": concept.get("beneficiary_fit"),
            "evidence": confirmed,
            "rank_score": concept.get("rank_score"),
        })
        resolved.add(surface)
    unresolved = sorted(set(required) - resolved)
    result = {"schema": SCHEMA_ID, "status": "PASS" if not unresolved else "PARTIAL", "required_surfaces": required, "obligations": sorted(obligations, key=lambda x: (x["surface"], x["concept_id"])), "resolved_surfaces": sorted(resolved), "unresolved_surfaces": unresolved, "blockers": []}
    output_errors = schema_errors(result, OBLIGATION_SCHEMA)
    if output_errors:
        result["status"] = "FAIL"
        result["blockers"] = output_errors
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--harvest", required=True)
    parser.add_argument("--harvest-schema", required=True)
    parser.add_argument("--surface", action="append", default=[])
    parser.add_argument("--destination", action="append", default=[])
    args = parser.parse_args()
    destinations = dict(item.split("=", 1) for item in args.destination)
    result = compile_obligations(load_json(Path(args.harvest)), args.surface, destinations, Path(args.harvest_schema))
    print(json.dumps(result, indent=2, sort_keys=True))
    return {"PASS": 0, "PARTIAL": 3, "BLOCKED": 2, "FAIL": 1}[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())

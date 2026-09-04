#!/usr/bin/env python3
"""Normalize canonical Harvest IR into evidence for DocumentationObligation objects."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def schema_errors(data: dict[str, Any], schema_path: Path) -> list[str]:
    schema = load_json(schema_path)
    validator = Draft202012Validator(schema)
    return [
        f"{'.'.join(map(str, error.path)) or '$'}: {error.message}"
        for error in sorted(validator.iter_errors(data), key=lambda item: list(item.path))
    ]


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


def compile_harvest_evidence(
    harvest: dict[str, Any],
    required_surfaces: list[str],
    destinations: dict[str, str],
    harvest_schema: Path,
    *,
    accepted_dispositions: list[str],
) -> dict[str, Any]:
    required = sorted(set(required_surfaces))
    errors = (
        schema_errors(harvest, harvest_schema)
        if harvest_schema.is_file()
        else [f"harvest schema unavailable: {harvest_schema}"]
    )
    request = harvest.get("request") if isinstance(harvest.get("request"), dict) else None
    if errors:
        return {
            "status": "FAIL",
            "request": request,
            "required_surfaces": required,
            "concepts_by_surface": {},
            "resolved_surfaces": [],
            "unresolved_surfaces": required,
            "blockers": errors,
        }
    if harvest.get("status") in {"BLOCKED", "FAIL"}:
        return {
            "status": "BLOCKED",
            "request": request,
            "required_surfaces": required,
            "concepts_by_surface": {},
            "resolved_surfaces": [],
            "unresolved_surfaces": required,
            "blockers": [f"harvest status is {harvest.get('status')}"],
        }

    evidence = {e.get("id"): e for e in harvest.get("evidence", []) if isinstance(e, dict)}
    reverse = {destinations[s]: s for s in required if s in destinations}
    concepts_by_surface: dict[str, list[dict[str, Any]]] = {}
    resolved: set[str] = set()
    for concept in harvest.get("concepts", []):
        if not isinstance(concept, dict) or not concept.get("nugget"):
            continue
        disposition = concept.get("disposition")
        if disposition not in accepted_dispositions:
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
            confirmed.append(
                {
                    "id": evidence_id,
                    "source": item.get("source"),
                    "locator": locator,
                    "claim": item.get("claim"),
                }
            )
        if not confirmed:
            continue
        if action not in {"PRESERVE", "HANDOFF"} and not concept.get("semantic_contract"):
            continue
        concepts_by_surface.setdefault(surface, []).append(
            {
                "concept_id": concept["id"],
                "name": concept.get("name", ""),
                "action": action,
                "disposition": disposition,
                "semantic_contract": concept.get("semantic_contract"),
                "problem": concept.get("problem", ""),
                "risks": concept.get("risks", []),
                "acceptance_tests": concept.get("acceptance_tests", []),
                "beneficiary_fit": concept.get("beneficiary_fit"),
                "evidence": confirmed,
                "rank_score": concept.get("rank_score"),
            }
        )
        resolved.add(surface)
    for surface in concepts_by_surface:
        concepts_by_surface[surface].sort(key=lambda row: (row["concept_id"], row["action"]))
    unresolved = sorted(set(required) - resolved)
    return {
        "status": "PASS" if not unresolved else "PARTIAL",
        "request": request,
        "required_surfaces": required,
        "concepts_by_surface": concepts_by_surface,
        "resolved_surfaces": sorted(resolved),
        "unresolved_surfaces": unresolved,
        "blockers": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--harvest", required=True)
    parser.add_argument("--harvest-schema", required=True)
    parser.add_argument("--surface", action="append", default=[])
    parser.add_argument("--destination", action="append", default=[])
    parser.add_argument("--accepted-disposition", action="append", default=[])
    args = parser.parse_args()
    destinations = dict(item.split("=", 1) for item in args.destination)
    result = compile_harvest_evidence(
        load_json(Path(args.harvest)),
        args.surface,
        destinations,
        Path(args.harvest_schema),
        accepted_dispositions=args.accepted_disposition,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return {"PASS": 0, "PARTIAL": 3, "BLOCKED": 2, "FAIL": 1}[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())

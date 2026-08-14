#!/usr/bin/env python3
"""Validate a Replan Revision against program-execution.replan.v1."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "shared/schemas/replan-revision.schema.json"
CONTRACT_PATH = ROOT / "shared/REPLAN_CONTRACT.yaml"

FORBIDDEN = {
    "objective",
    "architecture",
    "public_contract",
    "ownership",
    "target_set",
    "authorization_ceiling",
    "accepted_risk",
    "mandatory_convergence_gates",
    "historical_evidence",
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest_object(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def load_revision(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("revision must be a JSON object")
    return data


def schema_errors(revision: dict[str, Any]) -> list[str]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(revision), key=lambda e: list(e.path))
    return [f"{'.'.join(str(p) for p in e.path) or '<root>'}: {e.message}" for e in errors]


def containment_errors(revision: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    delta = revision.get("delta") or {}
    classes = list(delta.get("classes") or [])
    forbidden_hit = [c for c in classes if c in FORBIDDEN]
    containment = revision.get("authority_containment") or {}
    if forbidden_hit:
        errors.append(f"forbidden delta classes present: {forbidden_hit}")
    if containment.get("widens_lock") is True:
        errors.append("authority_containment.widens_lock must be false")
    if containment.get("result") != "PASS":
        errors.append("authority_containment.result must be PASS")
    declared = list(containment.get("forbidden_classes_present") or [])
    if declared:
        errors.append(f"authority_containment reports forbidden classes: {declared}")
    if revision.get("proposer_actor") and revision.get("verifier_actor"):
        if revision["proposer_actor"] == revision["verifier_actor"]:
            errors.append("proposer_actor must not equal verifier_actor")
    payload = {k: v for k, v in revision.items() if k != "revision_digest"}
    expected = digest_object(payload)
    if revision.get("revision_digest") != expected:
        errors.append("revision_digest does not match canonical payload")
    if revision.get("previous_plan_revision") == revision.get("proposed_plan_revision"):
        errors.append("proposed_plan_revision must advance previous_plan_revision")
    return errors


def validate_revision(revision: dict[str, Any]) -> list[str]:
    return schema_errors(revision) + containment_errors(revision)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate program-execution.replan.v1 revision")
    parser.add_argument("revision", type=Path)
    args = parser.parse_args()
    if not CONTRACT_PATH.is_file() or not SCHEMA_PATH.is_file():
        print("FAIL")
        print("- missing replan contract or schema")
        return 1
    try:
        revision = load_revision(args.revision)
    except Exception as exc:  # noqa: BLE001 — CLI surface
        print("FAIL")
        print(f"- parse: {exc}")
        return 1
    errors = validate_revision(revision)
    if errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("PASS")
    print(f"revision_id={revision['revision_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

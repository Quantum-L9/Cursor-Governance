#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REQUIRED = {"objective", "task_kind", "claims", "options", "selected_option", "selection_rationale", "action", "stop_condition"}
TASKS = {"plan", "review", "architecture", "debug", "decision", "corpus"}
ACTIONS = {"proceed", "proceed_with_validation", "bounded_probe", "block"}
GRADES = {"direct", "corroborated", "inferred", "unknown"}


def validate(data: dict) -> list[str]:
    errors = []
    missing = sorted(REQUIRED - set(data))
    if missing:
        errors.append(f"missing fields: {missing}")
    if data.get("task_kind") not in TASKS:
        errors.append("invalid task_kind")
    if data.get("action") not in ACTIONS:
        errors.append("invalid action")
    if not isinstance(data.get("claims"), list):
        errors.append("claims must be a list")
    else:
        for index, claim in enumerate(data["claims"]):
            if not isinstance(claim, dict):
                errors.append(f"claim {index} must be an object")
                continue
            if claim.get("evidence_grade") not in GRADES:
                errors.append(f"claim {index} has invalid evidence_grade")
            if claim.get("evidence_grade") == "unknown" and not claim.get("uncertainty_type"):
                errors.append(f"claim {index} unknown evidence requires uncertainty_type")
    if data.get("action") == "proceed" and any(c.get("decision_effect") == "blocks" for c in data.get("claims", []) if isinstance(c, dict)):
        errors.append("cannot proceed with a blocking claim")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("ledger")
    args = parser.parse_args()
    data = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
    errors = validate(data)
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: ledger valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

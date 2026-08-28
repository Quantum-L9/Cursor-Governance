#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REQUIRED = {
    "objective",
    "task_kind",
    "claims",
    "options",
    "selected_option",
    "selection_rationale",
    "action",
    "stop_condition",
}
TASKS = {"plan", "review", "architecture", "debug", "decision", "corpus"}
ACTIONS = {"proceed", "proceed_with_validation", "bounded_probe", "block"}
GRADES = {"direct", "corroborated", "inferred", "unknown"}
QUALITIES = {"high", "medium", "low", "unknown"}
RISKS = {"reversible", "guarded", "irreversible"}
CALIBRATION = {"none", "uncalibrated", "calibrated"}
ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "references" / "confidence-policy.yaml"


def load_allow_set() -> dict[str, dict[str, list[str]]]:
    try:
        import yaml
    except ImportError:
        return {}
    if not POLICY_PATH.is_file():
        return {}
    data = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8")) or {}
    raw = data.get("allow_set") or {}
    if not isinstance(raw, dict):
        return {}
    return raw


def validate(data: dict) -> list[str]:
    errors = []
    if not isinstance(data, dict):
        return ["ledger must be an object"]
    envelope = str(data.get("envelope") or "")
    if "Confidence: 85%" in envelope or "Confidence: {score}%" in envelope:
        errors.append("uncalibrated percent envelope is forbidden")
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
    if data.get("action") == "proceed" and any(
        c.get("decision_effect") == "blocks" for c in data.get("claims", []) if isinstance(c, dict)
    ):
        errors.append("cannot proceed with a blocking claim")

    quality = data.get("evidence_quality")
    risk = data.get("decision_risk")
    if quality is not None and quality not in QUALITIES:
        errors.append("invalid evidence_quality")
    if risk is not None and risk not in RISKS:
        errors.append("invalid decision_risk")
    if quality in QUALITIES and risk in RISKS:
        allow = load_allow_set()
        allowed = (allow.get(quality) or {}).get(risk)
        if allowed is not None and data.get("action") not in set(allowed):
            errors.append(
                f"action {data.get('action')!r} not in allow_set[{quality}][{risk}]={allowed}"
            )

    status = data.get("calibration_status", "none")
    if status is None:
        status = "none"
    if status not in CALIBRATION:
        errors.append("invalid calibration_status")
    stated = data.get("stated_probability", None)
    if stated is not None and status != "calibrated":
        errors.append("stated_probability requires calibration_status=calibrated")
    if status == "calibrated":
        for key in ("window", "n", "ece"):
            if data.get(key) in (None, ""):
                errors.append(f"calibrated status requires {key}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("ledger")
    args = parser.parse_args()
    raw = Path(args.ledger).read_text(encoding="utf-8")
    data = json.loads(raw)
    errors = validate(data)
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: ledger valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Compare compatible *declared* Strategic Value assessments; never predict outcomes."""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path


def _load_sibling(stem: str):
    import importlib.util

    name = f"l9_strategic_plan_scripts.{stem}"
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    path = Path(__file__).resolve().parent / f"{stem}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(stem)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_assessment = _load_sibling("check_sv_assessment")
ClaimBlocked = _assessment.ClaimBlocked
check = _assessment.check

CONTEXT_FIELDS = (
    "objective_ref",
    "focal_beneficiary_ref",
    "utility_unit",
    "baseline_ref",
    "horizon_ref",
)


def compare(candidates: list[dict]) -> dict:
    if not isinstance(candidates, list) or len(candidates) < 2:
        raise ClaimBlocked("TWO_OR_MORE_ALTERNATIVES_REQUIRED")
    ids = set()
    eligible = []
    excluded = []
    unresolved = []
    context = None
    for c in candidates:
        if (
            not isinstance(c, dict)
            or not isinstance(c.get("action_ref"), str)
            or (not c["action_ref"].strip())
        ):
            raise ClaimBlocked("ACTION_REF_REQUIRED")
        action_id = c["action_ref"]
        if action_id in ids:
            raise ClaimBlocked("DUPLICATE_ACTION_REF")
        ids.add(action_id)
        comparable = tuple(c.get(f) for f in CONTEXT_FIELDS)
        if context is None:
            context = comparable
        elif comparable != context:
            raise ClaimBlocked("INCOMPATIBLE_OBJECTIVE_BENEFICIARY_BASELINE_UNITS_OR_HORIZON")
        if any(not isinstance(v, str) or not v.strip() for v in comparable):
            raise ClaimBlocked("COMPARISON_CONTEXT_UNKNOWN")
        try:
            result = check(c)
            if result["status"] == "INFEASIBLE_EXCLUDED":
                excluded.append(action_id)
            elif result["status"] == "DECLARED_INPUT_CONSISTENT_NOT_NUMERICALLY_ATTESTED":
                eligible.append((action_id, Decimal(result["calculated_sv"])))
            else:
                unresolved.append({"action_ref": action_id, "reason": result["status"]})
        except ClaimBlocked as exc:
            unresolved.append({"action_ref": action_id, "reason": str(exc)})
    ranked = sorted(eligible, key=lambda p: (-p[1], p[0]))
    frontier = []
    if ranked and (not unresolved):
        frontier = [aid for aid, value in ranked if value == ranked[0][1]]
    return {
        "status": "DECLARED_VALUES_ONLY_NOT_NUMERICALLY_ATTESTED"
        if not unresolved
        else "PARTIAL_UNRESOLVED_NO_WINNER",
        "eligible_ranked_actions": [
            {"action_ref": aid, "declared_sv": str(v)} for aid, v in ranked
        ],
        "excluded_infeasible_actions": excluded,
        "unresolved_actions": unresolved,
        "frontier_if_all_resolved": frontier,
        "unique_preferred_if_all_resolved": frontier[0] if len(frontier) == 1 else None,
        "comparison_context": dict(zip(CONTEXT_FIELDS, context)),
        "authority_effect": "none",
        "method_assurance": (
            "local declared arithmetic only; external numerical model/evidence unverified"
        ),
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", type=Path, help="JSON array of separately declared candidate claims")
    a = p.parse_args(argv)
    try:
        result = compare(json.loads(a.input.read_text()))
        print(json.dumps(result, indent=2))
        return 0 if not result["unresolved_actions"] else 2
    except (OSError, ValueError, ClaimBlocked) as exc:
        print(json.dumps({"status": "COMPARISON_BLOCKED", "reason": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main())

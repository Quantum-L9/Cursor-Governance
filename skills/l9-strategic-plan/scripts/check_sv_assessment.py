#!/usr/bin/env python3
"""Conservative Strategic Value consumer consistency checks, not a valuation solver.

Accepts a declared five-bucket causal ledger and optional material-claim evidence
flags. It does not authenticate external evidence, predict future utility, verify
model calibration, or claim Strategic Authority. Known blocker -> fail closed.
"""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

BUCKETS = ("IEV", "SFV", "DC", "ERL", "OC")
COSTS = {"DC", "ERL", "OC"}
CLAIM = "objective_relative_quantitative_strategic_value"


class ClaimBlocked(ValueError):
    pass


def require(ok, why):
    if not ok:
        raise ClaimBlocked(why)


def d(value, what):
    require(
        isinstance(value, (str, int)) and (not isinstance(value, bool)),
        f"{what}: MISSING_NUMERIC_VALUE",
    )
    try:
        n = Decimal(str(value))
    except InvalidOperation as e:
        raise ClaimBlocked(f"{what}: INVALID_NUMERIC_VALUE") from e
    require(n.is_finite(), f"{what}: NONFINITE_NUMERIC_VALUE")
    return n


def string_ref(v):
    return isinstance(v, str) and bool(v.strip())


def nonempty_refs(v):
    return isinstance(v, list) and bool(v) and all(string_ref(x) for x in v)


def check(data):
    require(
        isinstance(data, dict) and data.get("schema") == "l9.strategic-planner-value-claim/v1",
        "WRONG_CLAIM_SCHEMA",
    )
    if data.get("claim_type") != CLAIM:
        return {
            "status": "NOT_APPLICABLE",
            "reason": "NO_APPLICABLE_STRATEGIC_VALUE_CLAIM",
            "authority_effect": "none",
        }
    for key in (
        "objective_ref",
        "utility_unit",
        "baseline_ref",
        "horizon_ref",
        "model_revision_ref",
        "evidence_snapshot_ref",
        "focal_beneficiary_ref",
        "counterfactual_identification_ref",
    ):
        require(string_ref(data.get(key)), f"{key}: REQUIRED_FOR_SV_CLAIM")
    require(
        data.get("feasibility") in ("admissible", "blocked", "unknown"),
        "FORMAL_FEASIBILITY_REQUIRED",
    )
    if data["feasibility"] == "blocked":
        require(
            nonempty_refs(data.get("feasibility_evidence_refs")), "FORMAL_BLOCKED_EVIDENCE_REQUIRED"
        )
        return {"status": "INFEASIBLE_EXCLUDED", "authority_effect": "none"}
    require(
        data["feasibility"] == "admissible"
        and nonempty_refs(data.get("feasibility_evidence_refs")),
        "UNKNOWN_OR_UNPROVEN_FEASIBILITY",
    )
    effects = data.get("effects")
    require(isinstance(effects, list) and effects, "MATERIAL_EFFECT_LEDGER_REQUIRED")
    seen = set()
    values = dict.fromkeys(BUCKETS, Decimal("0"))
    for effect in effects:
        require(isinstance(effect, dict), "EFFECT_RECORD_INVALID")
        eid = effect.get("effect_id")
        home = effect.get("accounting_home")
        cls = effect.get("economic_class")
        require(string_ref(eid) and eid not in seen, "DUPLICATE_OR_MISSING_EFFECT_IDENTITY")
        seen.add(eid)
        require(home in BUCKETS and cls in BUCKETS, f"{eid}: EFFECT_BUCKET_INVALID")
        require(
            nonempty_refs(effect.get("evidence_refs")) and string_ref(effect.get("period_ref")),
            f"{eid}: EFFECT_PROVENANCE_OR_PERIOD_MISSING",
        )
        n = d(effect.get("amount"), f"{eid}.amount")
        if home in COSTS:
            require(cls == home and n >= 0, f"{eid}: SEPARATE_COST_REQUIRES_POSITIVE_MAGNITUDE")
        elif cls in COSTS:
            require(
                n <= 0 and effect.get("embedded") is True,
                f"{eid}: EMBEDDED_COST_MUST_BE_NEGATIVE_AND_RECONCILED",
            )
            require(
                string_ref(effect.get("net_flow_coverage_ref")),
                f"{eid}: EMBEDDED_COST_COVERAGE_MISSING",
            )
        else:
            require(
                cls == home and (not effect.get("embedded", False)),
                f"{eid}: AMBIGUOUS_ACCOUNTING_HOME",
            )
        values[home] += n
    summary = data.get("declared_components")
    require(
        isinstance(summary, dict) and set(summary) == set(BUCKETS),
        "EXACT_FIVE_BUCKET_DECLARATION_REQUIRED",
    )
    for bucket in BUCKETS:
        require(
            d(summary[bucket], bucket) == values[bucket], f"{bucket}: COMPONENT_LEDGER_MISMATCH"
        )
    final = values["IEV"] + values["SFV"] - values["DC"] - values["ERL"] - values["OC"]
    require(d(data.get("declared_sv"), "declared_sv") == final, "FIVE_TERM_FORMULA_MISMATCH")
    method = data.get("method")
    require(
        isinstance(method, dict)
        and string_ref(method.get("method_ref"))
        and (method.get("owner") == "Numerical Reasoning"),
        "NUMERICAL_METHOD_OWNER_OR_ID_MISSING",
    )
    require(
        method.get("kind")
        in (
            "declared_aggregate",
            "bounded_scenarios",
            "robust_optimization",
            "qv_lookahead",
            "other_owner_admitted",
        ),
        "UNSUPPORTED_METHOD_KIND",
    )
    if method["kind"] == "qv_lookahead":
        require(
            nonempty_refs(method.get("belief_state_refs"))
            and string_ref(method.get("bounded_policy_ref")),
            "QV_ONLY_METHOD_COORDINATES_MISSING",
        )
    if method["kind"] == "bounded_scenarios" and method.get("probabilistic") is True:
        require(
            nonempty_refs(method.get("probability_model_refs")),
            "SCENARIO_PROBABILITY_MODEL_MISSING",
        )
    if data.get("responsive_actors_material") is True:
        require(
            string_ref(data.get("actor_response_coverage_ref")), "UNMODELED_MATERIAL_ACTOR_RESPONSE"
        )
    if data.get("cross_actor_utility_material") is True:
        require(string_ref(data.get("welfare_aggregation_ref")), "UNAUTHORIZED_CROSS_ACTOR_UTILITY")
    if data.get("sequential_policy_material") is True:
        require(
            string_ref(data.get("nonanticipativity_evidence_ref")), "FUTURE_INFORMATION_LEAKAGE"
        )
    if data.get("joint_portfolio_material") is True:
        require(
            string_ref(data.get("joint_interaction_model_ref")), "UNJUSTIFIED_PORTFOLIO_ADDITIVITY"
        )
    if data.get("preference_reversal_material") is True:
        require(string_ref(data.get("sensitivity_evidence_ref")), "UNSUPPORTED_PRECISE_WINNER")
    if data.get("claim_strength") == "independently_verified":
        require(
            nonempty_refs(data.get("numerical_owner_execution_refs"))
            and nonempty_refs(data.get("independent_model_validation_refs")),
            "VERIFIED_METHOD_CLAIM_WITHOUT_REVIEWABLE_EVIDENCE",
        )
    require(
        data.get("claim_strength") in ("declared", "independently_verified"),
        "CLAIM_STRENGTH_MUST_BE_DECLARED",
    )
    # Presence of refs cannot authenticate their provenance: never report an
    # independently verified numeric result from this consumer-side checker.
    return {
        "status": "DECLARED_INPUT_CONSISTENT_NOT_NUMERICALLY_ATTESTED",
        "components": {k: str(v) for k, v in values.items()},
        "calculated_sv": str(final),
        "effect_count": len(seen),
        "requires_owner_evidence_validation": True,
        "authority_effect": "none",
        "note": (
            "Arithmetic and declared causal partition only; "
            "source/model evidence not independently verified"
        ),
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", type=Path)
    a = p.parse_args(argv)
    try:
        result = check(json.loads(a.input.read_text(encoding="utf-8")))
        print(json.dumps(result, indent=2))
        return 0
    except (ClaimBlocked, ValueError, OSError) as e:
        print(json.dumps({"status": "CLAIM_BLOCKED", "reason": str(e)}, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
import sys

from _common import dump, load_json

VIABLE = {"PORT", "PORT_WITH_HARDENING", "CONFIGURE", "MERGE_WITH_EXISTING"}
BENEFICIARY_STRONGER_ALLOWED = {"MERGE_WITH_EXISTING", "KEEP_LOCAL", "REJECT", "UNKNOWN"}


def portability_closed(c):
    p = c.get("portability") or {}
    required_flags = (
        "donor_identity_independent",
        "donor_execution_authority_independent",
        "donor_infrastructure_independent",
        "incidental_implementation_independent",
    )
    if not all(p.get(flag) is True for flag in required_flags):
        return False
    if p.get("donor_runtime_required"):
        dep = p.get("external_dependency") or {}
        return all(bool(dep.get(key)) for key in ("target", "probe", "failure_behavior"))
    return p.get("external_dependency") in (None, {})


def beneficiary_fit_closed(c):
    fit = c.get("beneficiary_fit") or {}
    comparison = fit.get("comparison")
    if comparison not in {
        "DONOR_STRONGER",
        "BENEFICIARY_STRONGER",
        "EQUIVALENT",
        "STANDALONE",
        "UNKNOWN",
    }:
        return False
    if not fit.get("merge_decision") or not fit.get("compatibility_risk"):
        return False
    if (
        comparison == "BENEFICIARY_STRONGER"
        and c.get("disposition") not in BENEFICIARY_STRONGER_ALLOWED
    ):
        return False
    return True


def qualify(c):
    checks = {
        "stable_problem": bool(c.get("problem")),
        "semantic_contract": bool(c.get("semantic_contract")),
        "real_evidence": bool(c.get("evidence_ids")),
        "beneficiary_destination": bool(c.get("beneficiary_destination")),
        "explicit_risks": bool(c.get("risks")),
        "acceptance_test": bool(c.get("acceptance_tests")),
        "beneficiary_fit": beneficiary_fit_closed(c),
        "portability_closure": portability_closed(c),
    }
    out = dict(c)
    out["nugget"] = out.get("disposition") in VIABLE and all(checks.values())
    return out, checks


def main():
    obj = load_json(sys.argv[1])
    out = []
    checks = {}
    for concept in obj.get("concepts", []):
        concept, result = qualify(concept)
        out.append(concept)
        checks[concept["id"]] = result
    obj["concepts"] = out
    dump(obj, sys.argv[2] if len(sys.argv) > 2 else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
import sys

from _common import dump, load_json, policy, schema
from jsonschema import Draft202012Validator
from qualify_nuggets import beneficiary_fit_closed, portability_closed

VIABLE = {"PORT", "PORT_WITH_HARDENING", "CONFIGURE", "MERGE_WITH_EXISTING"}


def validate(obj):
    errs = [
        e.message for e in Draft202012Validator(schema("harvest-ir.schema.json")).iter_errors(obj)
    ]
    harvest_policy = policy("harvest-policy.yaml")
    allowed_classes = set(harvest_policy["classification"])
    evidence_rows = {e["id"]: e for e in obj.get("evidence", [])}

    for evidence in evidence_rows.values():
        if evidence.get("epistemic") in {"CONFIRMED", "INFERENCE"}:
            locator = evidence.get("locator") or {}
            if not evidence.get("claim"):
                errs.append(f"evidence {evidence.get('id')}: material claim missing")
            if locator.get("kind") == "unknown" or not locator.get("value"):
                errs.append(
                    f"evidence {evidence.get('id')}: observed/inferred claim lacks resolvable locator"
                )

    for item in obj.get("inventory", []):
        if item.get("classification") not in allowed_classes:
            errs.append(f"inventory {item.get('path')}: invalid canonicality classification")
        for evidence_id in item.get("evidence_ids", []):
            if evidence_id not in evidence_rows:
                errs.append(f"inventory {item.get('path')}: unresolved evidence {evidence_id}")

    for surface in obj.get("surfaces", []):
        for evidence_id in surface.get("evidence_ids", []):
            if evidence_id not in evidence_rows:
                errs.append(f"surface {surface.get('item')}: unresolved evidence {evidence_id}")
        if surface.get("is_wrapper") and not surface.get("resolved_target"):
            errs.append(f"surface {surface.get('item')}: wrapper has no resolved execution target")

    for concept in obj.get("concepts", []):
        for evidence_id in concept.get("evidence_ids", []):
            if evidence_id not in evidence_rows:
                errs.append(f"concept {concept.get('id')}: unresolved evidence {evidence_id}")

        fit = concept.get("beneficiary_fit") or {}
        if fit.get("comparison") == "BENEFICIARY_STRONGER" and concept.get("disposition") == "PORT":
            errs.append(
                f"concept {concept.get('id')}: donor cannot PORT over stronger beneficiary semantics"
            )

        if concept.get("nugget"):
            if concept.get("disposition") not in VIABLE:
                errs.append(
                    f"concept {concept.get('id')}: non-viable disposition cannot be a nugget"
                )
            if not concept.get("acceptance_tests"):
                errs.append(
                    f"concept {concept.get('id')}: qualified nugget missing acceptance test"
                )
            if not concept.get("semantic_contract"):
                errs.append(
                    f"concept {concept.get('id')}: qualified nugget missing semantic contract"
                )
            if not beneficiary_fit_closed(concept):
                errs.append(
                    f"concept {concept.get('id')}: qualified nugget lacks beneficiary-fit closure"
                )
            if not portability_closed(concept):
                errs.append(
                    f"concept {concept.get('id')}: qualified nugget lacks portability closure"
                )

        portability = concept.get("portability") or {}
        if portability.get("donor_runtime_required"):
            dep = portability.get("external_dependency") or {}
            missing = [key for key in ("target", "probe", "failure_behavior") if not dep.get(key)]
            if missing:
                errs.append(
                    f"concept {concept.get('id')}: retained donor runtime dependency missing {','.join(missing)}"
                )

    return errs


def main():
    obj = load_json(sys.argv[1])
    errs = validate(obj)
    status = "PASS" if not errs else "FAIL"
    receipt = {
        "request_id": obj.get("request", {}).get("request_id", "UNKNOWN"),
        "status": status,
        "checks": [
            {
                "id": "harvest_schema_evidence_portability_authority_closure",
                "status": status,
                "errors": errs,
            }
        ],
        "outputs": ["harvest.json"] if not errs else [],
        "unknowns": obj.get("unknowns", []),
    }
    if len(sys.argv) > 2:
        dump(receipt, sys.argv[2])
    dump({"status": status, "errors": errs})
    return 0 if not errs else 2


if __name__ == "__main__":
    raise SystemExit(main())

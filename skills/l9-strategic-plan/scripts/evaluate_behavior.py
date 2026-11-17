#!/usr/bin/env python3
"""Conservative receipt-based behavioral test ledger. No automatic model PASS."""

import argparse
import hashlib
import json
import pathlib
import sys


def evaluate(cases, receipts):
    seen = {}
    for r in receipts:
        k = r.get("case_id")
        if k in seen:
            raise ValueError("DUPLICATE_CASE_RECEIPT: " + str(k))
        seen[k] = r
    out = []
    ids = {c["id"] for c in cases}
    if set(seen) - ids:
        raise ValueError("UNKNOWN_CASE: " + ",".join(sorted(set(seen) - ids)))
    for c in cases:
        r = seen.get(c["id"])
        status = "NOT_RUN"
        why = "no execution receipt"
        if r:
            reviewer = r.get("reviewer_identity")
            executor = r.get("executor_identity")
            if not r.get("actual_response") or not r.get("run_context"):
                status = "INCOMPLETE"
                why = "missing response or execution context"
            elif not r.get("independent_reviewer") or not r.get("evidence_refs"):
                status = "REVIEW_REQUIRED"
                why = "no independent review with evidence"
            elif not (
                r.get("run_id")
                and r.get("skill_sha256")
                and r.get("source_snapshot_refs")
                and r.get("reviewer_verdict")
                and r.get("reviewer_evidence_refs")
                and isinstance(reviewer, str)
                and reviewer.strip()
                and isinstance(executor, str)
                and executor.strip()
                and reviewer != executor
            ):
                status = "REVIEW_REQUIRED"
                why = "missing traceable execution or separate reviewer identity"
            elif hashlib.sha256(r["actual_response"].encode("utf-8")).hexdigest() != r.get(
                "actual_response_sha256"
            ):
                status = "INCOMPLETE"
                why = "actual response digest mismatch"
            elif not isinstance(r.get("artifact_sha256_by_path"), dict):
                status = "INCOMPLETE"
                why = "missing artifact manifest (empty map allowed for text-only cases)"
            elif (
                r.get("observed_positive") is True
                and r.get("observed_forbidden") is False
                and (r.get("reviewer_verdict") == "PASS")
            ):
                status = "PASS"
                why = (
                    "receipt assertions and response digest consistent; "
                    "reviewer independence externally unverified"
                )
            elif (
                r.get("reviewer_verdict") == "FAIL"
                or r.get("observed_forbidden") is True
                or r.get("observed_positive") is False
            ):
                status = "FAIL"
                why = "recorded failure"
            else:
                status = "REVIEW_REQUIRED"
                why = "incomplete predicate assessment"
        out.append({"case_id": c["id"], "status": status, "reason": why})
    return {
        "cases": out,
        "counts": {
            s: sum(x["status"] == s for x in out)
            for s in ["PASS", "FAIL", "NOT_RUN", "INCOMPLETE", "REVIEW_REQUIRED"]
        },
        "behavioral_acceptance": "RECORDED_PASS_NOT_INDEPENDENTLY_AUTHENTICATED"
        if out and all(x["status"] == "PASS" for x in out)
        else "NOT_ESTABLISHED",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cases", required=True)
    p.add_argument("--receipts")
    p.add_argument("--out")
    a = p.parse_args()
    cases = json.loads(pathlib.Path(a.cases).read_text())
    receipts = json.loads(pathlib.Path(a.receipts).read_text()) if a.receipts else []
    result = evaluate(cases, receipts)
    data = json.dumps(result, indent=2)
    if a.out:
        pathlib.Path(a.out).write_text(data + "\n")
    print(data)
    return (
        0
        if result["behavioral_acceptance"] == "RECORDED_PASS_NOT_INDEPENDENTLY_AUTHENTICATED"
        else 2
    )


if __name__ == "__main__":
    sys.exit(main())

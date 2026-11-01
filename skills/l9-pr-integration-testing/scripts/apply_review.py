#!/usr/bin/env python3
"""Bind independent source/contract review to an already proven integration revision."""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

from integrate import verdict_for, now, sha
from validate_evidence import validate, seal_bundle

HEX = re.compile(r"^[0-9a-f]{40}$")


class ReviewError(ValueError):
    pass


def resolve_review(evidence_dir: Path, review_path: Path):
    if validate(evidence_dir):
        raise ReviewError("existing evidence failed independent integrity checks")
    review = json.loads(review_path.read_text(encoding="utf-8"))
    if review.get("schema") != "l9.integration.source-review/v1":
        raise ReviewError("source-review schema not recognized")
    root = evidence_dir
    docs = {name: json.loads((root / name).read_text(encoding="utf-8")) for name in
            ("integration_manifest.json", "integration_evidence.json", "integration_findings.json", "integration_verdict.json")}
    m = docs["integration_manifest.json"]
    evid = docs["integration_evidence.json"]
    findings = docs["integration_findings.json"]
    v = docs["integration_verdict.json"]
    if (root / "source-review.json").exists():
        raise ReviewError("review already applied; rebind and rerun instead of overwriting")
    combined = next((s for s in m.get("states", []) if s.get("name") == "combined"), None)
    if not combined or not combined.get("revision"):
        raise ReviewError("cannot review a nonexistent combined Git revision")
    integrated_sha = combined["revision"]["sha"]
    if not HEX.fullmatch(review.get("integrated_sha", "")) or review["integrated_sha"] != integrated_sha:
        raise ReviewError("source-review SHA must equal exact tested synthetic revision")
    if not review.get("reviewer") or review.get("decision") not in {"PASS", "FINDINGS", "INCOMPLETE"}:
        raise ReviewError("reviewer and explicit bounded decision required")
    known = {e["id"] for e in evid["records"]}
    changed_paths = sorted(set(x for paths in m.get("changed_files_by_pr", {}).values() for x in paths))
    reported = review.get("paths", [])
    if not isinstance(reported, list):
        raise ReviewError("paths must enumerate each changed source")
    observed = {}
    for x in reported:
        p = x.get("path")
        if p in observed or not isinstance(p, str) or x.get("disposition") not in {"PASS", "FINDING", "NOT_APPLICABLE", "UNKNOWN"}:
            raise ReviewError("duplicate/invalid changed-path disposition")
        if not x.get("source_coordinate") or not x.get("rationale"):
            raise ReviewError("changed-path dispositions need exact coordinate and rationale")
        refs = x.get("evidence_ids", [])
        if not refs or not set(refs).issubset(known):
            raise ReviewError("changed-path dispositions require existing execution/source evidence IDs")
        observed[p] = x
    if sorted(observed) != changed_paths:
        raise ReviewError("review does not account for every changed source path")
    obligations = review.get("contract_obligations", [])
    if not obligations:
        raise ReviewError("no governing contract and expected behavior were checked")
    for o in obligations:
        if not o.get("authority_source") or o.get("disposition") not in {"PASS", "FINDING", "UNKNOWN"} or not o.get("evidence_ids") or not set(o["evidence_ids"]).issubset(known):
            raise ReviewError("contract obligations require authority source, status and evidence")
    test_check = review.get("test_discrimination", [])
    verified_procedures = {p["procedure"] for p in combined.get("tests", [])}
    if not test_check or not verified_procedures.issubset({x.get("procedure") for x in test_check}):
        raise ReviewError("review must disposition every executed test procedure")
    for t in test_check:
        if not t.get("assertion_inspection") or t.get("disposition") not in {"PASS", "FINDING", "UNKNOWN"}:
            raise ReviewError("test procedure quality needs assertion inspection and disposition")
    issues = review.get("findings", [])
    for f in issues:
        if not f.get("source_coordinate") or not f.get("root_cause_state") or not f.get("corrective_obligation") or f.get("severity") not in {"CRITICAL", "HIGH", "MEDIUM", "LOW"}:
            raise ReviewError("review findings require exact location, cause and correction")
    complete = (review["decision"] == "PASS" and all(x["disposition"] in {"PASS", "NOT_APPLICABLE"} for x in reported) and
                all(x["disposition"] == "PASS" for x in obligations) and
                all(x["disposition"] == "PASS" for x in test_check) and not issues)
    review_text = json.dumps(review, sort_keys=True, indent=2) + "\n"
    rid = f"E{len(evid['records']) + 1:05d}"
    log_path = "logs/" + rid + ".txt"
    (root / log_path).write_text("Independent review receipt for candidate " + integrated_sha + "\n" + review_text)
    evid["records"].append({"id": rid, "subject": "independent source review", "kind": "SOURCE_REVIEW", "status": "PASS" if complete else "INCOMPLETE",
                            "details": {"review_sha256": sha(review_text.encode()), "integrated_sha": integrated_sha, "changed_paths_dispositioned": len(observed)},
                            "log_path": log_path, "log_sha256": sha((root / log_path).read_bytes())})
    for f in findings["findings"]:
        if f["classification"] == "UNVERIFIED" and f["reason"] in {
            "Independent exact-revision adversarial source review not yet attached", "Applicable domain obligation closure not yet reviewed"}:
            f["disposition"] = "RESOLVED" if complete else "REMAINS_OPEN"
            f["resolution_evidence_id"] = rid
    for issue in issues:
        fid = "F-" + sha((issue["source_coordinate"] + issue["corrective_obligation"]).encode())[:12]
        findings["findings"].append({"id": fid, "classification": "PR_DEFECT", "severity": issue["severity"],
                                      "reason": issue.get("reason", "Material source-review defect"),
                                      "scope": issue["source_coordinate"], "evidence_ids": [rid],
                                      "root_cause": issue["root_cause_state"], "corrective_obligation": issue["corrective_obligation"]})
    m["source_review"] = {"integrated_sha": integrated_sha, "receipt_id": rid, "state": review["decision"]}
    exec_state = v["execution"]
    exec_state["source_review_verified"] = complete
    exec_state["required_contracts_verified"] = complete
    # The basic runner is not an Odoo/PostgreSQL/Compose adapter; source review cannot turn missing services into proof.
    if any(x in m.get("adapters_detected", []) for x in ("ODOO", "DATABASE")):
        exec_state["required_contracts_verified"] = False
    open_findings = [f for f in findings["findings"] if f.get("disposition") != "RESOLVED"]
    state = verdict_for(exec_state, open_findings, m)
    v.update({"state": state, "execution": exec_state, "generated_at": now(),
              "blocking_findings": [f["id"] for f in open_findings if f["severity"] in ("CRITICAL", "HIGH")],
              "unverified": [f["reason"] for f in open_findings if f["classification"] in ("UNVERIFIED", "AUTHORITY", "ENVIRONMENT")]})
    for name, body in docs.items():
        (root / name).write_text(json.dumps(body, sort_keys=True, indent=2) + "\n")
    (root / "source-review.json").write_text(review_text)
    seal_bundle(root)
    errors = validate(root)
    if errors:
        raise ReviewError("modified evidence invalid: " + "; ".join(errors))
    return v


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--evidence-dir", type=Path, required=True)
    ap.add_argument("--review-file", type=Path, required=True)
    args = ap.parse_args()
    try:
        outcome = resolve_review(args.evidence_dir, args.review_file)
    except (ReviewError, ValueError, OSError) as exc:
        print("REVIEW_BLOCKED: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps({"state": outcome["state"], "evidence": str(args.evidence_dir)}))
    return 0 if outcome["state"] == "INTEGRATION_READY" else 1

if __name__ == "__main__":
    sys.exit(main())

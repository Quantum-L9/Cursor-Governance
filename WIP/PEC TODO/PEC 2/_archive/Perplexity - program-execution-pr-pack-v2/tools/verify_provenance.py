#!/usr/bin/env python3
"""tools/verify_provenance.py"""
from __future__ import annotations
import argparse, json, subprocess, sys

def verify(artifact, owner):
    result = subprocess.run(["gh", "attestation", "verify", artifact, "-o", owner, "--format", "json"], capture_output=True, text=True)
    if result.returncode != 0: return {"verdict": "FAIL", "reason": result.stderr.strip()}
    try: data = json.loads(result.stdout)
    except json.JSONDecodeError: return {"verdict": "FAIL", "reason": "unparseable attestation output"}
    return {"verdict": "PASS", "attestation": data}

def check_required_fields(predicate, required): return [f for f in required if f not in predicate]

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--artifact", required=True); p.add_argument("--owner", default="Quantum-L9")
    p.add_argument("--required-fields", nargs="*", default=["source_sha", "workflow_ref", "node_id", "contract_digest"])
    args = p.parse_args()
    outcome = verify(args.artifact, args.owner)
    if outcome["verdict"] == "FAIL": print(json.dumps(outcome, indent=2)); sys.exit(1)
    predicate = outcome.get("attestation", {}).get("predicate", {})
    missing = check_required_fields(predicate, args.required_fields)
    if missing:
        outcome = {"verdict": "FAIL", "reason": f"missing predicate fields: {missing}"}
        print(json.dumps(outcome, indent=2)); sys.exit(1)
    print(json.dumps(outcome, indent=2))

if __name__ == "__main__":
    main()

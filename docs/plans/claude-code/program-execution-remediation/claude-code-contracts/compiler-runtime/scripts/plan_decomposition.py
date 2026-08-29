#!/usr/bin/env python3
"""
plan_decomposition.py — claude-coding-contract-compiler v2.7.0
Deterministic sizing and chain-decomposition planner.

Given a source contract manifest (deliverables, files, commits, matrix cases),
decides whether the mandate fits one Claude Code session and, if not, emits
an ordered sub-contract chain with a stable chain_digest.

SESSION BUDGET THRESHOLDS (tunable via --config):
  max_new_files:    20   (files that can be written in one focused session)
  max_commits:       1   (one local commit per contract; decompose multi-commit work)
  max_matrix_cases: 25   (evaluator/test matrix cases per session)
  max_deliverables: 10   (discrete deliverables per session)

If ANY threshold is exceeded -> DECOMPOSE.
"""
import argparse, hashlib, json, sys
from pathlib import Path

DEFAULTS = {
    "max_new_files":    20,
    "max_commits":       1,
    "max_matrix_cases": 25,
    "max_deliverables": 10,
}

def sha256(s: str) -> str:
    return "sha256:" + hashlib.sha256(s.encode()).hexdigest()

def fits_one(m: dict, cfg: dict) -> tuple[bool, list[str]]:
    reasons = []
    if m.get("new_files", 0)      > cfg["max_new_files"]:    reasons.append(f"new_files={m['new_files']} > {cfg['max_new_files']}")
    if m.get("commits", 0)         > cfg["max_commits"]:      reasons.append(f"commits={m['commits']} > {cfg['max_commits']}")
    if m.get("matrix_cases", 0)    > cfg["max_matrix_cases"]: reasons.append(f"matrix_cases={m['matrix_cases']} > {cfg['max_matrix_cases']}")
    if m.get("deliverables", 0)    > cfg["max_deliverables"]: reasons.append(f"deliverables={m['deliverables']} > {cfg['max_deliverables']}")
    return (len(reasons) == 0, reasons)

def group_commits(commit_groups: list[list[int]], source_id: str, total: int) -> list[dict]:
    """Convert raw commit groups -> sub-contract descriptors with stable IDs."""
    base = source_id.replace("-v1.0.0", "")
    # Sub-contract IDs append the chain index directly to the source base, so a
    # source of L9-CI-CORE-PR-B yields L9-CI-CORE-PR-B1..Bn — the human PR-B1 naming,
    # and the planner (not hand-authoring) is the source of truth for the IDs.
    sub_contracts = []
    for i, commits in enumerate(commit_groups):
        sid = f"{base}{i+1}-v1.0.0"
        prev = f"{base}{i}-v1.0.0" if i > 0 else None
        nxt  = f"{base}{i+2}-v1.0.0" if i < len(commit_groups)-1 else None
        sub_contracts.append({
            "id": sid, "index": i+1, "total": total,
            "source_commits": commits,
            "prerequisite": prev,
            "next_contract": nxt,
        })
    return sub_contracts

def compute_chain_digest(sub_contracts: list[dict]) -> str:
    ids = [c["id"] for c in sub_contracts]
    return sha256(json.dumps(ids, separators=(",", ":")))

def plan(manifest: dict, commit_groups: list[list[int]], cfg: dict) -> dict:
    ok, reasons = fits_one(manifest, cfg)
    if ok:
        return {"decompose": False, "fits_one_session": True, "session_budget": manifest}

    total = len(commit_groups)
    sub_contracts = group_commits(commit_groups, manifest["contract_id"], total)
    chain_digest  = compute_chain_digest(sub_contracts)

    return {
        "decompose": True,
        "fits_one_session": False,
        "decomposition_reasons": reasons,
        "chain_digest": chain_digest,
        "sub_contracts": sub_contracts,
        "session_budget": {
            "estimated_new_files":      manifest.get("new_files", 0),
            "estimated_modified_files": manifest.get("modified_files", 0),
            "estimated_test_cases":     manifest.get("matrix_cases", 0),
            "fits_one_session":         False,
            "decomposition_reason":     "; ".join(reasons)
        }
    }

def main():
    ap = argparse.ArgumentParser(description="Deterministic sub-contract chain planner.")
    ap.add_argument("--manifest",  required=True, help="JSON file with contract sizing fields")
    ap.add_argument("--groups",    required=True, help="JSON file: list of commit groups e.g. [[1],[2,3],[4,5]]")
    ap.add_argument("--config",    default=None,  help="Optional JSON override for thresholds")
    ap.add_argument("--output",    default=None,  help="Write plan JSON to file (default: stdout)")
    args = ap.parse_args()

    cfg = dict(DEFAULTS)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text()))

    manifest     = json.loads(Path(args.manifest).read_text())
    commit_groups = json.loads(Path(args.groups).read_text())

    result = plan(manifest, commit_groups, cfg)
    out    = json.dumps(result, indent=2)

    if args.output:
        Path(args.output).write_text(out)
        print(f"Plan written to {args.output}", file=sys.stderr)
    else:
        print(out)

    sys.exit(0 if not result["decompose"] else 1)

if __name__ == "__main__":
    main()

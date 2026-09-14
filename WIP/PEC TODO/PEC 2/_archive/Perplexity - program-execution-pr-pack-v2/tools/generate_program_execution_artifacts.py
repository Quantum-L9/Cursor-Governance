#!/usr/bin/env python3
"""tools/generate_program_execution_artifacts.py"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
try: import yaml
except ImportError: print("FAIL: PyYAML required", file=sys.stderr); sys.exit(2)

def generate_codeowners(tree):
    lines = ["# GENERATED FILE — do not edit by hand.", "# Source: tools/generate_program_execution_artifacts.py", ""]
    for node in tree.get("nodes", []):
        owner = node.get("owner", "@Quantum-L9/governance")
        for pattern in node.get("file_scope", []): lines.append(f"{pattern} {owner}")
    return "\n".join(lines) + "\n"

def generate_ruleset(tree):
    required_checks = sorted({g for n in tree.get("nodes", []) for g in n.get("gates", [])})
    return {"name": "program-execution", "target": "branch", "enforcement": "active",
            "conditions": {"ref_name": {"include": ["refs/heads/main"]}},
            "rules": [{"type": "required_status_checks", "parameters": {
                "required_status_checks": [{"context": c} for c in required_checks],
                "strict_required_status_checks_policy": True}},
                {"type": "pull_request", "parameters": {"required_approving_review_count": 1}}]}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tree", required=True, type=Path)
    p.add_argument("--out-codeowners", required=True, type=Path)
    p.add_argument("--out-ruleset", required=True, type=Path)
    p.add_argument("--check", action="store_true")
    args = p.parse_args()
    tree = yaml.safe_load(args.tree.read_text())
    codeowners = generate_codeowners(tree); ruleset = json.dumps(generate_ruleset(tree), indent=2) + "\n"
    if args.check:
        drift = False
        if not args.out_codeowners.exists() or args.out_codeowners.read_text() != codeowners: print(f"FAIL: {args.out_codeowners} out of date"); drift = True
        if not args.out_ruleset.exists() or args.out_ruleset.read_text() != ruleset: print(f"FAIL: {args.out_ruleset} out of date"); drift = True
        sys.exit(1 if drift else 0)
    args.out_codeowners.parent.mkdir(parents=True, exist_ok=True); args.out_codeowners.write_text(codeowners)
    args.out_ruleset.parent.mkdir(parents=True, exist_ok=True); args.out_ruleset.write_text(ruleset)
    print("PASS: generated CODEOWNERS and ruleset from feature tree.")

if __name__ == "__main__":
    main()

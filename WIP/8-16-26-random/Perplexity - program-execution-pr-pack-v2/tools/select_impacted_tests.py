#!/usr/bin/env python3
"""tools/select_impacted_tests.py"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
try: import yaml
except ImportError: print("FAIL: PyYAML required", file=sys.stderr); sys.exit(2)

def select(impact_map, changed_files):
    entries = impact_map.get("entries", [])
    selected, covered = set(), []
    for f in changed_files:
        matched = False
        for entry in entries:
            if f.startswith(entry["module_prefix"]):
                matched = True; covered.append(entry["module_prefix"])
                selected.update(entry.get("tests", [])); selected.update(entry.get("transitive_dependents", []))
        if not matched: return {"fallback_full_suite": True, "reason": f"no impact-map entry covers {f}"}
    return {"fallback_full_suite": False, "selected_tests": sorted(selected), "covered_prefixes": sorted(set(covered))}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--impact-map", required=True, type=Path); p.add_argument("--changed-files", nargs="+", required=True)
    args = p.parse_args()
    impact_map = yaml.safe_load(args.impact_map.read_text())
    print(json.dumps(select(impact_map, args.changed_files), indent=2))

if __name__ == "__main__":
    main()

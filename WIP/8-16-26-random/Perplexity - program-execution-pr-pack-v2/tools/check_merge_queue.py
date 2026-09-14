#!/usr/bin/env python3
"""tools/check_merge_queue.py"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
try: import yaml
except ImportError: print("FAIL: PyYAML required", file=sys.stderr); sys.exit(2)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tree", required=True, type=Path)
    p.add_argument("--batch-node-ids", nargs="+", required=True)
    args = p.parse_args()
    tree = yaml.safe_load(args.tree.read_text())
    nodes = {n["id"]: n for n in tree["nodes"]}
    batch = set(args.batch_node_ids)
    problems = []
    for nid in batch:
        node = nodes.get(nid)
        if node is None: problems.append(f"unknown node in batch: {nid}"); continue
        for dep in node.get("depends_on", []):
            dep_node = nodes.get(dep)
            if (dep_node is None or dep_node.get("state") != "merged") and dep not in batch:
                problems.append(f"{nid} depends on unmerged {dep}, which is not in this batch")
    if problems:
        print(json.dumps({"verdict": "FAIL", "problems": problems}, indent=2)); sys.exit(1)
    required_gates = sorted({g for nid in batch for g in nodes[nid].get("gates", [])})
    print(json.dumps({"verdict": "PASS", "batch": sorted(batch), "required_gates": required_gates}, indent=2))

if __name__ == "__main__":
    main()

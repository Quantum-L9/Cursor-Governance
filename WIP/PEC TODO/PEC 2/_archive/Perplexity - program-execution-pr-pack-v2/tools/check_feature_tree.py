#!/usr/bin/env python3
"""tools/check_feature_tree.py — validate a canonical feature tree.
Checks: DAG validity (FT001/FT002), stack-base correctness (FT003),
bottom-up merge order (FT004), disjoint file_scope (FT005), contract
existence (FT006), PR diff-scope enforcement (FT031)."""
from __future__ import annotations
import argparse, fnmatch, json, sys
from pathlib import Path
try:
    import yaml
except ImportError:
    print("FAIL: PyYAML is required", file=sys.stderr); sys.exit(2)

class TreeError(Exception):
    def __init__(self, code, message):
        super().__init__(f"{code}: {message}"); self.code, self.message = code, message

def load_tree(path):
    if not path.exists():
        raise TreeError("FT000", f"feature tree file not found: {path}")
    data = yaml.safe_load(path.read_text())
    if data.get("schema") != "canonical.schema.feature_tree.v1":
        raise TreeError("FT000", "schema field missing or mismatched")
    return data

def index_nodes(tree):
    nodes = {}
    for n in tree.get("nodes", []):
        if n["id"] in nodes:
            raise TreeError("FT002", f"duplicate node id: {n['id']}")
        nodes[n["id"]] = n
    return nodes

def check_dag(nodes):
    visiting, visited = set(), set()
    def dfs(node_id, stack):
        if node_id in visited: return
        if node_id in visiting:
            raise TreeError("FT001", f"cycle detected: {' -> '.join(stack + [node_id])}")
        node = nodes.get(node_id)
        if node is None:
            raise TreeError("FT002", f"unknown dependency id: {node_id}")
        visiting.add(node_id)
        for dep in node.get("depends_on", []): dfs(dep, stack + [node_id])
        visiting.discard(node_id); visited.add(node_id)
    for nid in nodes: dfs(nid, [])

def check_stack_base(tree, nodes):
    stack_base = tree["stack_base"]
    branch_of = {nid: n["branch"] for nid, n in nodes.items()}
    for nid, n in nodes.items():
        deps = n.get("depends_on", [])
        if not deps:
            if n["base"] != stack_base:
                raise TreeError("FT003", f"{nid}: root node base '{n['base']}' must equal stack_base '{stack_base}'")
        else:
            allowed = {branch_of[d] for d in deps} | {stack_base}
            if n["base"] not in allowed:
                raise TreeError("FT003", f"{nid}: base '{n['base']}' must be stack_base or dependency branch {sorted(allowed)}")

def check_merge_order(nodes):
    for nid, n in nodes.items():
        if n.get("state") == "merged":
            for dep in n.get("depends_on", []):
                dep_node = nodes.get(dep)
                if dep_node is None:
                    raise TreeError("FT002", f"unknown dependency id: {dep}")
                if dep_node.get("state") != "merged":
                    raise TreeError("FT004", f"{nid} is merged but dependency {dep} is not (state={dep_node.get('state')})")

def are_related(a, b, nodes):
    def ancestors(nid, seen):
        node = nodes.get(nid)
        if not node: return seen
        for dep in node.get("depends_on", []):
            if dep not in seen:
                seen.add(dep); ancestors(dep, seen)
        return seen
    return b in ancestors(a, set()) or a in ancestors(b, set())

def check_disjoint_scope(nodes):
    ids = list(nodes.keys())
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = ids[i], ids[j]
            if are_related(a, b, nodes): continue
            for pa in nodes[a].get("file_scope", []):
                for pb in nodes[b].get("file_scope", []):
                    if pa == pb or fnmatch.fnmatch(pa, pb) or fnmatch.fnmatch(pb, pa):
                        raise TreeError("FT005", f"scope collision between {a} and {b}: '{pa}' overlaps '{pb}'")

def check_contracts_exist(nodes, repo_root):
    for nid, n in nodes.items():
        if not (repo_root / n["contract"]).exists():
            raise TreeError("FT006", f"{nid}: contract not found at {n['contract']}")

def check_diff_scope(nodes, node_id, diff_files):
    node = nodes.get(node_id)
    if node is None:
        raise TreeError("FT002", f"unknown node id: {node_id}")
    scope = node.get("file_scope", [])
    for f in diff_files:
        if not any(fnmatch.fnmatch(f, pattern) for pattern in scope):
            raise TreeError("FT031", f"diff escapes declared scope for {node_id}: '{f}' not in {scope}")

def resolve_merge_order(nodes):
    order, visited = [], set()
    def visit(nid):
        if nid in visited: return
        visited.add(nid)
        for dep in nodes[nid].get("depends_on", []): visit(dep)
        order.append(nid)
    for nid in nodes: visit(nid)
    return order

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tree", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--node")
    parser.add_argument("--diff-files", nargs="*", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    verdict = {"tree": str(args.tree), "checks": [], "verdict": "PASS"}
    try:
        tree = load_tree(args.tree); nodes = index_nodes(tree)
        check_dag(nodes); verdict["checks"].append("FT001 dag: PASS")
        check_stack_base(tree, nodes); verdict["checks"].append("FT003 stack_base: PASS")
        check_merge_order(nodes); verdict["checks"].append("FT004 merge_order: PASS")
        check_disjoint_scope(nodes); verdict["checks"].append("FT005 disjoint_scope: PASS")
        check_contracts_exist(nodes, args.repo_root); verdict["checks"].append("FT006 contracts_exist: PASS")
        if args.node:
            check_diff_scope(nodes, args.node, args.diff_files or [])
            verdict["checks"].append(f"FT031 diff_scope[{args.node}]: PASS")
            verdict["node"] = args.node
        verdict["merge_order"] = resolve_merge_order(nodes)
    except TreeError as e:
        verdict.update({"verdict": "FAIL", "error_code": e.code, "error_message": e.message})
        print(json.dumps(verdict, indent=2) if args.json else f"FAIL: {e.code} {e.message}")
        sys.exit(1)
    except Exception as e:
        print(f"FAIL: FT999 unexpected error: {e}", file=sys.stderr); sys.exit(2)
    if args.json: print(json.dumps(verdict, indent=2))
    else:
        print("PASS"); print("merge_order:", " -> ".join(verdict["merge_order"]))
    sys.exit(0)

if __name__ == "__main__":
    main()

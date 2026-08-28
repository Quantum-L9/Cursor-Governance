#!/usr/bin/env python3
import ast
import json
import sys
from pathlib import Path


def _name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def validate(path):
    path = Path(path)
    errors = []
    if not path.is_file():
        return {"status": "FAIL", "errors": [f"missing file: {path}"], "dag_symbols": []}
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        return {"status": "FAIL", "errors": [f"syntax error: {exc}"], "dag_symbols": []}

    dag_symbols = []
    node_ids = set()
    edges = []
    register_targets = []
    imported_register = False

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "workflows.session.registry":
            imported_register |= any(alias.name == "register_session_dag" for alias in node.names)
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = node.value
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if isinstance(value, ast.Call) and _name(value.func) == "SessionDAG":
                for target in targets:
                    if isinstance(target, ast.Name):
                        dag_symbols.append(target.id)
            if isinstance(value, ast.Call) and _name(value.func) == "SessionNode":
                for kw in value.keywords:
                    if (
                        kw.arg == "id"
                        and isinstance(kw.value, ast.Constant)
                        and isinstance(kw.value.value, str)
                    ):
                        node_ids.add(kw.value.value)
        if isinstance(node, ast.Call) and _name(node.func) == "SessionNode":
            for kw in node.keywords:
                if (
                    kw.arg == "id"
                    and isinstance(kw.value, ast.Constant)
                    and isinstance(kw.value.value, str)
                ):
                    node_ids.add(kw.value.value)
        if isinstance(node, ast.Call) and _name(node.func) == "SessionEdge":
            vals = {}
            for kw in node.keywords:
                if kw.arg in {"from_node", "to_node"} and isinstance(kw.value, ast.Constant):
                    vals[kw.arg] = kw.value.value
            if vals:
                edges.append(vals)
        if isinstance(node, ast.Call) and _name(node.func) == "register_session_dag" and node.args:
            register_targets.append(_name(node.args[0]))

    if len(dag_symbols) != 1:
        errors.append(
            f"expected exactly one canonical SessionDAG assignment, found {len(dag_symbols)}"
        )
    if not imported_register:
        errors.append("register_session_dag is not imported from workflows.session.registry")
    if dag_symbols and dag_symbols[0] not in register_targets:
        errors.append(
            f"canonical DAG symbol {dag_symbols[0]} is not registered "
            "through register_session_dag()"
        )
    dangling = sorted(
        {
            v
            for edge in edges
            for v in edge.values()
            if isinstance(v, str) and node_ids and v not in node_ids
        }
    )
    if dangling:
        errors.append("dangling static edge endpoints: " + ",".join(dangling))

    return {
        "status": "FAIL" if errors else "PASS",
        "errors": errors,
        "dag_symbols": dag_symbols,
        "node_count_static": len(node_ids),
        "edge_count_static": len(edges),
    }


def main(argv):
    if len(argv) != 2:
        print(
            json.dumps(
                {"status": "FAIL", "errors": ["usage: validate_session_dag_source.py DAG_FILE"]},
                indent=2,
            )
        )
        return 2
    result = validate(argv[1])
    print(json.dumps(result, indent=2, sort_keys=True))
    return 2 if result["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

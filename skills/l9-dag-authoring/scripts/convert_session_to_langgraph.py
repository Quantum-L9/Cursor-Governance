#!/usr/bin/env python3
"""Emit a LangGraph package only for CONVERT_TO_LANGGRAPH."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

from classify_conversion_disposition import classify_request
from validate_langgraph_source import validate as validate_langgraph
from validate_langgraph_source import validate_package

TERMINAL_KINDS = {"terminal"}
BOUNDED_KINDS = {"bounded_llm"}


def _literal(node: ast.AST):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.List):
        return [_literal(elt) for elt in node.elts]
    if isinstance(node, ast.Dict):
        out = {}
        for key, value in zip(node.keys, node.values, strict=False):
            if isinstance(key, ast.Constant):
                out[key.value] = _literal(value)
        return out
    if isinstance(node, ast.Call):
        return _literal_kwargs(node)
    return None


def _literal_kwargs(call: ast.Call) -> dict:
    return {kw.arg: _literal(kw.value) for kw in call.keywords if kw.arg}


def _called_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def load_session_graph(path: Path) -> dict:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    nodes: list[dict] = []
    edges: list[dict] = []
    entry = None
    dag_id = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _called_name(node)
        kwargs = _literal_kwargs(node)
        if name == "SessionNode":
            metadata = kwargs.get("metadata") if isinstance(kwargs.get("metadata"), dict) else {}
            nodes.append(
                {
                    "id": kwargs.get("id"),
                    "action": kwargs.get("action"),
                    "kind": metadata.get("ir_kind"),
                    "next": [],
                }
            )
        elif name == "SessionEdge":
            edges.append({"from": kwargs.get("from_node"), "to": kwargs.get("to_node")})
        elif name == "SessionDAG":
            dag_id = kwargs.get("id")
            entry = kwargs.get("entry_node")
    by_id = {n["id"]: n for n in nodes if n.get("id")}
    for edge in edges:
        src = by_id.get(edge.get("from"))
        if src is not None and edge.get("to"):
            src.setdefault("next", []).append(edge["to"])
    return {
        "id": dag_id,
        "entrypoint": entry or (nodes[0]["id"] if nodes else None),
        "nodes": nodes,
    }


def load_ir_graph(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    workflow = data.get("workflow") or {}
    nodes = []
    for raw in workflow.get("nodes") or []:
        nodes.append(
            {
                "id": raw.get("id"),
                "kind": raw.get("kind"),
                "action": raw.get("action"),
                "next": list(raw.get("next") or []),
                "capabilities": list(raw.get("capabilities") or []),
            }
        )
    return {
        "id": (data.get("authority") or {}).get("dag_registry_id"),
        "entrypoint": workflow.get("entrypoint"),
        "nodes": nodes,
    }


def _is_script(repo: Path, action: object) -> bool:
    if not isinstance(action, str) or not action.endswith(".py"):
        return False
    return (repo / action).is_file()


def _action_kind(repo: Path, node: dict) -> str:
    kind = node.get("kind")
    action = node.get("action")
    if kind in TERMINAL_KINDS:
        return "terminal"
    if kind in BOUNDED_KINDS:
        return "bounded_llm"
    if _is_script(repo, action):
        return "script"
    if kind == "deterministic":
        return "prose"
    if not action or action == "terminal state; no action":
        return "terminal"
    return "prose"


def refuse_prose(repo: Path, graph: dict) -> list[str]:
    errors = []
    for node in graph["nodes"]:
        if _action_kind(repo, node) == "prose":
            errors.append(f"prose_action_refused:{node.get('id')}:{node.get('action')}")
    return errors


def _builder_name(dag_id: str, emit_dir: Path) -> str:
    if dag_id == "intelligence-harvest-v1" or emit_dir.name == "intelligence_harvest":
        return "build_intelligence_harvest_graph"
    return "build_graph"


def _state_name(emit_dir: Path) -> str:
    if emit_dir.name == "intelligence_harvest":
        return "HarvestState"
    return "ConvertedState"


def emit_package(repo: Path, graph: dict, emit_dir: Path, dag_id: str) -> dict:
    emit_dir.mkdir(parents=True, exist_ok=True)
    builder = _builder_name(dag_id, emit_dir)
    state_name = _state_name(emit_dir)
    node_ids = [n["id"] for n in graph["nodes"] if n.get("id")]
    entry = graph.get("entrypoint") or node_ids[0]
    kinds = {n["id"]: _action_kind(repo, n) for n in graph["nodes"]}
    actions = {n["id"]: n.get("action") for n in graph["nodes"]}
    nexts = {n["id"]: list(n.get("next") or []) for n in graph["nodes"]}

    (emit_dir / "state.py").write_text(
        "from __future__ import annotations\n\n"
        "from typing import TypedDict\n\n\n"
        f"class {state_name}(TypedDict, total=False):\n"
        "    status: str\n"
        "    unknowns: list[str]\n"
        "    errors: list[str]\n"
        "    ran: list[str]\n"
        "    blocked: bool\n",
        encoding="utf-8",
    )

    node_lines = [
        "from __future__ import annotations\n",
        f"from workflows.dags.{emit_dir.name}.state import {state_name}\n",
        "\n",
    ]
    for nid in node_ids:
        kind = kinds[nid]
        fn = f"node_{nid.lower()}"
        if kind == "script":
            script = actions[nid]
            node_lines.append(
                f"def {fn}(state: {state_name}) -> {state_name}:\n"
                f"    ran = list(state.get('ran') or [])\n"
                f"    ran.append({script!r})\n"
                f"    state['ran'] = ran\n"
                f"    return state\n\n"
            )
        elif kind == "bounded_llm":
            node_lines.append(
                f"def {fn}(state: {state_name}) -> {state_name}:\n"
                f"    unknowns = list(state.get('unknowns') or [])\n"
                f"    unknowns.append({nid!r})\n"
                f"    state['unknowns'] = unknowns\n"
                f"    return state\n\n"
            )
        else:
            node_lines.append(
                f"def {fn}(state: {state_name}) -> {state_name}:\n"
                f"    state['status'] = {nid!r}\n"
                f"    return state\n\n"
            )
    (emit_dir / "nodes.py").write_text("".join(node_lines), encoding="utf-8")

    route_lines = [
        "from __future__ import annotations\n\n",
        f"from workflows.dags.{emit_dir.name}.state import {state_name}\n\n",
    ]
    route_fns: dict[str, str] = {}
    for nid, targets in nexts.items():
        if len(targets) <= 1:
            continue
        fn = f"route_after_{nid.lower()}"
        route_fns[nid] = fn
        route_lines.append(
            f"def {fn}(state: {state_name}) -> str:\n"
            f"    status = str(state.get('status') or '')\n"
            f"    if status in {targets!r}:\n"
            f"        return status\n"
            f"    if state.get('errors'):\n"
            f"        return 'FAIL' if 'FAIL' in {targets!r} else {targets[-1]!r}\n"
            f"    if state.get('blocked'):\n"
            f"        return 'BLOCKED' if 'BLOCKED' in {targets!r} else {targets[-1]!r}\n"
            f"    if state.get('unknowns'):\n"
            f"        return 'PARTIAL' if 'PARTIAL' in {targets!r} else {targets[0]!r}\n"
            f"    return {targets[0]!r}\n\n"
        )
    (emit_dir / "routing.py").write_text("".join(route_lines), encoding="utf-8")

    graph_lines = [
        "from __future__ import annotations\n\n",
        "from langgraph.graph import END, START, StateGraph\n\n",
        f"from workflows.dags.{emit_dir.name}.nodes import (\n",
    ]
    for nid in node_ids:
        graph_lines.append(f"    node_{nid.lower()},\n")
    graph_lines.append(")\n")
    if route_fns:
        graph_lines.append(f"from workflows.dags.{emit_dir.name}.routing import (\n")
        for fn in route_fns.values():
            graph_lines.append(f"    {fn},\n")
        graph_lines.append(")\n")
    graph_lines.append(f"from workflows.dags.{emit_dir.name}.state import {state_name}\n\n\n")
    graph_lines.append(f"def {builder}() -> StateGraph:\n")
    graph_lines.append(f"    graph = StateGraph({state_name})\n")
    for nid in node_ids:
        graph_lines.append(f"    graph.add_node({nid!r}, node_{nid.lower()})\n")
    graph_lines.append(f"    graph.add_edge(START, {entry!r})\n")
    for nid, targets in nexts.items():
        if not targets:
            graph_lines.append(f"    graph.add_edge({nid!r}, END)\n")
        elif len(targets) == 1:
            graph_lines.append(f"    graph.add_edge({nid!r}, {targets[0]!r})\n")
        else:
            mapping = ", ".join(f"{t!r}: {t!r}" for t in targets)
            graph_lines.append(
                f"    graph.add_conditional_edges({nid!r}, {route_fns[nid]}, {{{mapping}}})\n"
            )
    graph_lines.append("    return graph\n")
    graph_py = emit_dir / "graph.py"
    graph_py.write_text("".join(graph_lines), encoding="utf-8")

    dag_key = str(graph.get("id") or emit_dir.name)
    (emit_dir / "executor.py").write_text(
        "from __future__ import annotations\n\n"
        "from datetime import datetime\n"
        "from pathlib import Path\n"
        "from typing import Any\n\n"
        "from workflows.dags._runtime.durable_checkpointer import open_checkpointer\n"
        f"from workflows.dags.{emit_dir.name}.graph import {builder}\n\n"
        f"DAG_ID = {dag_key!r}\n\n\n"
        "def compile_graph(workspace: Path | None = None):\n"
        "    root = Path(workspace) if workspace else Path.cwd()\n"
        "    checkpointer = open_checkpointer(DAG_ID, workspace=root)\n"
        f"    return {builder}().compile(checkpointer=checkpointer)\n\n\n"
        "class RuntimeExecutor:\n"
        "    def __init__(self, workspace: Path | None = None):\n"
        "        self.workspace = Path(workspace) if workspace else Path.cwd()\n"
        "        self.checkpointer = open_checkpointer(DAG_ID, workspace=self.workspace)\n"
        f"        self.compiled = {builder}().compile(checkpointer=self.checkpointer)\n\n"
        "    def run(self, initial: dict[str, Any] | None = None, thread_id: str | None = None):\n"
        "        if thread_id is None:\n"
        "            thread_id = f\"{DAG_ID}-{datetime.now().strftime('%Y%m%d%H%M%S%f')}\"\n"
        '        config = {"configurable": {"thread_id": thread_id}}\n'
        "        state = self.compiled.invoke(initial or {}, config)\n"
        '        return {"thread_id": thread_id, "state": state}\n\n'
        "    def resume(self, thread_id: str, updates: dict[str, Any] | None = None):\n"
        '        config = {"configurable": {"thread_id": thread_id}}\n'
        "        current = self.compiled.get_state(config)\n"
        "        payload = dict(current.values) if current else {}\n"
        "        if updates:\n"
        "            payload.update(updates)\n"
        "        state = self.compiled.invoke(payload, config)\n"
        '        return {"thread_id": thread_id, "state": state}\n\n'
        "    def get_state(self, thread_id: str):\n"
        '        config = {"configurable": {"thread_id": thread_id}}\n'
        "        snapshot = self.compiled.get_state(config)\n"
        "        return snapshot.values if snapshot else None\n",
        encoding="utf-8",
    )
    (emit_dir / "__init__.py").write_text(
        f"from workflows.dags.{emit_dir.name}.graph import {builder}\n\n__all__ = [{builder!r}]\n",
        encoding="utf-8",
    )

    proof = validate_langgraph(graph_py)
    package = validate_package(emit_dir)
    return {
        "emitted_runtime": str(graph_py.as_posix()),
        "builder": builder,
        "nodes": node_ids,
        "validate": proof,
        "validate_package": package,
    }


def convert(
    repo: Path,
    *,
    dag_id: str | None = None,
    disposition: str | None = None,
    source: Path | None = None,
    proof_path: Path | None = None,
    emit_dir: Path | None = None,
) -> dict:
    if disposition and disposition != "CONVERT_TO_LANGGRAPH":
        return {
            "status": "FAIL",
            "reason": "disposition_must_be_CONVERT_TO_LANGGRAPH",
            "disposition": disposition,
        }
    row = None
    if dag_id and disposition is None:
        row = classify_request(repo, dag_id)
        if row.get("status") != "PASS":
            return {"status": row.get("status", "BLOCKED"), **row}
        disposition = row.get("disposition")
        if disposition != "CONVERT_TO_LANGGRAPH":
            return {
                "status": "FAIL",
                "reason": "disposition_must_be_CONVERT_TO_LANGGRAPH",
                "disposition": disposition,
                "dag_id": dag_id,
            }
        if source is None and row.get("source_path"):
            source = repo / str(row["source_path"])
        if proof_path is None and row.get("proof_path"):
            proof_path = repo / str(row["proof_path"])
        if emit_dir is None and row.get("emit_dir"):
            emit_dir = repo / str(row["emit_dir"])

    if disposition != "CONVERT_TO_LANGGRAPH":
        return {
            "status": "FAIL",
            "reason": "disposition_must_be_CONVERT_TO_LANGGRAPH",
            "disposition": disposition,
        }
    if emit_dir is None:
        return {"status": "FAIL", "reason": "emit_dir_required"}

    if proof_path and proof_path.suffix == ".json":
        graph = load_ir_graph(proof_path)
        if source and source.suffix == ".py":
            session = load_session_graph(source)
            actions = {n["id"]: n for n in session["nodes"]}
            for node in graph["nodes"]:
                match = actions.get(node["id"])
                if match:
                    node["action"] = node.get("action") or match.get("action")
                    node["kind"] = node.get("kind") or match.get("kind")
    elif source and source.suffix == ".py":
        graph = load_session_graph(source)
    else:
        return {"status": "FAIL", "reason": "no_graph_source"}

    dag_id = dag_id or graph.get("id")
    errors = refuse_prose(repo, graph)
    if errors:
        return {"status": "FAIL", "reason": "prose_action_refused", "errors": errors}

    emitted = emit_package(repo, graph, emit_dir, str(dag_id or "converted"))
    if emitted["validate"].get("status") != "PASS":
        return {
            "status": "FAIL",
            "reason": "langgraph_source_invalid",
            "validate": emitted["validate"],
        }
    if emitted.get("validate_package", {}).get("status") != "PASS":
        return {
            "status": "FAIL",
            "reason": "langgraph_package_invalid",
            "validate": emitted["validate"],
            "validate_package": emitted.get("validate_package"),
        }
    return {
        "status": "PASS",
        "dag_id": dag_id,
        "disposition": "CONVERT_TO_LANGGRAPH",
        "emitted_runtime": emitted["emitted_runtime"],
        "builder": emitted["builder"],
        "nodes": emitted["nodes"],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", required=True)
    ap.add_argument("--dag-id")
    ap.add_argument("--disposition")
    ap.add_argument("--source")
    ap.add_argument("--proof-path")
    ap.add_argument("--emit-dir")
    ns = ap.parse_args(argv)
    result = convert(
        Path(ns.repo_root),
        dag_id=ns.dag_id,
        disposition=ns.disposition,
        source=Path(ns.source) if ns.source else None,
        proof_path=Path(ns.proof_path) if ns.proof_path else None,
        emit_dir=Path(ns.emit_dir) if ns.emit_dir else None,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())

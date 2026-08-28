#!/usr/bin/env python3
"""Classify a graph source as SESSION_GUIDANCE, LANGGRAPH_RUNTIME, or UNKNOWN.

Classification reads the AST, not raw text. A SessionDAG module that *documents*
LangGraph validation in a node ``action`` string is still SESSION_GUIDANCE: the
mention lives in a string literal, which is not a construction or an import.
Raw-substring matching classifies such a file as mixed and blocks it, which
would make `workflows/dags/dag_authoring_dag.py` — the graph whose own job is to
describe both kinds — unclassifiable by the Skill that owns it.

Evidence is ranked. A construction call (`SessionDAG(...)` / `StateGraph(...)`)
outranks an import, because a module that builds the graph is the graph's home;
a module that merely imports the type may be a helper. Only same-rank evidence
for both kinds is mixed.
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

SESSION_TYPES = {"SessionDAG"}
LANGGRAPH_TYPES = {"StateGraph"}
SESSION_MODULES = ("workflows.session.interface", "workflows.session.registry")
LANGGRAPH_MODULES = ("langgraph.graph", "langgraph")

# Text fallback for non-Python or unparseable sources only.
SESSION_MARKERS = ("SessionDAG", "workflows.session.interface")
LANGGRAPH_MARKERS = ("StateGraph", "langgraph.graph")


def _called_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _collect(tree: ast.AST) -> tuple[set[str], set[str]]:
    """Return (constructed_kinds, imported_kinds)."""
    constructed: set[str] = set()
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = _called_name(node)
            if name in SESSION_TYPES:
                constructed.add("SESSION_GUIDANCE")
            elif name in LANGGRAPH_TYPES:
                constructed.add("LANGGRAPH_RUNTIME")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.startswith(SESSION_MODULES):
                imported.add("SESSION_GUIDANCE")
            elif module.startswith(LANGGRAPH_MODULES):
                imported.add("LANGGRAPH_RUNTIME")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith(SESSION_MODULES):
                    imported.add("SESSION_GUIDANCE")
                elif alias.name.startswith(LANGGRAPH_MODULES):
                    imported.add("LANGGRAPH_RUNTIME")
    return constructed, imported


def _from_text(text: str) -> dict:
    session = any(marker in text for marker in SESSION_MARKERS)
    langgraph = any(marker in text for marker in LANGGRAPH_MARKERS)
    if session and langgraph:
        return {
            "status": "BLOCKED",
            "graph_kind": "UNKNOWN",
            "evidence": "text",
            "reason": "mixed_session_and_langgraph_markers",
        }
    if session:
        return {"status": "PASS", "graph_kind": "SESSION_GUIDANCE", "evidence": "text"}
    if langgraph:
        return {"status": "PASS", "graph_kind": "LANGGRAPH_RUNTIME", "evidence": "text"}
    return {
        "status": "BLOCKED",
        "graph_kind": "UNKNOWN",
        "evidence": "text",
        "reason": "no_canonical_graph_markers",
    }


def classify(path: Path) -> dict:
    path = Path(path)
    if not path.is_file():
        return {"status": "FAIL", "graph_kind": "UNKNOWN", "reason": f"missing file: {path}"}
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        return _from_text(text)

    constructed, imported = _collect(tree)

    for kinds, evidence in ((constructed, "construction"), (imported, "import")):
        if len(kinds) == 1:
            return {"status": "PASS", "graph_kind": next(iter(kinds)), "evidence": evidence}
        if len(kinds) > 1:
            return {
                "status": "BLOCKED",
                "graph_kind": "UNKNOWN",
                "evidence": evidence,
                "reason": "mixed_session_and_langgraph_markers",
            }

    return {
        "status": "BLOCKED",
        "graph_kind": "UNKNOWN",
        "evidence": "ast",
        "reason": "no_canonical_graph_markers",
    }


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(
            json.dumps(
                {"status": "FAIL", "error": "usage: classify_graph_kind.py SOURCE.py"}, indent=2
            )
        )
        return 2
    result = classify(Path(argv[1]))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

#!/usr/bin/env python3
"""Validate a LANGGRAPH_RUNTIME source.

Session-registry contamination is detected from the AST — an import of, or a call
to, `register_session_dag`, or a `SessionDAG(...)` construction. A runtime module
that names the registry only inside a docstring to say it must *not* be used is
documenting the boundary, not crossing it, and is not a violation.
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

SESSION_SYMBOLS = {"SessionDAG", "register_session_dag", "get_session_dag"}


def _called_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def validate(path: Path) -> dict:
    path = Path(path)
    if not path.is_file():
        return {"status": "FAIL", "errors": [f"missing file: {path}"]}
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        return {"status": "FAIL", "errors": [f"syntax_error:{exc.msg}"]}

    imports_langgraph = False
    constructs_stategraph = False
    session_symbols: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.startswith("langgraph"):
                imports_langgraph = True
            if module.startswith("workflows.session"):
                session_symbols.update(
                    alias.name for alias in node.names if alias.name in SESSION_SYMBOLS
                )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("langgraph"):
                    imports_langgraph = True
        elif isinstance(node, ast.Call):
            name = _called_name(node)
            if name == "StateGraph":
                constructs_stategraph = True
            elif name in SESSION_SYMBOLS:
                session_symbols.add(name)

    if not imports_langgraph:
        errors.append("missing_StateGraph_contract")
    if not constructs_stategraph:
        errors.append("no_StateGraph_construction")
    if session_symbols:
        errors.append(
            "langgraph_runtime_must_not_use_session_registry: " + ",".join(sorted(session_symbols))
        )

    return {"status": "FAIL" if errors else "PASS", "errors": errors}


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(
            json.dumps(
                {"status": "FAIL", "error": "usage: validate_langgraph_source.py SOURCE.py"},
                indent=2,
            )
        )
        return 2
    result = validate(Path(argv[1]))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

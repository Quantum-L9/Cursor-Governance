#!/usr/bin/env python3
"""Validate a LANGGRAPH_RUNTIME source.

Session-registry contamination is detected from the AST — an import of, or a call
to, `register_session_dag`, or a `SessionDAG(...)` construction. A runtime module
that names the registry only inside a docstring to say it must *not* be used is
documenting the boundary, not crossing it, and is not a violation.

`validate(path)` is structural (one .py that constructs StateGraph).
`validate_package(dir)` is the LANGGRAPH_RUNTIME durability gate.
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

SESSION_SYMBOLS = {"SessionDAG", "register_session_dag", "get_session_dag"}
EPHEMERAL_SAVERS = {"MemorySaver", "InMemorySaver"}
REASON_CODES = (
    "missing_durable_checkpointer",
    "ephemeral_checkpointer",
    "missing_thread_id",
    "builder_compiles_graph",
    "compile_not_in_executor",
)


def _called_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _parse(path: Path) -> ast.AST | dict:
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        return {"status": "FAIL", "errors": [f"syntax_error:{exc.msg}"]}


def _calls_named(tree: ast.AST, name: str) -> bool:
    return any(isinstance(node, ast.Call) and _called_name(node) == name for node in ast.walk(tree))


def _compile_calls(tree: ast.AST) -> list[ast.Call]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and _called_name(node) == "compile"
    ]


def validate(path: Path) -> dict:
    path = Path(path)
    if not path.is_file():
        return {"status": "FAIL", "errors": [f"missing file: {path}"]}
    tree = _parse(path)
    if isinstance(tree, dict):
        return tree

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

    errors: list[str] = []
    if not imports_langgraph:
        errors.append("missing_StateGraph_contract")
    if not constructs_stategraph:
        errors.append("no_StateGraph_construction")
    if session_symbols:
        errors.append(
            "langgraph_runtime_must_not_use_session_registry: " + ",".join(sorted(session_symbols))
        )

    return {"status": "FAIL" if errors else "PASS", "errors": errors}


def _executor_persistence(executor: Path) -> tuple[str, list[str]]:
    """Return (persistence_class, errors) for executor.py."""
    errors: list[str] = []
    tree = _parse(executor)
    if isinstance(tree, dict):
        return "none", list(tree.get("errors") or ["executor_unreadable"])

    compiles = _compile_calls(tree)
    if not compiles:
        errors.append("compile_not_in_executor")
        return "none", errors

    has_checkpointer = False
    ephemeral = False
    for call in compiles:
        for kw in call.keywords:
            if kw.arg == "checkpointer":
                has_checkpointer = True
                value = kw.value
                name = None
                if isinstance(value, ast.Call):
                    name = _called_name(value)
                elif isinstance(value, ast.Name):
                    name = value.id
                if name in EPHEMERAL_SAVERS:
                    ephemeral = True

    if _calls_named(tree, "MemorySaver") or _calls_named(tree, "InMemorySaver"):
        ephemeral = True
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name in EPHEMERAL_SAVERS:
                    ephemeral = True
        elif isinstance(node, ast.Name) and node.id in EPHEMERAL_SAVERS:
            ephemeral = True

    if not has_checkpointer:
        errors.append("missing_durable_checkpointer")
        persistence = "none"
    elif ephemeral:
        errors.append("ephemeral_checkpointer")
        persistence = "ephemeral"
    else:
        persistence = "durable"

    text = executor.read_text(encoding="utf-8")
    if "thread_id" not in text:
        errors.append("missing_thread_id")

    return persistence, errors


def validate_package(directory: Path) -> dict:
    directory = Path(directory)
    errors: list[str] = []
    if not directory.is_dir():
        return {
            "status": "FAIL",
            "errors": [f"missing package directory: {directory}"],
            "persistence_class": "none",
        }

    graph_py = directory / "graph.py"
    executor_py = directory / "executor.py"

    if graph_py.is_file():
        structural = validate(graph_py)
        errors.extend(structural.get("errors") or [])
        tree = _parse(graph_py)
        if isinstance(tree, ast.AST) and _compile_calls(tree):
            errors.append("builder_compiles_graph")
    else:
        errors.append("missing_StateGraph_contract")

    persistence = "none"
    if executor_py.is_file():
        persistence, exec_errors = _executor_persistence(executor_py)
        errors.extend(exec_errors)
    else:
        errors.append("compile_not_in_executor")
        errors.append("missing_durable_checkpointer")

    unique = list(dict.fromkeys(errors))
    status = "PASS" if (not unique and persistence == "durable") else "FAIL"
    return {
        "status": status,
        "errors": unique,
        "persistence_class": persistence,
    }


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "error": "usage: validate_langgraph_source.py SOURCE.py|PACKAGE_DIR",
                },
                indent=2,
            )
        )
        return 2
    target = Path(argv[1])
    result = validate_package(target) if target.is_dir() else validate(target)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

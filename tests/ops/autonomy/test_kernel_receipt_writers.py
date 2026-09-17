#!/usr/bin/env python3
"""One writer per receipt plane.

`ops/autonomy/l4_local.py` `record_kernels()` used to call
`kernel_gate.record()` as a side effect of an L4 self-report. That made two
modules writers of `.l9/autonomy/kernel-receipt.json`, and it let the weaker
claim -- two CLI flags -- satisfy a gate whose whole purpose is to ask for
evidence. Worse, the call sat inside `try/except Exception` *after* the phase
was already advanced, so hardening `record()` would have failed silently and
the agent would have proceeded anyway.

These checks are AST-based on purpose. The receipt itself lives under gitignored
`.l9/`, so no CI job can ever inspect one; the only enforceable invariant is a
static property of the source.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OPS = REPO / "ops"
SOLE_WRITER = OPS / "autonomy" / "kernel_gate.py"
RECEIPT_BASENAME = "kernel-receipt.json"


def _ops_modules() -> list[Path]:
    return sorted(p for p in OPS.rglob("*.py") if p.resolve() != SOLE_WRITER.resolve())


def _parse(path: Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return None


def _docstring_nodes(tree: ast.Module) -> list[ast.Constant]:
    holders = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    found: list[ast.Constant] = []
    for node in ast.walk(tree):
        if not isinstance(node, holders):
            continue
        body = getattr(node, "body", None) or []
        if not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            found.append(first.value)
    return found


class KernelReceiptHasOneWriter(unittest.TestCase):
    def test_no_ops_module_imports_kernel_gate_record(self) -> None:
        offenders: list[str] = []
        for path in _ops_modules():
            tree = _parse(path)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom):
                    continue
                module = node.module or ""
                if not module.endswith("kernel_gate"):
                    continue
                for alias in node.names:
                    if alias.name == "record":
                        rel = path.relative_to(REPO)
                        offenders.append(f"{rel}:{node.lineno} imports kernel_gate.record")
        self.assertEqual(
            offenders,
            [],
            "kernel_gate.record is the sole writer of the tree receipt; "
            f"remove these imports: {offenders}",
        )

    def test_no_ops_module_calls_kernel_gate_record(self) -> None:
        offenders: list[str] = []
        for path in _ops_modules():
            tree = _parse(path)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if (
                    isinstance(func, ast.Attribute)
                    and func.attr == "record"
                    and isinstance(func.value, ast.Name)
                    and func.value.id.endswith("kernel_gate")
                ):
                    rel = path.relative_to(REPO)
                    offenders.append(f"{rel}:{node.lineno} calls kernel_gate.record()")
        self.assertEqual(offenders, [], f"second stamp path reintroduced: {offenders}")

    def test_only_kernel_gate_builds_the_receipt_path(self) -> None:
        """Code may not re-derive the receipt path; prose may describe it.

        Docstrings and comments are excluded deliberately: the invariant is
        about who constructs the path, and documenting the plane is how the
        next reader learns it has one owner.
        """
        offenders: list[str] = []
        for path in _ops_modules():
            tree = _parse(path)
            if tree is None:
                continue
            docstrings = {id(node) for node in _docstring_nodes(tree)}
            for node in ast.walk(tree):
                if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                    continue
                if id(node) in docstrings:
                    continue
                if RECEIPT_BASENAME in node.value:
                    rel = path.relative_to(REPO)
                    offenders.append(f"{rel}:{node.lineno}")
        self.assertEqual(
            offenders,
            [],
            f"{RECEIPT_BASENAME} path built outside kernel_gate.py: {offenders}. "
            "Read it through kernel_gate, do not re-derive the path.",
        )

    def test_l4_record_kernels_advances_phase_without_stamping(self) -> None:
        source = (OPS / "autonomy" / "l4_local.py").read_text(encoding="utf-8")
        self.assertNotIn("stamp_kernel_hook", source)
        self.assertNotIn("kernel_hook_stamp", source)


if __name__ == "__main__":
    unittest.main()

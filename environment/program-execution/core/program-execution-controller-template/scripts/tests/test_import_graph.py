"""The `pec` package must stay acyclic.

It was not, and the workaround was deferred (function-local) imports: `replan`
reached back into `controller` from inside three wrapper functions, closing two
cycles that CodeQL reported as `py/cyclic-import`. Deferring an import hides a
cycle from the interpreter without removing it -- the modules still cannot be
reasoned about or imported independently, and nothing stops the next edit from
re-adding the edge.

So the primary invariant counts function-local imports, because that is the
graph CodeQL reasons about. A module-level-only view is *not* sufficient here:
it already held before the fix (every cycle was broken by a deferral), so it
would have passed on the broken shape and caught nothing. Both views are
asserted, but only the deferred-counting one discriminates.

These are `unittest.TestCase` classes on purpose. This directory is owned by the
`program-execution-controller` suite in `ops/config/python-contract.json`, which
runs `unittest discover`; it is excluded from root pytest. Bare pytest-style
functions here are collected by nothing and run in no CI job.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

PEC = Path(__file__).resolve().parents[1] / "pec"


def _sibling_edges(*, include_deferred: bool) -> dict[str, set[str]]:
    """Sibling-import graph, optionally counting function-local imports.

    `include_deferred=True` is the graph CodeQL's `py/cyclic-import` reasons
    about: it does not care that an edge is written inside a function body, so
    neither can the guard. `include_deferred=False` is the narrower graph that
    decides whether a module can be imported standalone.
    """
    edges: dict[str, set[str]] = {}
    for path in sorted(PEC.glob("*.py")):
        module = path.stem
        edges[module] = set()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        nodes = ast.walk(tree) if include_deferred else tree.body
        for node in nodes:
            if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
                edges[module].add(node.module.split(".")[0])
    return edges


def _find_cycle(edges: dict[str, set[str]]) -> list[str] | None:
    """Return one cycle as an explicit chain, or None.

    Depth-first search colouring nodes grey while they are on the current path
    and black once fully explored. Re-entering a grey node is a back-edge, and
    the slice of the path from that node onward is the cycle.
    """
    on_path: set[str] = set()
    finished: set[str] = set()
    path: list[str] = []

    def visit(node: str) -> list[str] | None:
        if node in finished:
            return None
        if node in on_path:
            return path[path.index(node) :] + [node]
        on_path.add(node)
        path.append(node)
        for nxt in sorted(edges.get(node, ())):
            if nxt not in edges:  # not a sibling module (stdlib, third party)
                continue
            found = visit(nxt)
            if found is not None:
                return found
        path.pop()
        on_path.discard(node)
        finished.add(node)
        return None

    for module in sorted(edges):
        found = visit(module)
        if found is not None:
            return found
    return None


class ImportGraphTests(unittest.TestCase):
    def test_detector_reports_a_cycle_when_one_exists(self) -> None:
        """Guard the guard: a detector that never fires would assert nothing."""
        self.assertEqual(_find_cycle({"a": {"b"}, "b": {"a"}}), ["a", "b", "a"])
        self.assertEqual(_find_cycle({"a": {"a"}}), ["a", "a"])
        self.assertIsNone(_find_cycle({"a": {"b"}, "b": {"c"}, "c": set()}))
        self.assertIsNone(_find_cycle({"a": {"b", "c"}, "b": {"d"}, "c": {"d"}, "d": set()}))

        # The exact pre-fix shape: the deleted replan -> controller back-edge.
        edges = _sibling_edges(include_deferred=True)
        replayed = {k: set(v) for k, v in edges.items()}
        replayed["replan"].add("controller")
        self.assertIsNotNone(
            _find_cycle(replayed),
            "re-adding replan -> controller must be detected as a cycle",
        )

    def test_pec_has_no_import_cycle_counting_deferred_imports(self) -> None:
        """The invariant CodeQL enforces. Deferring an edge does not clear it.

        This is the discriminating one: before the extraction it fails on
        `controller -> contracts -> replan -> controller`, which is exactly the
        chain alert 409 reported.
        """
        edges = _sibling_edges(include_deferred=True)
        self.assertTrue(edges, f"no modules discovered under {PEC}")
        cycle = _find_cycle(edges)
        self.assertIsNone(
            cycle,
            "pec has an import cycle: "
            + " -> ".join(cycle or [])
            + ". Move the shared symbols into a leaf module (see pec/runtime.py) "
            "rather than deferring the import inside a function -- a deferred "
            "import hides the cycle from the interpreter, it does not remove it, "
            "and CodeQL py/cyclic-import still reports it.",
        )

    def test_pec_is_also_acyclic_at_module_level(self) -> None:
        """The narrower invariant: every module stays importable standalone."""
        cycle = _find_cycle(_sibling_edges(include_deferred=False))
        self.assertIsNone(cycle, "pec has a module-level import cycle: " + " -> ".join(cycle or []))

    def test_runtime_module_stays_a_leaf(self) -> None:
        """`pec.runtime` exists to break the cycle; it must import nothing that cycles.

        It may only depend on modules that never import back into `controller`
        or `replan`. If this fails, the extraction has been undone.
        """
        allowed = {"common", "ledger", "state"}
        actual = _sibling_edges(include_deferred=True)["runtime"]
        self.assertLessEqual(
            actual,
            allowed,
            f"pec.runtime imports {sorted(actual - allowed)}; it may only import "
            f"{sorted(allowed)} or it stops being a leaf and the cycle returns",
        )

    def test_replan_does_not_import_controller(self) -> None:
        """The back-edge that closed both cycles, at module or function level."""
        source = (PEC / "replan.py").read_text(encoding="utf-8")
        self.assertNotIn(
            "from .controller import",
            source,
            "replan imports controller again -- this is the edge that closed "
            "both cycles. The three symbols it needs (open_runtime, "
            "_runtime_config, _require_stack_proof_reentry) live in "
            "pec/runtime.py.",
        )


if __name__ == "__main__":
    unittest.main()

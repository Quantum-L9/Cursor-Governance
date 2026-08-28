"""The `pec` package must stay acyclic at module level.

It was not, and the workaround was deferred (function-local) imports: `replan`
reached back into `controller` from inside three wrapper functions, closing two
cycles that CodeQL reported as `py/cyclic-import`. Deferring an import hides a
cycle from the interpreter without removing it -- the modules still cannot be
reasoned about or imported independently, and nothing stops the next edit from
re-adding the edge.

So the invariant is asserted on the *module-level* graph, which is the one that
decides whether a module can be imported on its own. Function-local imports are
deliberately not counted: they are legitimate for genuinely optional or lazy
dependencies. What this test forbids is a module-level cycle returning by
accident.
"""

from __future__ import annotations

import ast
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


def test_pec_has_no_import_cycle_counting_deferred_imports() -> None:
    """The invariant CodeQL enforces. Deferring an edge does not clear it.

    This is the discriminating one: before the extraction it fails on
    `controller -> contracts -> replan -> controller`, which is exactly the
    chain alert 409 reported.
    """
    edges = _sibling_edges(include_deferred=True)
    assert edges, f"no modules discovered under {PEC}"
    cycle = _find_cycle(edges)
    assert cycle is None, (
        "pec has an import cycle: "
        + " -> ".join(cycle or [])
        + ". Move the shared symbols into a leaf module (see pec/runtime.py) "
        "rather than deferring the import inside a function -- a deferred "
        "import hides the cycle from the interpreter, it does not remove it, "
        "and CodeQL py/cyclic-import still reports it."
    )


def test_pec_is_also_acyclic_at_module_level() -> None:
    """The narrower invariant: every module stays importable standalone."""
    cycle = _find_cycle(_sibling_edges(include_deferred=False))
    assert cycle is None, "pec has a module-level import cycle: " + " -> ".join(cycle or [])


def test_runtime_module_stays_a_leaf() -> None:
    """`pec.runtime` exists to break the cycle; it must import nothing that cycles.

    It may only depend on modules that never import back into `controller` or
    `replan`. If this fails, the extraction has been undone.
    """
    allowed = {"common", "ledger", "state"}
    actual = _sibling_edges(include_deferred=True)["runtime"]
    assert actual <= allowed, (
        f"pec.runtime imports {sorted(actual - allowed)}; it may only import "
        f"{sorted(allowed)} or it stops being a leaf and the cycle returns"
    )


def test_replan_does_not_import_controller() -> None:
    """The specific back-edge that closed both cycles, at module or function level."""
    source = (PEC / "replan.py").read_text(encoding="utf-8")
    assert "from .controller import" not in source, (
        "replan imports controller again -- this is the edge that closed both "
        "cycles. The three symbols it needs (open_runtime, _runtime_config, "
        "_require_stack_proof_reentry) live in pec/runtime.py."
    )

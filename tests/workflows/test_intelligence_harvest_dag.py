"""The registered DAG must stay a projection of the pack IR, never a second graph.

`skills/l9-intelligence-harvest` declares `workflows/dags/intelligence_harvest_dag.py`
as its canonical runtime and states that the pack "must not invent a parallel
registry". The IR owns the typed graph; the module registers it. Nothing but a
test can hold those two together once they live in different files.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from workflows.dags.intelligence_harvest_dag import INTELLIGENCE_HARVEST_V1

ROOT = Path(__file__).resolve().parents[2]
IR_PATH = ROOT / "skills" / "l9-intelligence-harvest" / "meta" / "skill-ir.json"

DAG = INTELLIGENCE_HARVEST_V1
IR = json.loads(IR_PATH.read_text(encoding="utf-8"))["workflow"]


def test_the_skill_declares_this_module_and_registry_id() -> None:
    authority = json.loads(IR_PATH.read_text(encoding="utf-8"))["authority"]
    assert authority["canonical_dag"] == "workflows/dags/intelligence_harvest/graph.py"
    assert authority["dag_registry_id"] == DAG.id == "intelligence-harvest-v1"


def test_node_set_matches_the_ir_exactly() -> None:
    assert {n.id for n in DAG.nodes} == {n["id"] for n in IR["nodes"]}


def test_edge_set_matches_the_ir_exactly() -> None:
    ir_edges = {(n["id"], nxt) for n in IR["nodes"] for nxt in n["next"]}
    assert {(e.from_node, e.to_node) for e in DAG.edges} == ir_edges


def test_entrypoint_matches_the_ir() -> None:
    assert DAG.entry_node == IR["entrypoint"]


def test_every_node_carries_its_ir_kind_and_capabilities() -> None:
    by_id = {n["id"]: n for n in IR["nodes"]}
    for node in DAG.nodes:
        source = by_id[node.id]
        assert node.metadata["ir_kind"] == source["kind"]
        assert node.metadata["impl"] == source["impl"]
        assert node.metadata["capabilities"] == source["capabilities"]


def test_dag_structure_is_valid_and_registered() -> None:
    from workflows.session.registry import get_session_dag

    assert DAG.validate() == []
    assert get_session_dag("intelligence-harvest-v1") is DAG


def test_terminal_states_are_the_four_the_skill_documents() -> None:
    terminals = {n["id"] for n in IR["nodes"] if n["kind"] == "terminal"}
    assert terminals == {"PASS", "PARTIAL", "BLOCKED", "FAIL"}
    for name in terminals:
        assert DAG.get_next_nodes(name) == [], f"{name} must be terminal"


def test_every_node_is_reachable_from_the_entrypoint() -> None:
    """An unreachable node is a graph that does not do what the pack says."""
    seen: set[str] = set()
    queue = [DAG.entry_node]
    while queue:
        current = queue.pop()
        if current in seen:
            continue
        seen.add(current)
        queue.extend(DAG.get_next_nodes(current))
    assert seen == {n.id for n in DAG.nodes}


@pytest.mark.parametrize(
    "script",
    [
        "bind_request.py",
        "inventory_source.py",
        "qualify_nuggets.py",
        "rank_nuggets.py",
        "validate_harvest.py",
        "render_brief.py",
    ],
)
def test_deterministic_node_scripts_exist_in_the_pack(script: str) -> None:
    """The pack's rule: never substitute model judgment for these operations."""
    assert (ROOT / "skills" / "l9-intelligence-harvest" / "scripts" / script).is_file()

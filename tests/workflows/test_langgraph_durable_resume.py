"""Crash-resume proof for the workspace sqlite checkpointer.

AST validate_package is not this test. Instance A must die (or drop) before
instance B reads the same sqlite path and thread_id.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills" / "l9-dag-authoring" / "scripts"))

from validate_langgraph_source import validate, validate_package  # noqa: E402

from workflows.dags._runtime.durable_checkpointer import (  # noqa: E402
    checkpoint_path,
    open_checkpointer,
)
from workflows.dags.gmp.state import GMPPhase, GMPState  # noqa: E402

DAG_ID = "durable-resume-fixture"
THREAD_ID = "crash-resume-1"


class ResumeState(TypedDict, total=False):
    step1_done: bool
    step1_runs: int
    step2_done: bool


def _close(saver: Any) -> None:
    conn = getattr(saver, "conn", None)
    if conn is not None:
        conn.close()


def _build_resume_graph(flag: Path) -> StateGraph:
    def node1(state: ResumeState) -> dict[str, Any]:
        if state.get("step1_done"):
            return {}
        prior = 0
        if flag.exists():
            prior = int(flag.read_text(encoding="utf-8") or "0")
        flag.write_text(str(prior + 1), encoding="utf-8")
        return {"step1_done": True, "step1_runs": state.get("step1_runs", 0) + 1}

    def node2(state: ResumeState) -> dict[str, Any]:
        return {"step2_done": True}

    graph = StateGraph(ResumeState)
    graph.add_node("node1", node1)
    graph.add_node("node2", node2)
    graph.add_edge(START, "node1")
    graph.add_edge("node1", "node2")
    graph.add_edge("node2", END)
    return graph


def test_two_instance_crash_resume(tmp_path: Path) -> None:
    flag = tmp_path / "node1.runs"
    config = {"configurable": {"thread_id": THREAD_ID}}

    saver_a = open_checkpointer(DAG_ID, workspace=tmp_path)
    compiled_a = _build_resume_graph(flag).compile(
        checkpointer=saver_a,
        interrupt_after=["node1"],
    )
    compiled_a.invoke({}, config)
    snap_a = compiled_a.get_state(config)
    values_a = snap_a.values if snap_a else {}
    assert values_a.get("step1_done") is True
    assert values_a.get("step1_runs") == 1
    assert values_a.get("step2_done") is not True
    assert flag.read_text(encoding="utf-8") == "1"
    _close(saver_a)
    del compiled_a
    del saver_a

    db = checkpoint_path(DAG_ID, workspace=tmp_path)
    assert db.is_file()

    saver_b = open_checkpointer(DAG_ID, workspace=tmp_path)
    compiled_b = _build_resume_graph(flag).compile(
        checkpointer=saver_b,
        interrupt_after=["node1"],
    )
    snap_b = compiled_b.get_state(config)
    assert snap_b is not None
    values_b = snap_b.values
    assert values_b.get("step1_done") is True
    assert values_b.get("step1_runs") == 1

    compiled_b.invoke(None, config)
    final = compiled_b.get_state(config)
    assert final is not None
    assert final.values.get("step2_done") is True
    assert final.values.get("step1_runs") == 1
    assert flag.read_text(encoding="utf-8") == "1"
    _close(saver_b)


def test_gmpstate_sqlite_serde(tmp_path: Path) -> None:
    def stamp(state: GMPState | dict[str, Any]) -> dict[str, Any]:
        task = state["task"] if isinstance(state, dict) else state.task
        return {"task": f"{task}+ckpt"}

    graph = StateGraph(GMPState)
    graph.add_node("stamp", stamp)
    graph.add_edge(START, "stamp")
    graph.add_edge("stamp", END)

    thread_id = "gmp-serde-1"
    config = {"configurable": {"thread_id": thread_id}}
    saver_a = open_checkpointer("gmp-serde", workspace=tmp_path)
    compiled_a = graph.compile(checkpointer=saver_a)
    compiled_a.invoke(GMPState(task="hello", phase=GMPPhase.START), config)
    _close(saver_a)
    del compiled_a
    del saver_a

    saver_b = open_checkpointer("gmp-serde", workspace=tmp_path)
    compiled_b = graph.compile(checkpointer=saver_b)
    snap = compiled_b.get_state(config)
    assert snap is not None
    values = snap.values
    task = values["task"] if isinstance(values, dict) else values.task
    assert task == "hello+ckpt"
    _close(saver_b)


def test_exemplar_packages_are_durable() -> None:
    for rel in ("workflows/dags/gmp", "workflows/dags/intelligence_harvest"):
        package = ROOT / rel
        structural = validate(package / "graph.py")
        assert structural["status"] == "PASS", (rel, structural)
        proof = validate_package(package)
        assert proof["status"] == "PASS", (rel, proof)
        assert proof["persistence_class"] == "durable"

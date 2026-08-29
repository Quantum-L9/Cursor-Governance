"""Emitted harvest StateGraph must match the IR node set and stay off the registry."""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IR_PATH = ROOT / "skills" / "l9-intelligence-harvest" / "meta" / "skill-ir.json"
GRAPH_PATH = ROOT / "workflows" / "dags" / "intelligence_harvest" / "graph.py"
REQUIRED = {
    "BIND_REQUEST",
    "PROBE_CAPABILITIES",
    "LOCK_SOURCE_IDENTITY",
    "INVENTORY_DONOR",
    "RECONSTRUCT_SYSTEM",
    "TRACE_SURFACES",
    "DETECT_DUPLICATION_DRIFT",
    "EXTRACT_CONCEPT_CANDIDATES",
    "QUALIFY_NUGGETS",
    "COMPARE_BENEFICIARY",
    "DISPOSITION_CONCEPTS",
    "DERIVE_ACCEPTANCE_TESTS",
    "RANK_NUGGETS",
    "SAFETY_PORTABILITY_AUDIT",
    "EVIDENCE_CLOSURE",
    "RENDER_OUTPUT",
    "PASS",
    "PARTIAL",
    "BLOCKED",
    "FAIL",
}


def _node_ids(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else None
        if name != "add_node" or not node.args:
            continue
        arg = node.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            found.add(arg.value)
    return found


def test_graph_declares_the_ir_node_set() -> None:
    ir_ids = {n["id"] for n in json.loads(IR_PATH.read_text(encoding="utf-8"))["workflow"]["nodes"]}
    assert _node_ids(GRAPH_PATH) == ir_ids == REQUIRED


def test_builder_source_is_langgraph_and_off_registry() -> None:
    sys.path.insert(0, str(ROOT / "skills" / "l9-dag-authoring" / "scripts"))
    from validate_langgraph_source import validate

    assert validate(GRAPH_PATH)["status"] == "PASS"
    text = GRAPH_PATH.read_text(encoding="utf-8")
    assert "register_session_dag" not in text
    assert "def build_intelligence_harvest_graph" in text
    probe = (
        "import sys, types\n"
        f"root = {str(ROOT)!r}\n"
        "sys.path.insert(0, root)\n"
        "for name, rel in ("
        "('workflows', 'workflows'),"
        "('workflows.dags', 'workflows/dags'),"
        "('workflows.dags.intelligence_harvest', 'workflows/dags/intelligence_harvest'),"
        "):\n"
        "    pkg = types.ModuleType(name)\n"
        "    pkg.__path__ = [root + '/' + rel]\n"
        "    sys.modules[name] = pkg\n"
        "from workflows.dags.intelligence_harvest.graph import build_intelligence_harvest_graph\n"
        "build_intelligence_harvest_graph().compile()\n"
    )
    done = subprocess.run([sys.executable, "-c", probe], cwd=ROOT, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr


def test_session_adapter_still_resolves() -> None:
    adapter = ROOT / "workflows" / "dags" / "intelligence_harvest_dag.py"
    text = adapter.read_text(encoding="utf-8")
    assert "register_session_dag" in text
    assert 'id="intelligence-harvest-v1"' in text or "intelligence-harvest-v1" in text

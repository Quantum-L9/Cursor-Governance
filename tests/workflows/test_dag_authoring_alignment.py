"""Alignment between the l9-dag-authoring control plane and the workflows runtime.

The Skill owns graph lifecycle mechanics; `workflows/` owns implementation and
execution. These tests pin the seam that used to contradict itself: the package
docstring called SessionDAG and LangGraph "two complementary systems" while the
discovery boundary called SessionDAG "fake" and "legacy".

Two graph kinds are first-class here. Neither is a generation of the other.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL = REPO_ROOT / "skills" / "l9-dag-authoring"
SCRIPTS = SKILL / "scripts"

sys.path.insert(0, str(SCRIPTS))

from classify_graph_kind import classify  # noqa: E402
from validate_command_trigger import validate as validate_command  # noqa: E402
from validate_langgraph_source import validate as validate_langgraph  # noqa: E402
from validate_session_dag_source import validate as validate_session  # noqa: E402

DAG_AUTHORING_SOURCE = REPO_ROOT / "workflows" / "dags" / "dag_authoring_dag.py"
DISCOVERY_BOUNDARY = REPO_ROOT / "workflows" / "dags" / "__init__.py"
PACKAGE_INIT = REPO_ROOT / "workflows" / "__init__.py"
COMMAND = REPO_ROOT / "commands" / "dag-authoring.md"


# --------------------------------------------------------------------------
# Graph-kind classification
# --------------------------------------------------------------------------


def test_session_guidance_classification(tmp_path):
    source = tmp_path / "guidance.py"
    source.write_text(
        "from workflows.session.interface import SessionDAG\n"
        "from workflows.session.registry import register_session_dag\n"
        "D = SessionDAG(id='d', name='D', version='1', description='', nodes=[], edges=[])\n"
        "register_session_dag(D)\n",
        encoding="utf-8",
    )
    result = classify(source)
    assert result["status"] == "PASS"
    assert result["graph_kind"] == "SESSION_GUIDANCE"


def test_langgraph_runtime_classification(tmp_path):
    source = tmp_path / "runtime.py"
    source.write_text(
        "from langgraph.graph import StateGraph\ndef build():\n    return StateGraph(dict)\n",
        encoding="utf-8",
    )
    result = classify(source)
    assert result["status"] == "PASS"
    assert result["graph_kind"] == "LANGGRAPH_RUNTIME"


def test_mixed_kind_blocks(tmp_path):
    """Both kinds constructed in one module is unresolvable, not a judgement call."""
    source = tmp_path / "mixed.py"
    source.write_text(
        "from langgraph.graph import StateGraph\n"
        "from workflows.session.interface import SessionDAG\n"
        "G = StateGraph(dict)\n"
        "D = SessionDAG(id='d', name='D', version='1', description='', nodes=[], edges=[])\n",
        encoding="utf-8",
    )
    result = classify(source)
    assert result["status"] == "BLOCKED"
    assert result["graph_kind"] == "UNKNOWN"


def test_documenting_the_other_kind_does_not_block(tmp_path):
    """A SessionDAG that *documents* runtime validation is still SESSION_GUIDANCE.

    Regression pin for the real reason classification reads the AST. The authoring
    graph's own job is to describe both kinds, so a raw-substring classifier
    reports it as mixed and blocks the one file the Skill most needs to classify.
    """
    source = tmp_path / "documents_both.py"
    source.write_text(
        "from workflows.session.interface import SessionDAG, SessionNode\n"
        "from workflows.session.registry import register_session_dag\n"
        "D = SessionDAG(\n"
        "    id='d', name='D', version='1',\n"
        "    description='Never register a StateGraph from langgraph.graph here.',\n"
        "    nodes=[], edges=[],\n"
        ")\n"
        "register_session_dag(D)\n",
        encoding="utf-8",
    )
    assert classify(source)["graph_kind"] == "SESSION_GUIDANCE"


def test_authoring_graph_classifies_as_session_guidance():
    """The live artifact, not a fixture."""
    result = classify(DAG_AUTHORING_SOURCE)
    assert result["status"] == "PASS"
    assert result["graph_kind"] == "SESSION_GUIDANCE"


# --------------------------------------------------------------------------
# SessionDAG: validate -> register -> discover -> lookup
# --------------------------------------------------------------------------


def test_session_dag_source_is_structurally_valid():
    result = validate_session(DAG_AUTHORING_SOURCE)
    assert result["status"] == "PASS", result["errors"]
    assert result["dag_symbols"] == ["DAG_AUTHORING_DAG"]


def test_session_dag_validate_register_discover_lookup():
    """Discovery is a separate proof obligation from constructing the object."""
    pytest.importorskip("structlog")
    import workflows.dags  # noqa: F401  — import is the discovery mechanism
    from workflows.session.registry import get_session_dag

    dag = get_session_dag("dag-authoring-v1")
    assert dag is not None, "authoring graph not reachable through the registry"
    assert dag.validate() == []

    node_ids = [node.id for node in dag.nodes]
    assert len(node_ids) == len(set(node_ids)), "duplicate node ids"
    dangling = [
        (edge.from_node, edge.to_node)
        for edge in dag.edges
        if edge.from_node not in set(node_ids) or edge.to_node not in set(node_ids)
    ]
    assert not dangling, dangling


def test_authoring_graph_classifies_kind_before_authoring():
    """Graph kind is resolved first, and UNKNOWN has somewhere to go."""
    pytest.importorskip("structlog")
    import workflows.dags  # noqa: F401
    from workflows.session.registry import get_session_dag

    dag = get_session_dag("dag-authoring-v1")
    assert dag is not None

    first = dag.get_next_nodes(dag.entry_node)
    assert first == ["classify_graph_kind"], first

    node_ids = {node.id for node in dag.nodes}
    assert {"gate_graph_kind", "blocked_unknown_kind"} <= node_ids
    # Both kinds have their own validation path.
    assert {"validate_session_dag", "validate_langgraph"} <= node_ids
    # Registration belongs to exactly one of them.
    assert "register_and_discover" in node_ids
    assert "prove_runtime_entrypoint" in node_ids


def test_registry_has_no_get_dag():
    """The authoring graph used to instruct agents to import a symbol that never existed."""
    pytest.importorskip("structlog")
    from workflows.session import registry

    assert not hasattr(registry, "get_dag")
    assert hasattr(registry, "get_session_dag")

    text = DAG_AUTHORING_SOURCE.read_text(encoding="utf-8")
    # The defect was instruction text telling agents to import a symbol that does
    # not exist. Naming get_dag() to say it does not exist is the correction, not
    # a recurrence — so pin the import and the call, not the mention.
    assert "import get_dag" not in text
    assert "= get_dag(" not in text
    assert "get_session_dag" in text


# --------------------------------------------------------------------------
# LangGraph runtime never touches the SessionDAG registry
# --------------------------------------------------------------------------


def test_langgraph_does_not_use_session_registry(tmp_path):
    contaminated = tmp_path / "bad.py"
    contaminated.write_text(
        "from langgraph.graph import StateGraph\n"
        "from workflows.session.registry import register_session_dag\n"
        "def build():\n"
        "    return StateGraph(dict)\n",
        encoding="utf-8",
    )
    result = validate_langgraph(contaminated)
    assert result["status"] == "FAIL"
    assert any("session_registry" in error for error in result["errors"])


def test_langgraph_may_document_the_boundary(tmp_path):
    """Naming the registry to forbid it is documenting the boundary, not crossing it."""
    source = tmp_path / "documented.py"
    source.write_text(
        '"""Runtime graph. Never call register_session_dag() from here."""\n'
        "from langgraph.graph import StateGraph\n"
        "def build():\n"
        "    return StateGraph(dict)\n",
        encoding="utf-8",
    )
    assert validate_langgraph(source)["status"] == "PASS"


def test_repo_langgraph_runtimes_stay_out_of_the_registry():
    """The live LangGraph graphs are absent from the SessionDAG registry by design."""
    pytest.importorskip("structlog")
    import workflows.dags  # noqa: F401
    from workflows.session.registry import list_session_dags

    registered = {entry["id"] for entry in list_session_dags()}
    for runtime_id in ("inspect-v1", "inspect", "gmp-langgraph"):
        assert runtime_id not in registered

    for runtime in ("inspect_dag.py", "gmp/graph.py"):
        source = REPO_ROOT / "workflows" / "dags" / runtime
        assert classify(source)["graph_kind"] == "LANGGRAPH_RUNTIME"
        assert validate_langgraph(source)["status"] == "PASS", runtime


# --------------------------------------------------------------------------
# Taxonomy: the two surfaces must agree
# --------------------------------------------------------------------------


def test_discovery_boundary_drops_fake_and_legacy_language():
    text = DISCOVERY_BOUNDARY.read_text(encoding="utf-8")
    docstring = ast.get_docstring(ast.parse(text)) or ""
    lowered = docstring.lower()
    assert "neither is a legacy" in lowered or "legacy generation" in lowered
    # The claim being retired: SessionDAG as a fake awaiting migration.
    assert "fake dataclass" not in lowered
    assert "to be migrated" not in lowered
    assert "SESSION_GUIDANCE" in docstring
    assert "LANGGRAPH_RUNTIME" in docstring


def test_package_docstring_declares_both_kinds():
    docstring = ast.get_docstring(ast.parse(PACKAGE_INIT.read_text(encoding="utf-8"))) or ""
    assert "SESSION_GUIDANCE" in docstring
    assert "LANGGRAPH_RUNTIME" in docstring
    # SessionDAG definitions live in workflows/dags, not workflows/session/dags.
    assert "workflows/session/dags" not in docstring


def test_discovery_boundary_exports_are_grouped_by_kind():
    text = DISCOVERY_BOUNDARY.read_text(encoding="utf-8")
    assert "# SESSION_GUIDANCE" in text
    assert "# LANGGRAPH_RUNTIME" in text
    assert "Legacy (to be migrated)" not in text


def test_discovery_boundary_still_registers_every_session_dag():
    """Taxonomy edits must not change discovery behavior."""
    pytest.importorskip("structlog")
    import workflows.dags
    from workflows.session.registry import list_session_dags

    registered = {entry["id"] for entry in list_session_dags()}
    assert "dag-authoring-v1" in registered
    assert len(registered) >= 9
    for symbol in ("DAG_AUTHORING_DAG", "INSPECT_DAG", "WIRE_DAG"):
        assert symbol in workflows.dags.__all__


# --------------------------------------------------------------------------
# Command binding stays a thin trigger
# --------------------------------------------------------------------------


def test_command_trigger_uses_canonical_path():
    result = validate_command(COMMAND, "dag-authoring-v1")
    assert result["status"] == "PASS", result["errors"]
    assert result["line_count"] <= 80


def test_command_trigger_rejects_stale_cursor_commands_path(tmp_path):
    stale = tmp_path / "stale.md"
    stale.write_text(
        "---\ndag: dag-authoring-v1\n"
        "dag_file: .cursor-commands/workflows/dags/dag_authoring_dag.py\n---\n",
        encoding="utf-8",
    )
    result = validate_command(stale, "dag-authoring-v1")
    assert result["status"] == "FAIL"
    assert any("stale" in error for error in result["errors"])


# --------------------------------------------------------------------------
# Subsystem README states the same taxonomy as the code
# --------------------------------------------------------------------------


def test_workflows_readme_points_at_the_real_tree():
    """The README documented workflows/session/dags/, which has never existed."""
    text = (REPO_ROOT / "workflows" / "README.md").read_text(encoding="utf-8")
    layout = text.split("## Directory Layout")[1].split("```")[1]
    assert "session/dags/" not in layout
    assert "dags/" in layout

    for path in ("workflows/dags", "workflows/session/interface.py"):
        assert (REPO_ROOT / path).exists()
    assert not (REPO_ROOT / "workflows" / "session" / "dags").exists()


def test_workflows_readme_declares_both_graph_kinds():
    text = (REPO_ROOT / "workflows" / "README.md").read_text(encoding="utf-8")
    assert "SESSION_GUIDANCE" in text
    assert "LANGGRAPH_RUNTIME" in text


def test_workflows_readme_does_not_claim_an_absent_generator():
    """workflows/README.md stays handwritten; the generator is wired for others."""
    text = (REPO_ROOT / "workflows" / "README.md").read_text(encoding="utf-8")
    front = text.split("---")[1]
    assert "auto_generated: false" in front
    assert "generator_present: true" in front
    assert (REPO_ROOT / "scripts" / "generate_subsystem_readmes.py").is_file()
    assert (REPO_ROOT / "config" / "subsystems" / "readme_config.yaml").is_file()

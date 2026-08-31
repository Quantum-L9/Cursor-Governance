"""plan-simple-build-v1 is a SESSION_GUIDANCE composition, not a new skill."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_SCRIPTS = REPO_ROOT / "skills" / "l9-dag-authoring" / "scripts"
DAG_SOURCE = REPO_ROOT / "workflows" / "dags" / "plan_simple_build_dag.py"
COMMAND = REPO_ROOT / "commands" / "l9-plan-build.md"

sys.path.insert(0, str(SKILL_SCRIPTS))

from classify_graph_kind import classify  # noqa: E402
from validate_command_trigger import validate as validate_command  # noqa: E402
from validate_session_dag_source import validate as validate_session  # noqa: E402

DOMAIN_ACTIONS = {
    "plan_simple": "skills/l9-plan-simple/SKILL.md",
    "improve": "kernels/Improve.md",
    "validate_repair": "kernels/Validate & Repair.md",
    "build": "skills/l9-plan-simple/references/plan-workflow-simple.md",
    "gmp_start": "workflows/gmp_executor.py",
    "gmp_finalize": "workflows/gmp_executor.py",
    "kernel_receipt": "skills/l9-plan/scripts/validate_plan_kernel_receipt.py",
    "validate_plan": "skills/l9-plan/scripts/validate_plan_document.py",
    "generate_section_receipt": ("skills/l9-plan-simple/scripts/generate_plan_section_receipt.py"),
    "validate_section_receipt": ("skills/l9-plan-simple/scripts/validate_plan_section_receipt.py"),
}


def test_classifies_as_session_guidance() -> None:
    result = classify(DAG_SOURCE)
    assert result["status"] == "PASS"
    assert result["graph_kind"] == "SESSION_GUIDANCE"


def test_source_is_structurally_valid() -> None:
    result = validate_session(DAG_SOURCE)
    assert result["status"] == "PASS", result["errors"]
    assert result["dag_symbols"] == ["PLAN_SIMPLE_BUILD_DAG"]


def test_registered_and_structurally_valid() -> None:
    pytest.importorskip("structlog")
    import workflows.dags  # noqa: F401
    from workflows.dags.plan_simple_build_dag import PLAN_SIMPLE_BUILD_DAG
    from workflows.session.registry import get_session_dag

    dag = get_session_dag("plan-simple-build-v1")
    assert dag is PLAN_SIMPLE_BUILD_DAG
    assert dag.validate() == []
    assert dag.entry_node == "start"


def test_composition_order() -> None:
    pytest.importorskip("structlog")
    from workflows.dags.plan_simple_build_dag import PLAN_SIMPLE_BUILD_DAG

    dag = PLAN_SIMPLE_BUILD_DAG
    assert dag.get_next_nodes("start") == ["plan_simple"]
    assert dag.get_next_nodes("plan_simple") == ["validate_plan"]
    assert dag.get_next_nodes("validate_plan") == ["generate_section_receipt"]
    assert dag.get_next_nodes("generate_section_receipt") == ["validate_section_receipt"]
    assert dag.get_next_nodes("validate_section_receipt") == ["gate_plan"]
    assert "improve" in dag.get_next_nodes("gate_plan", condition="passed")
    assert dag.get_next_nodes("improve") == ["validate_repair"]
    assert "gmp_start" in dag.get_next_nodes("gate_kernel", condition="passed")
    assert dag.get_next_nodes("gmp_start") == ["build"]
    assert dag.get_next_nodes("build") == ["gmp_finalize"]


def test_domain_actions_are_existing_repo_paths() -> None:
    pytest.importorskip("structlog")
    from workflows.dags.plan_simple_build_dag import PLAN_SIMPLE_BUILD_DAG

    by_id = {node.id: node for node in PLAN_SIMPLE_BUILD_DAG.nodes}
    for node_id, rel in DOMAIN_ACTIONS.items():
        assert by_id[node_id].action == rel
        assert (REPO_ROOT / rel).is_file(), rel


def test_gmp_start_argv_supplies_plan_and_task() -> None:
    pytest.importorskip("structlog")
    from workflows.dags.plan_simple_build_dag import PLAN_SIMPLE_BUILD_DAG

    node = next(item for item in PLAN_SIMPLE_BUILD_DAG.nodes if item.id == "gmp_start")
    argv = list(node.metadata["argv"])
    plan_at = argv.index("--plan")
    assert plan_at + 2 < len(argv)
    assert argv[plan_at + 1] != "--plan"
    assert argv[plan_at + 1].startswith("<")
    assert argv[plan_at + 2].startswith("<")


def test_does_not_restate_gmp_phases_or_wire_campaign() -> None:
    text = DAG_SOURCE.read_text(encoding="utf-8")
    assert "make campaign" not in text
    assert "Phase 0" not in text
    assert "TODO PLAN (LOCKED)" not in text


def test_gates_have_explicit_outcomes() -> None:
    pytest.importorskip("structlog")
    from workflows.dags.plan_simple_build_dag import PLAN_SIMPLE_BUILD_DAG

    for gate_id, outcomes in (
        ("gate_plan", {"passed", "failed", "blocked"}),
        ("gate_kernel", {"passed", "failed", "blocked"}),
        ("gate_execute", {"passed", "failed", "abort"}),
    ):
        conditions = {
            edge.condition for edge in PLAN_SIMPLE_BUILD_DAG.edges if edge.from_node == gate_id
        }
        assert conditions == outcomes, gate_id


def test_every_node_is_reachable() -> None:
    pytest.importorskip("structlog")
    from workflows.dags.plan_simple_build_dag import PLAN_SIMPLE_BUILD_DAG

    seen: set[str] = set()
    queue = [PLAN_SIMPLE_BUILD_DAG.entry_node]
    while queue:
        current = queue.pop()
        if current in seen:
            continue
        seen.add(current)
        queue.extend(PLAN_SIMPLE_BUILD_DAG.get_next_nodes(current))
    assert seen == {node.id for node in PLAN_SIMPLE_BUILD_DAG.nodes}


def test_build_records_missing_build_kernel_as_intended() -> None:
    pytest.importorskip("structlog")
    from workflows.dags.plan_simple_build_dag import PLAN_SIMPLE_BUILD_DAG

    build = next(node for node in PLAN_SIMPLE_BUILD_DAG.nodes if node.id == "build")
    assert build.action == "skills/l9-plan-simple/references/plan-workflow-simple.md"
    assert build.metadata["intended_kernel"] == "kernels/Build.md"
    assert build.metadata["execute_via"] == "cursor-build"


def test_command_is_a_thin_trigger() -> None:
    result = validate_command(COMMAND, "plan-simple-build-v1")
    assert result["status"] == "PASS", result["errors"]
    assert result["line_count"] <= 80

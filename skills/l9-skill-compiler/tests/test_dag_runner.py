# ruff: noqa: E402
"""The runner derives order, guards, and terminal state from the canonical DAG."""

import importlib.util
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "scripts")
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
RUNNER_PATH = os.path.join(REPO, "workflows", "dags", "skill_compiler_runner.py")


def _runner():
    spec = importlib.util.spec_from_file_location("skill_compiler_runner_test", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


runner = _runner()
dag, dag_source, degradation = runner.load_canonical_dag()


def test_canonical_dag_resolves_and_validates():
    assert dag.SKILL_COMPILER_V2["id"] == "skill-compiler-v2"
    assert dag.validate_graph() == []


def test_degraded_load_is_reported_not_hidden():
    # Either the package import worked, or the fallback named why it did not.
    assert (dag_source == "package_import") == (degradation is None)
    if degradation is not None:
        assert degradation["id"] == "canonical_package_import_unavailable"
        assert runner.CANONICAL_DAG_PATH in degradation["resolution"]


def test_execution_order_covers_the_reachable_graph_and_respects_edges():
    entry = dag.SKILL_COMPILER_V2["entrypoint"]
    order = runner.execution_order(dag.NODES, entry)
    assert set(order) == runner.reachable(dag.NODES, entry)
    position = {node_id: index for index, node_id in enumerate(order)}
    for node in dag.NODES:
        for target in node.get("next", []):
            if node["id"] in position and target in position:
                assert position[node["id"]] < position[target]


def test_runner_holds_no_stage_list_of_its_own():
    with open(RUNNER_PATH, encoding="utf-8") as handle:
        source = handle.read()
    for node in dag.NODES:
        exec_path = node.get("exec")
        if exec_path:
            assert os.path.basename(exec_path) not in source


def test_every_executable_node_declares_its_invocation_shape():
    for node in dag.NODES:
        if node.get("exec"):
            assert node["args"], node["id"]
            assert isinstance(node["writes"], bool), node["id"]
            for token in node["args"]:
                assert token in dag.ARG_TOKENS


def test_guarded_nodes_are_machine_evaluable():
    guarded = [node for node in dag.NODES if node.get("guard")]
    assert guarded
    ids = {node["id"] for node in dag.NODES}
    for node in guarded:
        guard = node["guard_when"]
        assert guard["stage"] in ids
        assert guard["field"] and guard["equals"]


def test_guard_only_fires_on_its_declared_stage_output():
    node = next(item for item in dag.NODES if item["id"] == "TOPOLOGY_OWNERSHIP_JUDGMENT")
    assert runner._guard_satisfied(node, {}) is False
    assert (
        runner._guard_satisfied(
            node, {"SCAN_SKILL_TOPOLOGY": {"decision": "ESCALATE_TO_BOUNDED_LLM"}}
        )
        is True
    )
    assert (
        runner._guard_satisfied(node, {"SCAN_SKILL_TOPOLOGY": {"decision": "CREATE_NEW"}}) is False
    )


def test_terminal_state_table_never_calls_a_dry_run_a_build():
    assert dag.TERMINAL_STATES["DRY_RUN"]["build_succeeded"] is False
    assert dag.TERMINAL_STATES["BOUNDED_LLM_REQUIRED"]["status"] == "BLOCKED"
    assert dag.TERMINAL_STATES["PASS"]["build_succeeded"] is True


def test_unresolved_required_input_halts_instead_of_defaulting():
    context = runner.RunContext(request=None, repo_root=REPO)
    node = next(item for item in dag.NODES if item["id"] == "BIND_INPUTS")
    commands, problem = runner._stage_commands(node, context, sys.executable)
    assert commands is None
    assert "request" in problem


def test_compiler_self_test_passes():
    completed = subprocess.run(
        [sys.executable, os.path.join(SCRIPTS, "self_test.py")],
        capture_output=True,
        text=True,
        cwd=REPO,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr

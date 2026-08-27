#!/usr/bin/env python3
# Compiler self-host validation. Runs the compiler against its own pack.
import ast
import contextlib
import importlib.util
import json
import os
import sys

import check_capability_closure
import classify_skill_profile
import evaluate_activation
import normalize_skill_ir
import render_target_profile
import scan_skill_topology
import static_validate
from _common import PACK, emit

IR = os.path.join(str(PACK), "tests", "fixtures", "self-ir.json")
REPO_FIXTURE = os.path.join(str(PACK), "tests", "fixtures", "repo", "skills")
LIVE_SKILLS = {
    "l9-dag-authoring",
    "l9-structured-reasoning",
    "l9-wire-skill-into-repo",
}
CLI = os.path.join(str(PACK), "scripts", "compile_skill.py")
RUNNER = os.path.join(str(PACK.parent.parent), "workflows", "dags", "skill_compiler_runner.py")
# Stage modules the operator CLI must never import: importing them would let it
# sequence compilation itself instead of invoking the DAG.
STAGE_MODULES = {
    "bind_inputs",
    "scan_skill_topology",
    "classify_skill_profile",
    "normalize_skill_ir",
    "render_target_profile",
    "static_validate",
    "check_capability_closure",
    "evaluate_activation",
    "package_skill",
}


def _load_runner():
    spec = importlib.util.spec_from_file_location("skill_compiler_runner_selftest", RUNNER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    # Registering the DAG logs; keep that off this harness's result stream.
    with contextlib.redirect_stdout(sys.stderr):
        spec.loader.exec_module(module)
    return module


def cli_imports():
    """Module names the operator CLI imports, read statically from its source."""
    with open(CLI, encoding="utf-8") as handle:
        tree = ast.parse(handle.read(), CLI)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def _load_ir():
    with open(IR, encoding="utf-8") as handle:
        return json.load(handle)


def run():
    steps = []
    ir = normalize_skill_ir.normalize(_load_ir())
    steps.append(("normalize_skill_ir.validate", not normalize_skill_ir.validate(ir)))
    steps.append(("normalize_skill_ir.round_trip", normalize_skill_ir.round_trip(ir)))

    static_exit = static_validate.main(["self_test", IR, str(PACK)])
    steps.append(("static_validate", static_exit == 0))

    closure = check_capability_closure.check(
        ir,
        str(PACK.parent.parent),
        live_skills=LIVE_SKILLS,
    )
    steps.append(("capability_closure", closure["result"] in ("CLOSED", "RUNTIME_BOUND")))

    activation = evaluate_activation.evaluate(ir, live_skills=LIVE_SKILLS)
    steps.append(("activation_eval", activation["status"] == "PASS"))

    portable = render_target_profile.render(ir, "portable")
    l9_profile = render_target_profile.render(ir, "l9")
    steps.append(
        (
            "deterministic_render",
            portable == render_target_profile.render(ir, "portable"),
        )
    )
    steps.append(
        (
            "profile_specific_validation",
            "Canonical DAG" in l9_profile and "Canonical DAG" not in portable,
        )
    )

    gated = False
    try:
        render_target_profile.render(ir, "cursor")
    except PermissionError:
        gated = True
    steps.append(("unverified_profile_is_gated", gated))

    profile = classify_skill_profile.classify("rebuild a compiler that renders skill artifacts")
    steps.append(("classification_compiler", profile["primary_family"] == "compiler"))

    runner = _load_runner()
    dag, _, _ = runner.load_canonical_dag()
    steps.append(
        ("dag_runner_resolves_canonical_graph", dag.SKILL_COMPILER_V2["id"] == "skill-compiler-v2")
    )
    order = runner.execution_order(dag.NODES, dag.SKILL_COMPILER_V2["entrypoint"])
    reachable = runner.reachable(dag.NODES, dag.SKILL_COMPILER_V2["entrypoint"])
    position = {node_id: index for index, node_id in enumerate(order)}
    edges_respected = all(
        position[node["id"]] < position[target]
        for node in dag.NODES
        if node["id"] in position
        for target in node.get("next", [])
        if target in position
    )
    steps.append(
        (
            "execution_order_derived_from_graph",
            set(order) == reachable and edges_respected and not dag.validate_graph(),
        )
    )
    steps.append(
        (
            "terminal_state_mapping_exists",
            set(dag.TERMINAL_STATES) >= {"PASS", "BLOCKED", "FAIL", "DRY_RUN"}
            and dag.TERMINAL_STATES["DRY_RUN"]["build_succeeded"] is False
            and dag.TERMINAL_STATES["PASS"]["build_succeeded"] is True,
        )
    )
    steps.append(("operator_cli_is_executable", os.path.isfile(CLI) and os.access(CLI, os.X_OK)))
    steps.append(
        ("operator_cli_does_not_import_stage_modules", not (cli_imports() & STAGE_MODULES))
    )

    live = scan_skill_topology.enumerate_live_skills(REPO_FIXTURE)
    decision, _, _, _ = scan_skill_topology.decide(
        {
            "proposed_name": "l9-skill-compiler",
            "existing_skill": "l9-skill-compiler",
        },
        live,
    )
    steps.append(("topology_replace_existing", decision == "REPLACE_EXISTING"))
    return steps, closure, activation


def main(argv):
    del argv
    steps, closure, activation = run()
    failed = [name for name, ok in steps if not ok]
    return emit(
        {
            "stage": "SELF_TEST",
            "status": "FAIL" if failed else "PASS",
            "checks": [{"id": name, "status": "pass" if ok else "fail"} for name, ok in steps],
            "failed": failed,
            "capability_closure_result": closure["result"],
            "activation_status": activation["status"],
        },
        2 if failed else 0,
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv))

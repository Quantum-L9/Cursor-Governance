# ruff: noqa: E402
"""Operator CLI behavior: normalization, typed failures, and DAG invocation."""

import ast
import importlib.util
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "scripts")
sys.path.insert(0, SCRIPTS)

import compile_skill as cli

FIX = os.path.join(HERE, "fixtures")
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CLI_PATH = os.path.join(SCRIPTS, "compile_skill.py")


def _write_capable_nodes():
    """Node ids the DAG itself marks as write-capable."""
    runner_path = os.path.join(REPO, "workflows", "dags", "skill_compiler_runner.py")
    spec = importlib.util.spec_from_file_location("skill_compiler_runner_cli_test", runner_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    dag, _, _ = module.load_canonical_dag()
    return {node["id"] for node in dag.NODES if node.get("writes")}


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


def parse(argv):
    return cli.build_parser().parse_args(argv)


def normalize(argv):
    return cli.normalize_request(parse(argv))[0]


def invoke(argv):
    """Run the CLI as an operator would and return (exit_code, machine_output)."""
    completed = subprocess.run(
        [sys.executable, CLI_PATH, *argv, "--output-json"],
        capture_output=True,
        text=True,
        cwd=REPO,
        check=False,
    )
    try:
        payload = json.loads(completed.stdout)
    except ValueError:
        payload = None
    return completed.returncode, payload, completed.stderr


# --------------------------------------------------------------------------
# normalization
# --------------------------------------------------------------------------


def test_optimize_normalizes_to_evolve_intent():
    request = normalize(["optimize", "l9-skill-compiler"])
    assert request["intent"] == "evolve"
    assert request["subject"]["existing_skill"] == "l9-skill-compiler"
    assert request["subject"]["proposed_name"] == "l9-skill-compiler"


def test_rebuild_normalizes_to_rebuild_intent():
    request = normalize(["rebuild", "skills/l9-skill-compiler"])
    assert request["intent"] == "rebuild"
    assert request["subject"]["existing_skill"] == "l9-skill-compiler"


def test_create_generates_canonical_request_from_source():
    source = os.path.join(FIX, "compile-request.valid.json")
    request = normalize(["create", "--name", "l9-demo-skill", "--source", source])
    assert request["intent"] == "create"
    assert request["subject"]["proposed_name"] == "l9-demo-skill"
    assert request["subject"]["existing_skill"] is None
    assert request["source_material"] == [{"kind": "file", "ref": source}]


def test_default_profiles_include_portable_and_l9():
    request = normalize(["optimize", "l9-skill-compiler"])
    assert request["target_profiles"] == ["portable", "l9"]


def test_json_and_yaml_requests_normalize_identically():
    from_json = normalize(["compile", os.path.join(FIX, "compile-request.valid.json")])
    from_yaml = normalize(["compile", os.path.join(FIX, "compile-request.valid.yaml")])
    assert from_json == from_yaml


def test_yaml_is_input_only_and_has_no_second_schema():
    contracts = os.listdir(os.path.join(HERE, "..", "contracts"))
    assert not [name for name in contracts if "yaml" in name.lower()]


# --------------------------------------------------------------------------
# typed failures
# --------------------------------------------------------------------------


def _error(argv):
    try:
        normalize(argv)
    except cli.OperatorError as exc:
        return exc
    raise AssertionError("expected an OperatorError for " + " ".join(argv))


def test_unknown_skill_fails_cleanly():
    exc = _error(["optimize", "l9-no-such-skill-exists"])
    assert exc.code == "SKILL_NOT_FOUND"
    assert cli.ERRORS[exc.code][0] == 2


def test_missing_source_fails_cleanly():
    exc = _error(["create", "--name", "l9-demo", "--source", "/nonexistent/path"])
    assert exc.code == "SOURCE_NOT_FOUND"


def test_malformed_yaml_fails_cleanly(tmp_path):
    # Written at run time rather than committed: a file the repository's own
    # check-yaml hook cannot parse has no business sitting in the tree.
    broken = tmp_path / "compile-request.malformed.yaml"
    broken.write_text("request_id: broken\nintent: [rebuild\nsubject:\n  proposed_name: x\n")
    exc = _error(["compile", str(broken)])
    assert exc.code == "REQUEST_PARSE_FAILED"


def test_missing_request_file_fails_cleanly():
    exc = _error(["compile", os.path.join(FIX, "no-such-request.json")])
    assert exc.code == "REQUEST_PARSE_FAILED"


def test_every_error_class_has_an_exit_code():
    expected = {
        "INVALID_ARGUMENTS",
        "REQUEST_PARSE_FAILED",
        "REQUEST_SCHEMA_INVALID",
        "SOURCE_NOT_FOUND",
        "SKILL_NOT_FOUND",
        "TOPOLOGY_BLOCKED",
        "DAG_NOT_AVAILABLE",
        "DAG_EXECUTION_FAILED",
        "COMPILATION_BLOCKED",
        "COMPILATION_FAILED",
        "VALIDATION_FAILED",
        "UNKNOWN",
    }
    assert expected <= set(cli.ERRORS)
    assert {code: value[0] for code, value in cli.ERRORS.items()}["VALIDATION_FAILED"] == 5


def test_schema_invalid_request_is_rejected_by_the_canonical_schema():
    code, payload, _ = invoke(
        ["compile", os.path.join(FIX, "compile-request.invalid.json"), "--dry-run"]
    )
    assert code == 2
    assert payload["error_code"] == "REQUEST_SCHEMA_INVALID"


def test_yaml_unknown_key_fails_closed_against_the_canonical_schema():
    code, payload, _ = invoke(
        ["compile", os.path.join(FIX, "compile-request.unknown-key.yaml"), "--dry-run"]
    )
    assert code == 2
    assert payload["error_code"] == "REQUEST_SCHEMA_INVALID"


# --------------------------------------------------------------------------
# DAG invocation and dry-run
# --------------------------------------------------------------------------


def test_cli_invokes_the_registered_dag():
    code, payload, _ = invoke(["optimize", "l9-skill-compiler", "--dry-run"])
    assert code == 0
    assert payload["dag"]["id"] == "skill-compiler-v2"
    assert payload["dag"]["planned_order"][0] == "COMPILE_REQUEST"
    executed = {stage["node"] for stage in payload["stages"] if stage["status"] == "pass"}
    assert {"BIND_INPUTS", "SCAN_SKILL_TOPOLOGY", "CLASSIFY_SKILL_PROFILE"} <= executed


def test_topology_decision_comes_from_the_compiler_not_the_verb():
    code, payload, _ = invoke(
        ["create", "--name", "l9-skill-compiler", "--source", FIX, "--dry-run"]
    )
    assert code == 0
    # The operator typed `create`; the compiler still owns the ownership call.
    assert payload["intent"] == "create"
    assert payload["topology_decision"]["decision"] != "CREATE_NEW"


def test_dry_run_reports_a_plan_and_never_a_build():
    code, payload, _ = invoke(["optimize", "l9-skill-compiler", "--dry-run"])
    assert code == 0
    assert payload["dag"]["terminal_state"] == "DRY_RUN"
    assert payload["build_succeeded"] is False


def test_dry_run_mutates_nothing_in_the_repository():
    before = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        capture_output=True,
        text=True,
        cwd=REPO,
        check=False,
    ).stdout
    invoke(["optimize", "l9-skill-compiler", "--dry-run"])
    invoke(["compile", os.path.join(FIX, "compile-request.valid.yaml"), "--dry-run"])
    after = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        capture_output=True,
        text=True,
        cwd=REPO,
        check=False,
    ).stdout
    assert before == after


def test_dry_run_skips_every_write_capable_stage():
    code, payload, _ = invoke(
        [
            "compile",
            os.path.join(FIX, "compile-request.valid.json"),
            "--ir",
            os.path.join(FIX, "self-ir.json"),
            "--dry-run",
        ]
    )
    assert code == 0
    write_nodes = _write_capable_nodes()
    assert write_nodes, "the DAG declares no write-capable node to check"
    statuses = {stage["node"]: stage["status"] for stage in payload["stages"]}
    # Every write-capable node was reached and every one of them was skipped.
    assert write_nodes <= set(statuses)
    for node in sorted(write_nodes):
        assert statuses[node] == "skipped_dry_run_would_write", node
    assert payload["artifacts"] == []


def test_bounded_llm_stage_blocks_instead_of_claiming_success(tmp_path):
    code, payload, _ = invoke(
        [
            "compile",
            os.path.join(FIX, "compile-request.valid.json"),
            "--ir",
            os.path.join(FIX, "self-ir.json"),
            "--output-dir",
            str(tmp_path),
        ]
    )
    assert code == 3
    assert payload["status"] == "BLOCKED"
    assert payload["build_succeeded"] is False
    assert [item["node"] for item in payload["pending_bounded_llm"]] == ["BEHAVIOR_EVAL"]
    passed = {stage["node"] for stage in payload["stages"] if stage["status"] == "pass"}
    assert {
        "NORMALIZE_SKILL_IR",
        "STATIC_VALIDATE",
        "CAPABILITY_CLOSURE",
        "ACTIVATION_EVAL",
    } <= passed


def test_machine_output_carries_the_required_fields():
    code, payload, _ = invoke(["optimize", "l9-skill-compiler", "--dry-run"])
    assert code == 0
    for field in (
        "request_id",
        "command",
        "intent",
        "normalized_request",
        "topology_decision",
        "skill_profile",
        "dag",
        "receipt",
        "artifacts",
        "unknowns",
        "errors",
        "status",
    ):
        assert field in payload, field
    assert payload["dag"]["id"] == "skill-compiler-v2"


def test_receipt_path_never_claims_an_unfinished_build(tmp_path):
    receipt = tmp_path / "receipt.json"
    code, payload, _ = invoke(
        ["optimize", "l9-skill-compiler", "--dry-run", "--receipt-path", str(receipt)]
    )
    assert code == 0
    assert receipt.is_file()
    assert payload["receipt"]["build_receipt_complete"] is False


# --------------------------------------------------------------------------
# no parallel runtime
# --------------------------------------------------------------------------


def test_cli_never_imports_a_compilation_stage():
    with open(CLI_PATH, encoding="utf-8") as handle:
        tree = ast.parse(handle.read(), CLI_PATH)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert not imported & STAGE_MODULES


def test_cli_declares_no_stage_sequence_of_its_own():
    with open(CLI_PATH, encoding="utf-8") as handle:
        source = handle.read()
    # Naming a stage script path inside the CLI would mean it can invoke a stage
    # directly; only the DAG may hold those paths.
    for stage in STAGE_MODULES:
        assert stage + ".py" not in source

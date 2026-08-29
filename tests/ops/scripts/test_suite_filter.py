"""Changed-file suite skip + repo-root collector."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]


def _load_runner() -> Any:
    spec = importlib.util.spec_from_file_location(
        "run_python_test_suites",
        ROOT / "ops" / "scripts" / "run_python_test_suites.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = _load_runner()


def _registry() -> dict[str, Any]:
    return runner._load_json(ROOT / "ops" / "config" / "python-contract.json")


def test_live_registry_exclusive_owned_paths() -> None:
    suites = runner.validate_registry(_registry())
    by_id = {suite["id"]: suite for suite in suites}
    assert by_id["repo-root"]["owned_paths"] == []
    assert (
        "environment/program-execution/peer_execution/autonomy/"
        in by_id["repo-root"]["foreign_owned_paths"]
    )
    assert by_id["claude-code-autonomy"]["owned_paths"] == [
        "environment/program-execution/peer_execution/autonomy/"
    ]
    assert by_id["subagent-generated-data-wave3"]["owned_paths"] == [
        "environment/agents/generated-data/"
    ]
    assert by_id["program-execution-controller"]["owned_paths"] == [
        "environment/program-execution/core/program-execution-controller-template/"
    ]


def test_collector_maps_ops_script_to_tests_mirror(tmp_path: Path) -> None:
    src = tmp_path / "ops" / "scripts"
    src.mkdir(parents=True)
    (src / "pr_gate_failure.py").write_text("x = 1\n", encoding="utf-8")
    mapped = tmp_path / "tests" / "ops" / "scripts"
    mapped.mkdir(parents=True)
    (mapped / "test_pr_gate_failure.py").write_text(
        "def test_ok():\n    assert True\n", encoding="utf-8"
    )
    collected = runner.collect_repo_root_tests(["ops/scripts/pr_gate_failure.py"], tmp_path)
    assert collected == ["tests/ops/scripts/test_pr_gate_failure.py"]


def test_collector_includes_existing_test_path(tmp_path: Path) -> None:
    path = tmp_path / "tests" / "ops" / "scripts" / "test_pr_gate_failure.py"
    path.parent.mkdir(parents=True)
    path.write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    collected = runner.collect_repo_root_tests(
        ["tests/ops/scripts/test_pr_gate_failure.py"], tmp_path
    )
    assert collected == ["tests/ops/scripts/test_pr_gate_failure.py"]


def test_collector_notes_and_skips_unmapped(tmp_path: Path, capsys: Any) -> None:
    (tmp_path / "ops" / "scripts").mkdir(parents=True)
    (tmp_path / "ops" / "scripts" / "orphan.py").write_text("x = 1\n", encoding="utf-8")
    collected = runner.collect_repo_root_tests(["ops/scripts/orphan.py"], tmp_path)
    assert collected == []
    assert "NOTE: no mapped tests for ops/scripts/orphan.py" in capsys.readouterr().out


def test_suite_skip_for_ops_script_change() -> None:
    suites = runner.validate_registry(_registry())
    changed = ["ops/scripts/pr_gate_failure.py"]
    matched = {suite["id"]: runner.suite_changed_paths(suite, changed) for suite in suites}
    assert matched["repo-root"] == changed
    assert matched["claude-code-autonomy"] == []
    assert matched["subagent-generated-data-wave3"] == []
    assert matched["program-execution-controller"] == []


def test_suite_skip_for_autonomy_scheduler() -> None:
    suites = runner.validate_registry(_registry())
    changed = ["environment/program-execution/peer_execution/autonomy/scheduler.py"]
    matched = {suite["id"]: runner.suite_changed_paths(suite, changed) for suite in suites}
    assert matched["claude-code-autonomy"] == changed
    assert matched["repo-root"] == []
    assert matched["subagent-generated-data-wave3"] == []
    assert matched["program-execution-controller"] == []


def test_no_python_skips_all_suites(capsys: Any) -> None:
    listed = Path("/tmp")  # placeholder; exercise helper
    del listed
    suites = runner.validate_registry(_registry())
    changed = ["README.md", "ops/config/python-contract.json"]
    assert not any(runner.is_python_path(path) for path in changed)
    for suite in suites:
        assert not any(runner.is_python_path(p) for p in runner.suite_changed_paths(suite, changed))


def test_pytest_argv_replaces_dot_with_mapped_files() -> None:
    suite = {
        "id": "repo-root",
        "kind": "pytest",
        "profiles": {"local": {"argv": [".", "--ignore=child"]}},
    }
    argv = runner._pytest_argv_spec(suite, "local", ["tests/ops/scripts/test_pr_gate_failure.py"])
    assert argv[0] == "tests/ops/scripts/test_pr_gate_failure.py"
    assert "." not in argv


def test_suite_env_strips_pr_stack(monkeypatch: Any) -> None:
    monkeypatch.setenv("PR_STACK", "auto")
    env = runner._suite_env({"env": {"TESTING": "true"}}, {"REPO_ROOT": "/r", "PYTHON": "p"})
    assert "PR_STACK" not in env
    assert env["TESTING"] == "true"


def test_owned_paths_dot_rejected() -> None:
    reg = {
        "schema_version": "1.0.0",
        "import_map": {},
        "required_dev_distributions": [],
        "non_test_exclusions": [],
        "suites": [
            {
                "id": "repo-root",
                "kind": "pytest",
                "working_directory": ".",
                "owned_paths": ["."],
                "env": {},
                "append_user_pytest_args": True,
                "allow_exit_5": True,
                "profiles": {"local": {"argv": ["."]}, "ci": {"argv": ["."]}},
            }
        ],
    }
    try:
        runner.validate_registry(reg)
    except runner.RegistryError as exc:
        assert "must not claim owned_paths ['.']" in str(exc)
    else:
        raise AssertionError("expected RegistryError")

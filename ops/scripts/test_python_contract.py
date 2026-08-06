#!/usr/bin/env python3
"""Deterministic tests for the Python test contract runner and drift validator.

Runs offline against temporary fixture repositories; never mutates the real tree
and never touches the network. Executable directly (the canonical checkpoint runs
`python ops/scripts/test_python_contract.py`) and collectable by root pytest.

Modules under test are loaded by file path so this works whether the file is run
standalone (its own directory is on sys.path) or collected by pytest from the
repository root (its directory is not).
"""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

_SCRIPTS = Path(__file__).resolve().parent


def _load(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS / f"{name}.py")
    if spec is None or spec.loader is None:
        msg = f"cannot load module: {name}"
        raise RuntimeError(msg)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = _load("run_python_test_suites")
validator = _load("validate_python_contract")


def valid_registry() -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "import_map": {"yaml": "pyyaml"},
        "required_dev_distributions": ["pytest-xdist"],
        "non_test_exclusions": [
            {"path": "noise/not_a_test.py", "reason": "shaped like a test, is not one"}
        ],
        "suites": [
            {
                "id": "repo-root",
                "kind": "pytest",
                "working_directory": ".",
                "owned_paths": ["."],
                "env": {"TESTING": "true", "PYTHONPATH": "${REPO_ROOT}"},
                "append_user_pytest_args": True,
                "allow_exit_5": True,
                "profiles": {
                    "local": {"argv": [".", "--ignore=child/tests"]},
                    "ci": {"argv": [".", "--ignore=child/tests", "-n", "auto"]},
                },
                "rationale": "root discovery",
            },
            {
                "id": "child",
                "kind": "pytest",
                "working_directory": ".",
                "owned_paths": ["child/tests"],
                "env": {"PYTHONPATH": "${REPO_ROOT}/child"},
                "append_user_pytest_args": True,
                "allow_exit_5": True,
                "profiles": {
                    "local": {"argv": ["child/tests", "-o", "addopts="]},
                    "ci": {"argv": ["child/tests", "-o", "addopts="]},
                },
                "rationale": "isolated child package",
            },
        ],
    }


VALID_PYPROJECT = """\
[project]
name = "fixture"
version = "0.0.0"
dependencies = ["pyyaml>=6.0"]

[project.optional-dependencies]
dev = ["pytest-xdist==3.8.0"]
"""

VALID_REQUIREMENTS = "pytest-xdist==3.8.0\n"

VALID_WORKFLOW = """\
name: L9 Lint and Test
on: [push]
jobs:
  test:
    steps:
      - run: uv sync --locked --no-build --extra dev
      - run: uv run --frozen --no-build python ops/scripts/run_python_test_suites.py --profile ci
"""

VALID_WRAPPER = """\
#!/usr/bin/env bash
set -euo pipefail
exec python3 ops/scripts/run_python_test_suites.py --profile local -- "$@"
"""


def build_repo(
    root: Path,
    *,
    registry: dict[str, Any] | None = None,
    pyproject: str = VALID_PYPROJECT,
    requirements: str = VALID_REQUIREMENTS,
    workflow: str = VALID_WORKFLOW,
    wrapper: str = VALID_WRAPPER,
) -> Path:
    reg = registry if registry is not None else valid_registry()
    (root / "ops" / "config").mkdir(parents=True, exist_ok=True)
    (root / "ops" / "scripts").mkdir(parents=True, exist_ok=True)
    (root / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
    (root / "child" / "tests").mkdir(parents=True, exist_ok=True)
    (root / "noise").mkdir(parents=True, exist_ok=True)
    (root / "noise" / "not_a_test.py").write_text("# not a test\n", encoding="utf-8")
    (root / "ops" / "config" / "python-contract.json").write_text(
        json.dumps(reg, indent=2), encoding="utf-8"
    )
    (root / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    (root / "requirements.txt").write_text(requirements, encoding="utf-8")
    (root / ".github" / "workflows" / "l9-lint-test.yml").write_text(workflow, encoding="utf-8")
    (root / "ops" / "scripts" / "run_pytest_suites.sh").write_text(wrapper, encoding="utf-8")
    (root / "uv.lock").write_text("# lock\n", encoding="utf-8")
    return root


class ValidatorTests(unittest.TestCase):
    def test_valid_registry_passes_all_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = build_repo(Path(tmp))
            results = validator.run_all(root)
            failed = [(name, detail) for name, ok, detail in results if not ok]
            self.assertEqual(failed, [], f"unexpected failures: {failed}")

    def test_duplicate_suite_id_rejected(self) -> None:
        reg = valid_registry()
        reg["suites"][1]["id"] = "repo-root"
        with tempfile.TemporaryDirectory() as tmp:
            root = build_repo(Path(tmp), registry=reg)
            with self.assertRaises(validator.ContractError):
                validator.check_structure(validator.load_registry(root), root)

    def test_path_escape_rejected(self) -> None:
        reg = valid_registry()
        reg["suites"][1]["owned_paths"] = ["../outside"]
        with tempfile.TemporaryDirectory() as tmp:
            root = build_repo(Path(tmp), registry=reg)
            with self.assertRaises(validator.ContractError):
                validator.check_structure(validator.load_registry(root), root)

    def test_unknown_suite_kind_rejected(self) -> None:
        reg = valid_registry()
        reg["suites"][1]["kind"] = "make"
        with tempfile.TemporaryDirectory() as tmp:
            root = build_repo(Path(tmp), registry=reg)
            with self.assertRaises(validator.ContractError):
                validator.check_structure(validator.load_registry(root), root)

    def test_suite_order_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = build_repo(Path(tmp))
            suites = validator.check_structure(validator.load_registry(root), root)
            self.assertEqual([s["id"] for s in suites], ["repo-root", "child"])

    def test_missing_owner_for_ignored_suite_detected(self) -> None:
        # Root ignores a path no suite owns -> zero owners -> fail closed.
        reg = valid_registry()
        reg["suites"][1]["owned_paths"] = ["child/other"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_repo(root, registry=reg)
            (root / "child" / "other").mkdir(parents=True, exist_ok=True)
            suites = validator.check_structure(validator.load_registry(root), root)
            with self.assertRaises(validator.ContractError):
                validator.check_ignore_ownership(suites)

    def test_owned_path_must_exist(self) -> None:
        reg = valid_registry()
        reg["suites"][1]["owned_paths"] = ["child/missing"]
        with tempfile.TemporaryDirectory() as tmp:
            root = build_repo(Path(tmp), registry=reg)
            suites = validator.check_structure(validator.load_registry(root), root)
            with self.assertRaises(validator.ContractError):
                validator.check_owned_paths_exist(suites, root)

    def test_non_test_exclusion_without_reason_rejected(self) -> None:
        reg = valid_registry()
        reg["non_test_exclusions"] = [{"path": "noise/not_a_test.py", "reason": "   "}]
        with tempfile.TemporaryDirectory() as tmp:
            root = build_repo(Path(tmp), registry=reg)
            with self.assertRaises(validator.ContractError):
                validator.check_non_test_exclusions(validator.load_registry(root), root)

    def test_pin_mismatch_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = build_repo(Path(tmp), requirements="pytest-xdist==9.9.9\n")
            with self.assertRaises(validator.ContractError):
                validator.check_requirements_mirror(root)

    def test_absent_required_dev_tool_detected(self) -> None:
        pyproject = VALID_PYPROJECT.replace(
            'dev = ["pytest-xdist==3.8.0"]', 'dev = ["ruff==0.16.0"]'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = build_repo(Path(tmp), pyproject=pyproject, requirements="ruff==0.16.0\n")
            reg = validator.load_registry(root)
            with self.assertRaises(validator.ContractError):
                validator.check_dev_extra_pins(reg, root)

    def test_forbidden_floating_ci_install_detected(self) -> None:
        workflow = VALID_WORKFLOW + "      - run: pip install pytest-xdist\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = build_repo(Path(tmp), workflow=workflow)
            with self.assertRaises(validator.ContractError):
                validator.check_ci_workflow(root)

    def test_ci_bypassing_runner_detected(self) -> None:
        workflow = VALID_WORKFLOW.replace(
            "uv run --frozen --no-build python ops/scripts/run_python_test_suites.py --profile ci",
            "pytest .",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = build_repo(Path(tmp), workflow=workflow)
            with self.assertRaises(validator.ContractError):
                validator.check_ci_workflow(root)

    def test_wrapper_with_embedded_topology_detected(self) -> None:
        wrapper = VALID_WRAPPER + "pytest . --ignore=child/tests\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = build_repo(Path(tmp), wrapper=wrapper)
            with self.assertRaises(validator.ContractError):
                validator.check_wrapper(root)

    def test_import_map_unknown_distribution_detected(self) -> None:
        reg = valid_registry()
        reg["import_map"] = {"requests": "requests"}
        with tempfile.TemporaryDirectory() as tmp:
            root = build_repo(Path(tmp), registry=reg)
            with self.assertRaises(validator.ContractError):
                validator.check_import_map(reg, root)


class RunnerTests(unittest.TestCase):
    def test_registry_loads_and_validates(self) -> None:
        suites = runner.validate_registry(valid_registry())
        self.assertEqual([s["id"] for s in suites], ["repo-root", "child"])

    def test_duplicate_id_rejected_by_runner(self) -> None:
        reg = valid_registry()
        reg["suites"][1]["id"] = "repo-root"
        with self.assertRaises(runner.RegistryError):
            runner.validate_registry(reg)

    def test_command_suite_cannot_forward_pytest_args(self) -> None:
        reg = valid_registry()
        reg["suites"][1]["kind"] = "command"
        reg["suites"][1]["append_user_pytest_args"] = True
        reg["suites"][1]["profiles"]["local"]["argv"] = ["${PYTHON}", "-c", "pass"]
        reg["suites"][1]["profiles"]["ci"]["argv"] = ["${PYTHON}", "-c", "pass"]
        with self.assertRaises(runner.RegistryError):
            runner.validate_registry(reg)

    def test_unsupported_substitution_rejected(self) -> None:
        reg = valid_registry()
        reg["suites"][0]["env"]["PYTHONPATH"] = "${HOME}"
        with self.assertRaises(runner.RegistryError):
            runner.validate_registry(reg)

    def test_pythonpath_isolation_between_suites(self) -> None:
        reg = valid_registry()
        mapping = {"REPO_ROOT": "/repo", "PYTHON": "python3"}
        root_env = runner._suite_env(reg["suites"][0], mapping)
        child_env = runner._suite_env(reg["suites"][1], mapping)
        self.assertEqual(root_env["PYTHONPATH"], "/repo")
        self.assertEqual(child_env["PYTHONPATH"], "/repo/child")
        self.assertNotEqual(root_env["PYTHONPATH"], child_env["PYTHONPATH"])

    def test_exit5_normalization(self) -> None:
        self.assertEqual(runner._normalize_exit(5, True, "s"), 0)
        self.assertEqual(runner._normalize_exit(5, False, "s"), 5)
        self.assertEqual(runner._normalize_exit(1, True, "s"), 1)

    def test_user_args_forwarded_only_to_allowed_suites(self) -> None:
        reg = valid_registry()
        mapping = {"REPO_ROOT": str(_SCRIPTS.parents[1]), "PYTHON": "python3"}
        captured: list[list[str]] = []

        def fake_run(argv: list[str], cwd: Path, env: dict[str, str]) -> int:
            captured.append(argv)
            return 0

        # pytest suite that opts in -> user args appended.
        with mock.patch.object(runner, "_run_subprocess", side_effect=fake_run):
            runner.run_suite(reg["suites"][0], "local", ["-k", "smoke"], mapping)
        self.assertEqual(captured[-1][-2:], ["-k", "smoke"])

        # command suite that opts out -> user args never appended.
        reg["suites"][1]["kind"] = "command"
        reg["suites"][1]["append_user_pytest_args"] = False
        reg["suites"][1]["profiles"]["local"]["argv"] = ["${PYTHON}", "-c", "pass"]
        captured.clear()
        with mock.patch.object(runner, "_run_subprocess", side_effect=fake_run):
            runner.run_suite(reg["suites"][1], "local", ["-k", "smoke"], mapping)
        self.assertNotIn("-k", captured[-1])
        self.assertNotIn("smoke", captured[-1])

    def test_exact_nonzero_exit_propagates(self) -> None:
        suite = {
            "id": "boom",
            "kind": "command",
            "working_directory": ".",
            "owned_paths": ["."],
            "env": {},
            "append_user_pytest_args": False,
            "allow_exit_5": False,
            "profiles": {
                "local": {"argv": ["${PYTHON}", "-c", "import sys; sys.exit(7)"]},
                "ci": {"argv": ["${PYTHON}", "-c", "import sys; sys.exit(7)"]},
            },
            "rationale": "always fails",
        }
        import sys as _sys

        mapping = {"REPO_ROOT": str(_SCRIPTS.parents[1]), "PYTHON": _sys.executable}
        self.assertEqual(runner.run_suite(suite, "local", [], mapping), 7)

    def test_command_sequence_stops_on_first_failure(self) -> None:
        import sys as _sys

        suite = {
            "id": "seq",
            "kind": "command_sequence",
            "working_directory": ".",
            "owned_paths": ["."],
            "env": {},
            "append_user_pytest_args": False,
            "allow_exit_5": False,
            "profiles": {
                "local": {
                    "argv": [
                        ["${PYTHON}", "-c", "import sys; sys.exit(4)"],
                        ["${PYTHON}", "-c", "import sys; sys.exit(0)"],
                    ]
                },
                "ci": {"argv": [["${PYTHON}", "-c", "pass"]]},
            },
            "rationale": "first command fails",
        }
        mapping = {"REPO_ROOT": str(_SCRIPTS.parents[1]), "PYTHON": _sys.executable}
        self.assertEqual(runner.run_suite(suite, "local", [], mapping), 4)


if __name__ == "__main__":
    unittest.main()

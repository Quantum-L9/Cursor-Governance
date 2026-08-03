#!/usr/bin/env python3
"""Deterministic, network-free tests for the Python test contract.

Covers both authorities added by this change:

* ``validate_python_contract`` — the read-only drift validator, exercised
  against temporary fixture repositories (never the real repository).
* ``run_python_test_suites`` — the canonical runner's pure argv/env builders
  and its exit-code / exit-5 handling, exercised with the module's repository
  root pointed at a temporary directory.

Run directly (``python ops/scripts/test_python_contract.py``) or under pytest.
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_python_test_suites as runner  # noqa: E402
import validate_python_contract as validator  # noqa: E402


def _valid_registry() -> dict:
    return {
        "schema_version": "1.0.0",
        "description": "fixture",
        "import_map": {"yaml": "PyYAML"},
        "required_dev_distributions": ["pytest", "pytest-xdist"],
        "non_test_exclusions": [
            {"path": "pkg/helper_test.py", "reason": "helper, not a pytest test"}
        ],
        "suites": [
            {
                "id": "repo-root",
                "kind": "pytest",
                "working_directory": ".",
                "owned_paths": ["."],
                "environment": {"TESTING": "true", "PYTHONPATH": "${REPO_ROOT}"},
                "active_suite_ignores": ["sub/tests"],
                "profiles": {"local": {"argv": ["."]}, "ci": {"argv": [".", "-v"]}},
                "append_user_pytest_args": True,
                "allow_exit_5": True,
                "rationale": "root discovery",
            },
            {
                "id": "sub-runner",
                "kind": "command",
                "working_directory": ".",
                "owned_paths": ["sub/tests"],
                "environment": {},
                "command": ["${PYTHON}", "sub/tests/run.py"],
                "allow_exit_5": False,
                "rationale": "dedicated runner",
            },
        ],
    }


_PYPROJECT = """\
[project]
name = "fixture"
version = "0.0.0"
requires-python = ">=3.12"
dependencies = ["pydantic>=2.0,<3", "pyyaml>=6.0"]

[project.optional-dependencies]
dev = ["pytest==9.1.1", "pytest-xdist==3.8.0"]

[tool.uv]
package = false
"""

_REQUIREMENTS = "pytest==9.1.1\npytest-xdist==3.8.0\n"

_WORKFLOW = """\
name: L9 Lint and Test
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: uv sync --locked --extra dev
      - run: uv run --no-build python ops/scripts/run_python_test_suites.py --profile ci
"""

_WRAPPER = (
    '#!/usr/bin/env bash\npython3 ops/scripts/run_python_test_suites.py --profile local -- "$@"\n'
)


def _write_valid_repo(root: Path, registry: dict | None = None) -> None:
    (root / "ops" / "config").mkdir(parents=True, exist_ok=True)
    (root / "ops" / "scripts").mkdir(parents=True, exist_ok=True)
    (root / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
    (root / "sub" / "tests").mkdir(parents=True, exist_ok=True)

    data = registry if registry is not None else _valid_registry()
    (root / "ops" / "config" / "python-contract.json").write_text(
        json.dumps(data, indent=2), encoding="utf-8"
    )
    (root / "pyproject.toml").write_text(_PYPROJECT, encoding="utf-8")
    (root / "requirements.txt").write_text(_REQUIREMENTS, encoding="utf-8")
    (root / "uv.lock").write_text("# lock\n", encoding="utf-8")
    (root / ".github" / "workflows" / "l9-lint-test.yml").write_text(_WORKFLOW, encoding="utf-8")
    (root / "ops" / "scripts" / "run_pytest_suites.sh").write_text(_WRAPPER, encoding="utf-8")


class ValidatorTests(unittest.TestCase):
    def _run_with(self, mutate=None) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = _valid_registry()
            if mutate is not None:
                mutate(registry)
            _write_valid_repo(root, registry)
            return validator.run(root)

    def test_valid_registry_passes(self):
        self.assertEqual(self._run_with(), [])

    def test_deterministic_suite_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_valid_repo(root)
            loaded = validator.load_registry(root)
            self.assertEqual([s["id"] for s in loaded["suites"]], ["repo-root", "sub-runner"])

    def test_duplicate_suite_id_rejected(self):
        def mutate(reg):
            dup = copy.deepcopy(reg["suites"][1])
            dup["id"] = "repo-root"
            reg["suites"].append(dup)

        errors = self._run_with(mutate)
        self.assertTrue(any("duplicate suite id" in e for e in errors), errors)

    def test_path_escape_rejected(self):
        def mutate(reg):
            reg["suites"][1]["owned_paths"] = ["../escape"]

        errors = self._run_with(mutate)
        self.assertTrue(any("escapes root" in e for e in errors), errors)

    def test_unknown_suite_kind_rejected(self):
        def mutate(reg):
            reg["suites"][1]["kind"] = "magic"

        errors = self._run_with(mutate)
        self.assertTrue(any("unknown kind" in e for e in errors), errors)

    def test_unsupported_substitution_rejected(self):
        def mutate(reg):
            reg["suites"][1]["command"] = ["${SHELL}", "x"]

        errors = self._run_with(mutate)
        self.assertTrue(any("unsupported substitution" in e for e in errors), errors)

    def test_missing_generated_data_suite_detected(self):
        # Remove the owner of the 'sub/tests' active-suite ignore: the root
        # suite now ignores a path no registry suite owns.
        def mutate(reg):
            reg["suites"] = [reg["suites"][0]]

        errors = self._run_with(mutate)
        self.assertTrue(
            any("active_suite_ignore" in e and "sub/tests" in e for e in errors), errors
        )

    def test_missing_program_execution_suite_detected(self):
        # A second ignore with no owner is likewise flagged.
        def mutate(reg):
            reg["suites"][0]["active_suite_ignores"].append("pe/scripts/tests")

        errors = self._run_with(mutate)
        self.assertTrue(
            any("active_suite_ignore" in e and "pe/scripts/tests" in e for e in errors), errors
        )

    def test_non_test_exclusion_without_reason_rejected(self):
        def mutate(reg):
            reg["non_test_exclusions"][0].pop("reason")

        errors = self._run_with(mutate)
        self.assertTrue(any("missing a reason" in e for e in errors), errors)

    def test_import_map_unresolved_detected(self):
        def mutate(reg):
            reg["import_map"]["requests"] = "requests"

        errors = self._run_with(mutate)
        self.assertTrue(any("import_map" in e and "requests" in e for e in errors), errors)

    def test_absent_required_dev_tool_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_valid_repo(root)
            # Drop pytest-xdist from the dev extra AND the mirror.
            (root / "pyproject.toml").write_text(
                _PYPROJECT.replace(', "pytest-xdist==3.8.0"', ""), encoding="utf-8"
            )
            (root / "requirements.txt").write_text("pytest==9.1.1\n", encoding="utf-8")
            errors = validator.run(root)
        self.assertTrue(any("required dev distribution" in e for e in errors), errors)

    def test_pin_mismatch_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_valid_repo(root)
            (root / "requirements.txt").write_text(
                "pytest==9.1.1\npytest-xdist==3.7.0\n", encoding="utf-8"
            )
            errors = validator.run(root)
        self.assertTrue(any("pin mismatch" in e for e in errors), errors)

    def test_forbidden_floating_ci_install_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_valid_repo(root)
            workflow = _WORKFLOW + "      - run: pip install pytest-xdist\n"
            (root / ".github" / "workflows" / "l9-lint-test.yml").write_text(
                workflow, encoding="utf-8"
            )
            errors = validator.run(root)
        self.assertTrue(any("floating install" in e for e in errors), errors)

    def test_ci_bypassing_runner_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_valid_repo(root)
            workflow = (
                "name: x\non: [push]\njobs:\n  test:\n    steps:\n"
                "      - run: uv sync --locked --extra dev\n"
            )
            (root / ".github" / "workflows" / "l9-lint-test.yml").write_text(
                workflow, encoding="utf-8"
            )
            errors = validator.run(root)
        self.assertTrue(any("exactly once" in e for e in errors), errors)

    def test_shell_wrapper_embedded_topology_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_valid_repo(root)
            wrapper = _WRAPPER + "PYTHONPATH=environment/claude-code pytest --ignore=foo\n"
            (root / "ops" / "scripts" / "run_pytest_suites.sh").write_text(
                wrapper, encoding="utf-8"
            )
            errors = validator.run(root)
        self.assertTrue(any("embedded suite topology" in e for e in errors), errors)

    def test_missing_lockfile_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_valid_repo(root)
            (root / "uv.lock").unlink()
            errors = validator.run(root)
        self.assertTrue(any("lockfile missing" in e for e in errors), errors)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self._saved_root = runner.REPO_ROOT
        self._tmp = tempfile.TemporaryDirectory()
        runner.REPO_ROOT = Path(self._tmp.name)

    def tearDown(self):
        runner.REPO_ROOT = self._saved_root
        self._tmp.cleanup()

    def test_pythonpath_isolation_root_vs_claude(self):
        root_suite = {"environment": {"PYTHONPATH": "${REPO_ROOT}"}}
        claude_suite = {"environment": {"PYTHONPATH": "environment/claude-code"}}
        root_env = runner.build_env(root_suite)
        claude_env = runner.build_env(claude_suite)
        self.assertEqual(root_env["PYTHONPATH"], str(runner.REPO_ROOT))
        self.assertEqual(
            claude_env["PYTHONPATH"], str(runner.REPO_ROOT / "environment" / "claude-code")
        )
        self.assertNotEqual(root_env["PYTHONPATH"], claude_env["PYTHONPATH"])

    def test_user_args_forwarded_only_to_allowed_suites(self):
        allowed = {
            "profiles": {"local": {"argv": ["."]}},
            "append_user_pytest_args": True,
        }
        denied = {
            "profiles": {"local": {"argv": ["."]}},
            "append_user_pytest_args": False,
        }
        argv_allowed = runner.build_pytest_argv(allowed, "local", ["-k", "smoke"])
        argv_denied = runner.build_pytest_argv(denied, "local", ["-k", "smoke"])
        self.assertEqual(argv_allowed[-2:], ["-k", "smoke"])
        self.assertNotIn("smoke", argv_denied)

    def test_command_suite_ignores_user_args(self):
        suite = {"command": ["${PYTHON}", "run.py"]}
        argv = runner.build_command_argv(suite)
        self.assertEqual(argv, [sys.executable, "run.py"])

    def test_exact_nonzero_exit_propagation(self):
        suite = {
            "working_directory": ".",
            "environment": {},
            "command": ["${PYTHON}", "-c", "import sys; sys.exit(3)"],
        }
        self.assertEqual(runner._run_command(suite), 3)

    def test_exit5_rejected_by_default_and_accepted_when_configured(self):
        (runner.REPO_ROOT / "emptydir").mkdir()
        base = {
            "id": "empty",
            "working_directory": ".",
            "environment": {},
            "profiles": {"local": {"argv": ["emptydir"]}},
        }
        rejected = dict(base, allow_exit_5=False)
        accepted = dict(base, allow_exit_5=True)
        self.assertEqual(runner._run_pytest(rejected, "local", []), 5)
        self.assertEqual(runner._run_pytest(accepted, "local", []), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

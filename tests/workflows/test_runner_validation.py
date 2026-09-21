"""Regression tests for workflow graph validation before execution."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

RUNNER_PATH = Path(__file__).resolve().parents[2] / "workflows" / "runner.py"


def _runner_type():
    spec = importlib.util.spec_from_file_location("l9_workflow_runner", RUNNER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.DAGRunner


class WorkflowGraphValidationTests(unittest.TestCase):
    def _workflow(self, directory: Path, body: str) -> Path:
        path = directory / "workflow.yml"
        path.write_text(textwrap.dedent(body), encoding="utf-8")
        return path

    def test_run_rejects_unknown_dependency_before_shell_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            working_dir = Path(temp)
            workflow = self._workflow(
                working_dir,
                """
                id: blocked
                steps:
                  - id: unsafe
                    type: shell
                    depends_on: [missing]
                    config:
                      commands: ["touch must-not-exist"]
                """,
            )
            runner = _runner_type()(workflow, working_dir)
            self.assertFalse(runner.run())
            self.assertFalse((working_dir / "must-not-exist").exists())
            self.assertFalse((working_dir / ".workflow_state_blocked.json").exists())

    def test_validate_rejects_a_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            workflow = self._workflow(
                directory,
                """
                id: cyclic
                steps:
                  - id: one
                    type: checkpoint
                    depends_on: [two]
                  - id: two
                    type: checkpoint
                    depends_on: [one]
                """,
            )
            self.assertFalse(_runner_type()(workflow, directory).validate())

    def test_validate_rejects_duplicate_step_identifiers(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            workflow = self._workflow(
                directory,
                """
                id: duplicate
                steps:
                  - id: one
                    type: checkpoint
                  - id: one
                    type: checkpoint
                """,
            )
            self.assertFalse(_runner_type()(workflow, directory).validate())


if __name__ == "__main__":
    raise SystemExit(unittest.main())

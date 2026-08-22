"""Execution progress must count only what is finished.

`Execution: 3 / 39 tasks` counted LEASED, CONTRACTED, EXECUTING, SUBMITTED,
VERIFYING and PASSED_LOCAL as done, so a campaign with one task in flight and
none finished reported progress it had not made.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

PE_ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


timing = _load("pe_timing_progress_under_test", PE_ROOT / "scripts/pe_timing.py")


def _tasks(*pairs: tuple[str, str], eligible: set[str] | None = None) -> list[dict]:
    ready = eligible or set()
    return [
        {"id": task_id, "runtime_state": state, "eligible": task_id in ready}
        for task_id, state in pairs
    ]


class ProgressAccountingTest(unittest.TestCase):
    def _progress(self, tasks: list[dict]) -> dict:
        return timing.progress(tasks, campaign_id="demo", preparation="COMPLETE")

    def test_executing_task_is_not_counted_completed(self) -> None:
        report = self._progress(_tasks(("TASK-001", "EXECUTING")))

        self.assertEqual(report["execution"]["done"], 0)
        self.assertEqual(report["execution"]["in_progress"], 1)

    def test_passed_local_task_is_not_counted_completed(self) -> None:
        report = self._progress(_tasks(("TASK-001", "PASSED_LOCAL")))

        self.assertEqual(report["execution"]["done"], 0)
        self.assertEqual(report["execution"]["in_progress"], 1)

    def test_completed_count_requires_completed_state(self) -> None:
        report = self._progress(
            _tasks(
                ("TASK-001", "COMPLETED"),
                ("TASK-002", "COMPLETED"),
                ("TASK-003", "COMPLETED"),
                ("TASK-004", "VERIFYING"),
            )
        )

        self.assertEqual(report["execution"]["done"], 3)
        self.assertEqual(report["execution"]["total"], 4)

    def test_progress_reports_in_progress_separately(self) -> None:
        report = self._progress(
            _tasks(
                ("TASK-001", "COMPLETED"),
                ("TASK-002", "COMPLETED"),
                ("TASK-003", "COMPLETED"),
                ("TASK-004", "SUBMITTED"),
                ("TASK-005", "BLOCKED"),
                ("TASK-006", "BLOCKED"),
                ("TASK-007", "BLOCKED"),
                eligible={"TASK-005", "TASK-006"},
            )
        )

        execution = report["execution"]
        self.assertEqual(execution["done"], 3)
        self.assertEqual(execution["in_progress"], 1)
        self.assertEqual(execution["runnable"], 2)
        self.assertEqual(execution["not_ready"], 1)
        self.assertEqual(
            execution["done"]
            + execution["in_progress"]
            + execution["runnable"]
            + execution["not_ready"],
            execution["total"],
        )

    def test_every_state_is_accounted_for_exactly_once(self) -> None:
        self.assertNotIn(timing.COMPLETED_STATE, timing.IN_PROGRESS_STATES)
        self.assertEqual(
            timing.IN_PROGRESS_STATES | {timing.COMPLETED_STATE}, timing.EXECUTION_STATES
        )

    def test_rendered_progress_names_completed_not_tasks(self) -> None:
        report = self._progress(_tasks(("TASK-001", "EXECUTING"), ("TASK-002", "COMPLETED")))

        rendered = timing.format_progress(report)

        self.assertIn("Execution:    1 / 2 COMPLETED", rendered)
        self.assertIn("In progress:  1", rendered)


if __name__ == "__main__":
    unittest.main()

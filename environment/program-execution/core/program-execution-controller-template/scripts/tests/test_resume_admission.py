"""PEC-P1-001: `pec admit-resume` is the Controller's Program-identity decision."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml
from helpers import bootstrap_repo, run_cli, write_yaml


def _edit_task_objective(blueprint: Path, task_id: str, objective: str) -> None:
    path = blueprint / "TASK_CARDS.yaml"
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    for task in doc["tasks"]:
        if task["id"] == task_id:
            task["objective"] = objective
    write_yaml(path, doc)


class AdmitResumeTests(unittest.TestCase):
    def test_unchanged_blueprint_is_exact_match(self) -> None:
        with TemporaryDirectory() as raw:
            _, _, workspace = bootstrap_repo(Path(raw), two_tasks=True)
            verdict = run_cli("admit-resume", "--workspace", str(workspace))
            self.assertEqual(verdict["decision"], "EXACT_MATCH")
            self.assertTrue(verdict["may_execute"])

    def test_task_drift_names_the_relock_scope_and_refuses_execution(self) -> None:
        with TemporaryDirectory() as raw:
            blueprint, _, workspace = bootstrap_repo(Path(raw), two_tasks=True)
            _edit_task_objective(blueprint, "TASK-002", "edited after bootstrap")
            verdict = run_cli("admit-resume", "--workspace", str(workspace), expect=1)
            self.assertEqual(verdict["decision"], "TASK_SCOPED_DRIFT")
            self.assertFalse(verdict["may_execute"])
            self.assertEqual(verdict["relock_scope"], ["TASK-002"])
            # The canonical relock, with exactly that scope, restores identity.
            run_cli(
                "relock", "--workspace", str(workspace), "--actor", "test", "--task", "TASK-002"
            )
            again = run_cli("admit-resume", "--workspace", str(workspace))
            self.assertEqual(again["decision"], "EXACT_MATCH")

    def test_gate_drift_is_wider_than_tasks(self) -> None:
        with TemporaryDirectory() as raw:
            blueprint, _, workspace = bootstrap_repo(Path(raw))
            path = blueprint / "CONVERGENCE_GATES.yaml"
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
            doc["gates"][0]["blocking"] = False
            write_yaml(path, doc)
            verdict = run_cli("admit-resume", "--workspace", str(workspace), expect=1)
            self.assertEqual(verdict["decision"], "WIDER_PROGRAM_DRIFT")
            self.assertEqual(verdict["relock_scope"], [])

    def test_runtime_digest_disagreeing_with_the_lock_is_invalid(self) -> None:
        with TemporaryDirectory() as raw:
            _, _, workspace = bootstrap_repo(Path(raw))
            import sqlite3

            conn = sqlite3.connect(workspace / "runtime" / "state.sqlite")
            conn.execute(
                "UPDATE meta SET value=? WHERE key='program_digest'", ('"' + "0" * 64 + '"',)
            )
            conn.commit()
            conn.close()
            verdict = run_cli("admit-resume", "--workspace", str(workspace), expect=1)
            self.assertEqual(verdict["decision"], "LOCK_INVALID")


if __name__ == "__main__":
    unittest.main()

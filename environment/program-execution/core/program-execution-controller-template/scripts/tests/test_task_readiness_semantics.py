"""ADR-0023 conformance: ready / waiting / blocked are distinct conditions.

Dependency and wave sequencing is *waiting* (definition stays ready); blocked
is reserved for genuine inability to proceed (unresolved blocking Unknowns,
missing required evidence, explicitly failed blocking gates); terminal and
in-flight work is neither.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import yaml
from helpers import (
    SCRIPTS,
    bootstrap_repo,
    cleanup_worktree,
    make_blueprint,
    make_repo,
    prepare_attempt,
    register_contract,
    run_cli,
)

sys.path.insert(0, str(SCRIPTS))
from pec.state import StateDB


def _ids(items: list[dict[str, Any]]) -> list[str]:
    return [str(item["id"]) for item in items]


def _entry(view: dict[str, Any], bucket: str, task_id: str) -> dict[str, Any] | None:
    for item in view[bucket]:
        if item["id"] == task_id:
            return item
    return None


def _dependency_blueprint(temp: Path) -> Path:
    """Two complete tasks; TASK-002 depends on TASK-001 through the graph."""
    bp = make_blueprint(temp / "blueprint", two_tasks=True)
    graph = yaml.safe_load((bp / "DEPENDENCY_GRAPH.yaml").read_text(encoding="utf-8"))
    graph["edges"] = [
        {
            "id": "EDGE-001",
            "from": "TASK-001",
            "to": "TASK-002",
            "relation": "requires",
            "blocking": True,
            "proof_gate_ids": [],
        }
    ]
    (bp / "DEPENDENCY_GRAPH.yaml").write_text(
        yaml.safe_dump(graph, sort_keys=False), encoding="utf-8"
    )
    return bp


def _bootstrap(temp: Path, bp: Path) -> tuple[Path, Path]:
    repo = make_repo(temp / "repo")
    workspace = temp / "runtime"
    run_cli("bootstrap", "--workspace", str(workspace), "--blueprint", str(bp))
    run_cli("reconcile", "--workspace", str(workspace), "--repository", f"repo-a={repo}")
    return repo, workspace


class TaskReadinessSemanticsTest(unittest.TestCase):
    def test_dependency_wait_is_waiting_not_blocked(self):
        """C1/C2: an unmet dependency is sequencing; completion advances it."""
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            bp = _dependency_blueprint(temp)
            repo, workspace = _bootstrap(temp, bp)
            register_contract(temp, workspace, task_id="TASK-001", output="docs/result.txt")
            register_contract(temp, workspace, task_id="TASK-002", output="docs/second.txt")

            status = run_cli("status", "--workspace", str(workspace))
            by_id = {item["id"]: item for item in status["tasks"]}
            self.assertEqual(by_id["TASK-001"]["definition_status"], "ready")
            self.assertEqual(by_id["TASK-002"]["definition_status"], "ready")

            view = run_cli("next", "--workspace", str(workspace))
            self.assertIn("TASK-001", _ids(view["ready"]))
            self.assertIn("TASK-002", _ids(view["waiting"]))
            self.assertNotIn("TASK-002", _ids(view["blocked"]))
            waiting = _entry(view, "waiting", "TASK-002")
            assert waiting is not None
            self.assertIn("dependency_not_complete:TASK-001", waiting["waiting_reasons"])
            self.assertEqual(waiting["blocking_reasons"], [])
            self.assertEqual(waiting["blockers"], [])

            # A waiting task still refuses a claim until prerequisites hold.
            refused = run_cli(
                "claim", "TASK-002", "--workspace", str(workspace), "--holder", "worker", expect=2
            )
            self.assertIn("dependency_not_complete:TASK-001", refused["error"])

            # C2 + C7: drive TASK-001 to the qualifying verified state; while
            # it is in flight it is in_progress, never blocked.
            prepare_attempt(temp, workspace, task_id="TASK-001", output="docs/result.txt")
            mid = run_cli("next", "--workspace", str(workspace))
            self.assertIn("TASK-001", _ids(mid["in_progress"]))
            self.assertNotIn("TASK-001", _ids(mid["blocked"]))
            run_cli("verify", "TASK-001", "--workspace", str(workspace))

            after = run_cli("next", "--workspace", str(workspace))
            self.assertNotIn("TASK-002", _ids(after["waiting"]))
            self.assertIn("TASK-002", _ids(after["ready"]))
            self.assertNotIn("TASK-001", _ids(after["blocked"]))
            cleanup_worktree(repo, workspace, "TASK-001")

    def test_unresolved_unknown_and_decision_are_real_blocking(self):
        """C3: a declared blocking Unknown / required decision is blocked."""
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp, with_decision_unknown=True)
            register_contract(temp, workspace)
            view = run_cli("next", "--workspace", str(workspace))
            self.assertIn("TASK-001", _ids(view["blocked"]))
            self.assertNotIn("TASK-001", _ids(view["waiting"]))
            blocked = _entry(view, "blocked", "TASK-001")
            assert blocked is not None
            self.assertIn("blocking_unknown:UNK-001", blocked["blocking_reasons"])
            self.assertIn("required_decision_not_accepted:DEC-001", blocked["blocking_reasons"])
            self.assertIn("blocking_unknown:UNK-001", blocked["blockers"])

    def test_missing_required_evidence_is_real_blocking(self):
        """C4: required evidence that is absent or invalid blocks the task."""
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            db = StateDB(workspace / "runtime" / "state.sqlite")
            try:
                db.upsert_evidence({"id": "EVID-PLAN", "status": "invalidated"})
            finally:
                db.close()
            view = run_cli("next", "--workspace", str(workspace))
            self.assertIn("TASK-001", _ids(view["blocked"]))
            blocked = _entry(view, "blocked", "TASK-001")
            assert blocked is not None
            self.assertIn(
                "required_evidence_missing_or_invalid:EVID-PLAN", blocked["blocking_reasons"]
            )

    def test_gate_distinction_unevaluated_waits_failed_blocks(self):
        """C5: a future gate is waiting; an explicitly failed blocking gate blocks."""
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            bp = make_blueprint(temp / "blueprint", two_tasks=True)
            waves = yaml.safe_load((bp / "EXECUTION_WAVES.yaml").read_text(encoding="utf-8"))
            waves["waves"] = [
                {
                    "id": "W0",
                    "name": "first",
                    "sequence": 0,
                    "depends_on": [],
                    "workstream_ids": ["WS-01"],
                    "task_ids": ["TASK-001"],
                    "entry_gate_ids": [],
                    "exit_gate_ids": ["GATE-001"],
                    "rollback_boundary": "revert",
                    "definition_status": "active",
                },
                {
                    "id": "W1",
                    "name": "second",
                    "sequence": 1,
                    "depends_on": ["W0"],
                    "workstream_ids": ["WS-01"],
                    "task_ids": ["TASK-002"],
                    "entry_gate_ids": [],
                    "exit_gate_ids": ["GATE-001"],
                    "rollback_boundary": "revert",
                    "definition_status": "active",
                },
            ]
            (bp / "EXECUTION_WAVES.yaml").write_text(
                yaml.safe_dump(waves, sort_keys=False), encoding="utf-8"
            )
            tasks = yaml.safe_load((bp / "TASK_CARDS.yaml").read_text(encoding="utf-8"))
            tasks["tasks"][1]["wave_id"] = "W1"
            (bp / "TASK_CARDS.yaml").write_text(
                yaml.safe_dump(tasks, sort_keys=False), encoding="utf-8"
            )
            _, workspace = _bootstrap(temp, bp)
            register_contract(temp, workspace, task_id="TASK-002", output="docs/second.txt")

            view = run_cli("next", "--workspace", str(workspace))
            self.assertIn("TASK-002", _ids(view["waiting"]))
            self.assertNotIn("TASK-002", _ids(view["blocked"]))
            waiting = _entry(view, "waiting", "TASK-002")
            assert waiting is not None
            self.assertIn(
                "predecessor_wave_exit_gate_not_satisfied:W0:GATE-001",
                waiting["waiting_reasons"],
            )

            db = StateDB(workspace / "runtime" / "state.sqlite")
            try:
                db.set_gate("GATE-001", "FAIL", [], "receipt-path")
            finally:
                db.close()
            failed = run_cli("next", "--workspace", str(workspace))
            self.assertIn("TASK-002", _ids(failed["blocked"]))
            blocked = _entry(failed, "blocked", "TASK-002")
            assert blocked is not None
            self.assertIn(
                "predecessor_wave_exit_gate_not_satisfied:W0:GATE-001",
                blocked["blocking_reasons"],
            )

    def test_terminal_work_is_not_falsely_blocked(self):
        """C6: a COMPLETED task is terminal, not blocked."""
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            db = StateDB(workspace / "runtime" / "state.sqlite")
            try:
                db.transition_task("TASK-001", "ELIGIBLE")
                db.transition_task("TASK-001", "COMPLETED")
            finally:
                db.close()
            view = run_cli("next", "--workspace", str(workspace))
            self.assertNotIn("TASK-001", _ids(view["blocked"]))
            self.assertNotIn("TASK-001", _ids(view["waiting"]))
            self.assertIn("TASK-001", _ids(view["terminal"]))


if __name__ == "__main__":
    unittest.main()

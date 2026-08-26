from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import SCRIPTS

sys.path.insert(0, str(SCRIPTS))
from pec.state import StateDB


def _task_payload() -> dict:
    return {
        "id": "TASK-001",
        "title": "x",
        "wave_id": "W0",
        "workstream_id": "WS",
        "target_id": "T",
        "repository_id": "repo-a",
        "execution_kind": "repo_local",
        "objective": "x",
        "dependencies": [],
        "required_decisions": [],
        "blocking_unknowns": [],
        "required_evidence": [],
        "completion_gates": [],
        "authorization_ceiling": {"inspect": True},
        "required_acceptance": [],
        "required_validation_commands": [],
        "risk_tier": "T1",
        "definition_status": "ready",
        "source": {},
    }


class StateTransitionTest(unittest.TestCase):
    def test_invalid_transition_rejected(self):
        with TemporaryDirectory() as raw:
            db = StateDB(Path(raw) / "state.sqlite")
            try:
                db.upsert_task(_task_payload())
                # A new definition-ready task begins WAITING (ADR-0023), and
                # WAITING -> COMPLETED is not a legal direct edge.
                self.assertEqual(db.task("TASK-001")["runtime_state"], "WAITING")
                with self.assertRaises(ValueError):
                    db.transition_task("TASK-001", "COMPLETED")
            finally:
                db.close()

    def test_new_ready_task_initializes_waiting_not_blocked(self):
        with TemporaryDirectory() as raw:
            db = StateDB(Path(raw) / "state.sqlite")
            try:
                db.upsert_task(_task_payload())
                self.assertEqual(db.task("TASK-001")["runtime_state"], "WAITING")
            finally:
                db.close()

    def test_waiting_to_eligible_is_valid(self):
        with TemporaryDirectory() as raw:
            db = StateDB(Path(raw) / "state.sqlite")
            try:
                db.upsert_task(_task_payload())
                db.transition_task("TASK-001", "ELIGIBLE")
                self.assertEqual(db.task("TASK-001")["runtime_state"], "ELIGIBLE")
            finally:
                db.close()

    def test_waiting_cannot_jump_to_executing(self):
        with TemporaryDirectory() as raw:
            db = StateDB(Path(raw) / "state.sqlite")
            try:
                db.upsert_task(_task_payload())
                with self.assertRaises(ValueError):
                    db.transition_task("TASK-001", "EXECUTING")
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()

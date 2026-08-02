from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import SCRIPTS

sys.path.insert(0, str(SCRIPTS))
from pec.state import StateDB


class StateTransitionTest(unittest.TestCase):
    def test_invalid_transition_rejected(self):
        with TemporaryDirectory() as raw:
            db = StateDB(Path(raw) / "state.sqlite")
            try:
                db.upsert_task(
                    {
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
                )
                with self.assertRaises(ValueError):
                    db.transition_task("TASK-001", "COMPLETED")
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()

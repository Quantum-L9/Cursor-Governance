from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class ProgramControlTests(unittest.TestCase):
    def test_program_control_can_complete_only_after_gate_passes(self) -> None:
        # The universal fixture uses repo-local tasks; this test exercises the legal state edge directly.  # noqa: E501
        import sys

        from helpers import SCRIPTS

        sys.path.insert(0, str(SCRIPTS))
        from pec.state import StateDB

        with TemporaryDirectory() as raw:
            db = StateDB(Path(raw) / "state.sqlite")
            try:
                db.upsert_task(
                    {
                        "id": "TASK-PC",
                        "title": "lock",
                        "wave_id": "W0",
                        "workstream_id": "WS-01",
                        "target_id": "TARGET-001",
                        "repository_id": None,
                        "execution_kind": "program_control",
                        "objective": "lock",
                        "dependencies": [],
                        "required_decisions": [],
                        "blocking_unknowns": [],
                        "required_evidence": [],
                        "completion_gates": [],
                        "authorization_ceiling": {"inspect": True},
                        "required_acceptance": [],
                        "required_validation_commands": [],
                        "risk_tier": "T0",
                        "definition_status": "ready",
                        "source": {},
                    }
                )
                db.transition_task("TASK-PC", "ELIGIBLE")
                db.transition_task("TASK-PC", "COMPLETED")
                self.assertEqual(db.task("TASK-PC")["runtime_state"], "COMPLETED")
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()

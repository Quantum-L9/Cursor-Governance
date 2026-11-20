"""A declared evidence requirement collected at task validation is realized at verify.

Bootstrap materializes declared evidence requirements as ``planned`` rows. A
``collect_at_task_validation`` requirement (method ``command``) must become
available when the task its gates scope verifies PASSED_LOCAL — otherwise a
completion gate that requires it can only ever see it planned
(GATE_EVIDENCE_STALE) and stays UNKNOWN.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

# The gate discovers this suite from the repository root; the scripts dir
# (where the `pec` package lives) is not on the path there.
_SCRIPTS = Path(__file__).resolve().parents[1]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from pec.controller import _realize_planned_evidence  # noqa: E402
from pec.state import StateDB  # noqa: E402

BASE_SHA = "a" * 40
CANDIDATE = "b" * 40


def _evidence_item(**overrides):
    item = {
        "id": "EVID-WITNESS",
        "type": "test_result",
        "source": "repo-a",
        "revision": "UNKNOWN",
        "digest": None,
        "method": "command",
        "environment": "planning",
        "producer": "controller",
        "produced_at": "2026-08-01T13:00:00+00:00",
        "expires_at": None,
        "result": "INFORMATIONAL",
        "status": "planned",
        "supports": ["GATE-002"],
        "contradicts": [],
        "notes": "witnesses pass after the partition",
    }
    item.update(overrides)
    return item


def _lock_with(evidence):
    return {
        "gates": [
            {
                "id": "GATE-001",
                "scope": {"task_ids": ["TASK-001"]},
            },
            {
                "id": "GATE-002",
                "scope": {"task_ids": ["TASK-002"]},
            },
        ],
        "evidence": evidence,
    }


class EvidenceRealizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tempdir.name)
        runtime = self.workspace / "runtime"
        runtime.mkdir(parents=True)
        (runtime / "program-lock.json").write_text(
            json.dumps(_lock_with([_evidence_item()])), encoding="utf-8"
        )
        self.db = StateDB(runtime / "state.sqlite")
        self.db.upsert_evidence(_evidence_item())

    def tearDown(self) -> None:
        self.db.close()
        self.tempdir.cleanup()

    def _verification(self) -> dict:
        return {
            "verification_id": "VERIFY-test",
            "verified_at": "2026-08-02T12:00:00+00:00",
            "receipt_digest": "digest-test",
        }

    def test_planned_evidence_is_realized_for_the_task_its_gate_scopes(self) -> None:
        _realize_planned_evidence(
            self.db, self.workspace, "TASK-002", CANDIDATE, self._verification()
        )
        row = self.db.evidence("EVID-WITNESS")
        self.assertEqual(row["status"], "available")
        self.assertEqual(row["result"], "PASS")
        self.assertEqual(row["revision"], CANDIDATE)
        self.assertEqual(row["producer"], "Program Execution Controller")
        self.assertEqual(row["environment"], "local_worktree")

    def test_a_task_outside_the_gate_scope_does_not_realize_it(self) -> None:
        _realize_planned_evidence(
            self.db, self.workspace, "TASK-001", CANDIDATE, self._verification()
        )
        row = self.db.evidence("EVID-WITNESS")
        self.assertEqual(row["status"], "planned")

    def test_available_or_non_command_evidence_is_never_touched(self) -> None:
        self.db.upsert_evidence(_evidence_item(id="EVID-DONE", status="available"))
        self.db.upsert_evidence(_evidence_item(id="EVID-INSPECT", method="read_only_inspection"))
        _realize_planned_evidence(
            self.db, self.workspace, "TASK-002", CANDIDATE, self._verification()
        )
        self.assertEqual(self.db.evidence("EVID-DONE")["status"], "available")
        self.assertEqual(self.db.evidence("EVID-INSPECT")["status"], "planned")
        self.assertEqual(self.db.evidence("EVID-INSPECT")["revision"], "UNKNOWN")

    def test_a_missing_or_unreadable_lock_realizes_nothing(self) -> None:
        (self.workspace / "runtime" / "program-lock.json").write_text("{not json", encoding="utf-8")
        _realize_planned_evidence(
            self.db, self.workspace, "TASK-002", CANDIDATE, self._verification()
        )
        self.assertEqual(self.db.evidence("EVID-WITNESS")["status"], "planned")


if __name__ == "__main__":
    unittest.main()

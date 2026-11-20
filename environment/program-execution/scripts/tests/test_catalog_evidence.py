"""A passing task records the catalog evidence id its successor is waiting on."""

from __future__ import annotations

import inspect
import sys
import unittest
from pathlib import Path

PE_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = PE_ROOT / "core/program-execution-controller-template/scripts"
sys.path.insert(0, str(SCRIPTS))

from pec.controller import _satisfy_produced_catalog, verify_attempt  # noqa: E402


class _MemoryDB:
    def __init__(self) -> None:
        self.evidence = [
            {
                "id": "EVID-001",
                "freshness": "collect_at_admission",
                "status": "planned",
                "producer": "controller",
                "supports": [],
            },
            {
                "id": "EVID-002",
                "freshness": "collect_at_task_001",
                "status": "planned",
                "result": "INFORMATIONAL",
                "revision": "UNKNOWN",
                "producer": "worker",
                "supports": ["TASK-001"],
            },
        ]
        self.task_rows = [
            {
                "id": "TASK-001",
                "required_evidence": ["EVID-001"],
                "completion_gates": ["GATE-001"],
            }
        ]

    def evidence_items(self) -> list[dict]:
        return list(self.evidence)

    def tasks(self) -> list[dict]:
        return list(self.task_rows)

    def upsert_evidence(self, item: dict) -> None:
        self.evidence = [item if row["id"] == item["id"] else row for row in self.evidence]


class CatalogEvidenceTest(unittest.TestCase):
    def test_verify_pass_updates_the_catalog_id(self) -> None:
        source = inspect.getsource(verify_attempt)
        self.assertIn("_satisfy_produced_catalog", source)
        self.assertIn('verdict == "PASSED_LOCAL"', source)

    def test_pass_flips_the_produced_catalog_id_and_leaves_admission(self) -> None:
        db = _MemoryDB()
        _satisfy_produced_catalog(
            db,
            "TASK-001",
            candidate_sha="abc123",
            receipt_path=Path("receipts/TASK-001/verification.json"),
            produced_at="2026-11-19T00:00:00Z",
            digest="ab" * 32,
        )
        by_id = {item["id"]: item for item in db.evidence}
        self.assertEqual(by_id["EVID-001"]["status"], "planned")
        self.assertEqual(by_id["EVID-002"]["status"], "available")
        self.assertEqual(by_id["EVID-002"]["result"], "PASS")
        self.assertEqual(by_id["EVID-002"]["revision"], "abc123")


if __name__ == "__main__":
    unittest.main()

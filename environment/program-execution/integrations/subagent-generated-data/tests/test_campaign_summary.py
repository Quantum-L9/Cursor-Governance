"""RC-05 regressions: delivery acceptance is not persistence, retrieval, or
distillation. Downstream states the summary cannot observe stay UNKNOWN."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from adapters.common.imports import load_module

_MEMORY_STATUSES = (
    ("r-accepted", "u-accepted", "accepted"),
    ("r-duplicate", "u-duplicate", "duplicate"),
    ("r-deferred", "u-deferred", "deferred"),
    ("r-rejected", "u-rejected", "rejected"),
    ("r-submitted", "u-submitted", "submitted"),
)


def _seed_database(path: Path, campaign_id: str) -> None:
    connection = sqlite3.connect(str(path))
    try:
        connection.executescript(
            """
            CREATE TABLE processing_jobs (
              job_id TEXT PRIMARY KEY, campaign_id TEXT, state TEXT,
              packet_id TEXT, error_code TEXT, error_message TEXT);
            CREATE TABLE job_events (job_id TEXT, to_state TEXT);
            CREATE TABLE stage_snapshots (job_id TEXT, stage TEXT, payload_json TEXT);
            CREATE TABLE delivery_receipts (
              receipt_id TEXT, unit_id TEXT, job_id TEXT, route TEXT,
              destination_status TEXT, destination_reference TEXT, payload_json TEXT);
            CREATE TABLE delivery_attempts (job_id TEXT, status TEXT);
            CREATE TABLE dead_letters (job_id TEXT, status TEXT);
            """
        )
        connection.execute(
            "INSERT INTO processing_jobs VALUES ('job-1', ?, 'VALIDATED', 'p-1', NULL, NULL)",
            (campaign_id,),
        )
        connection.execute("INSERT INTO job_events VALUES ('job-1', 'VALIDATED')")
        for receipt_id, unit_id, status in _MEMORY_STATUSES:
            connection.execute(
                "INSERT INTO delivery_receipts VALUES (?, ?, 'job-1', 'memory', ?, NULL, '{}')",
                (receipt_id, unit_id, status),
            )
        connection.commit()
    finally:
        connection.close()


class CampaignSummaryTruthfulnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module(
            Path(__file__).resolve().parents[1] / "campaign_summary.py",
            "pes_test_campaign_summary",
        )

    def _summary(self) -> dict:
        with tempfile.TemporaryDirectory() as raw:
            runtime_root = Path(raw)
            database = runtime_root / "generated-data" / "pipeline.sqlite3"
            database.parent.mkdir(parents=True)
            _seed_database(database, "campaign-1")
            return self.module.build_summary(database_path=database, campaign_id="campaign-1")

    def test_delivery_statuses_never_claim_persistence_or_distillation(self) -> None:
        summary = self._summary()
        memory = summary["memory"]
        generated = summary["generated_data"]
        # Delivery accounting still works.
        self.assertEqual(memory["memory_candidates_accepted"], 1)
        self.assertEqual(memory["memory_candidates_deduplicated"], 1)
        self.assertEqual(memory["memory_candidates_deferred"], 1)
        self.assertEqual(memory["memory_candidates_quarantined"], 1)
        self.assertEqual(memory["memory_candidates_rejected"], 1)
        self.assertEqual(memory["memory_candidates_submitted"], 1)
        # Downstream truth was never observed: UNKNOWN, not a fabricated count.
        self.assertIsNone(memory["memory_units_persisted"])
        self.assertIsNone(memory["memory_units_retrievable"])
        self.assertIsNone(generated["distilled_units"])

    def test_brief_renders_unknown_downstream_states(self) -> None:
        brief = self.module.render_brief(self._summary())
        self.assertIn("distilled: UNKNOWN units", brief)
        self.assertIn("Memory persisted: UNKNOWN", brief)
        self.assertIn("retrievable: UNKNOWN", brief)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest
from pathlib import Path

from adapters.common.imports import load_module


class OutcomePublisherTests(unittest.TestCase):
    def test_projection_preserves_registered_agent(self) -> None:
        root = Path(__file__).resolve().parents[1]
        module = load_module(
            root / "receipt_projection.py",
            "pes_test_receipt_projection",
        )
        value = module.generated_data_packet(
            {"task_id": "TASK-1", "claimed_status": "completed"},
            repository="Quantum-L9/example",
            base_sha="1" * 40,
            agent_id="claude-code",
        )
        self.assertEqual(value["identity"]["agent_id"], "claude-code")
        self.assertEqual(value["identity"]["repository"], "Quantum-L9/example")

    def test_no_second_outbox_or_state_store(self) -> None:
        source = (Path(__file__).resolve().parents[1] / "outcome_publisher.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("class PipelineStateStore", source)
        self.assertNotIn("FileOutboxTransport", source)
        self.assertIn("GeneratedDataProcessor", source)


if __name__ == "__main__":
    unittest.main()

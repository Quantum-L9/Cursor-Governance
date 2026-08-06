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

    def test_publication_flags_are_evidence_derived(self) -> None:
        import inspect

        module = load_module(
            Path(__file__).resolve().parents[1] / "outcome_publisher.py",
            "pes_test_outcome_publisher",
        )
        source = inspect.getsource(module.OutcomePublisher.publish)
        # The processor call must forward the evidence-derived variables, not
        # hard-coded truths.
        self.assertIn("independent_validation_present=independent_validation_present", source)
        self.assertIn("designated_authority_approval=designated_authority_approval", source)
        # publish() must expose both flags and fail closed (default False).
        signature = inspect.signature(module.OutcomePublisher.publish)
        for name in ("independent_validation_present", "designated_authority_approval"):
            self.assertIn(name, signature.parameters)
            self.assertIs(signature.parameters[name].default, False)


if __name__ == "__main__":
    unittest.main()

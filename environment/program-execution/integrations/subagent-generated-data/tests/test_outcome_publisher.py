from __future__ import annotations

import importlib.util
import inspect
import sys
import unittest
from pathlib import Path

from adapters.common.imports import load_module


class OutcomePublisherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]

    def test_projection_is_canonical_and_stable(self) -> None:
        projection = load_module(
            self.root / "receipt_projection.py",
            "pes_test_receipt_projection",
        )
        receipt = {
            "task_id": "TASK-1",
            "claimed_status": "completed",
            "generated_at": "2026-08-23T12:00:00Z",
        }
        first = projection.generated_data_packet(
            receipt,
            repository="Quantum-L9/example",
            base_sha="1" * 40,
            agent_id="claude-code",
            campaign_id="campaign-1",
            graph_id="graph-1",
        )
        second = projection.generated_data_packet(
            receipt,
            repository="Quantum-L9/example",
            base_sha="1" * 40,
            agent_id="claude-code",
            campaign_id="campaign-1",
            graph_id="graph-1",
        )
        self.assertEqual(first, second)
        self.assertEqual(first["identity"]["agent_id"], "claude-code")
        self.assertEqual(first["identity"]["base_sha"], "1" * 40)
        self.assertEqual(first["primary_result"]["completion_status"], "completed")
        self.assertIn("packet_id", first)
        self.assertIn("generated_data_units", first)
        self.assertNotIn("generated_units", first)

        validator_path = self.root.parents[2] / "agents/generated-data/runtime/packet_validator.py"
        runtime = validator_path.parent
        if str(runtime) not in sys.path:
            sys.path.insert(0, str(runtime))
        spec = importlib.util.spec_from_file_location("pes_test_packet_validator", validator_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(validator_path)
        validator = importlib.util.module_from_spec(spec)
        # Register before executing: the validator declares @dataclass types and
        # dataclasses resolves them through sys.modules[cls.__module__].
        sys.modules[spec.name] = validator
        try:
            spec.loader.exec_module(validator)
        except BaseException:
            sys.modules.pop(spec.name, None)
            raise
        report = validator.PacketValidator().validate(first)
        self.assertTrue(report.valid, report.to_dict())

    def test_projection_refuses_unstable_missing_timestamp(self) -> None:
        projection = load_module(
            self.root / "receipt_projection.py",
            "pes_test_receipt_projection_missing_time",
        )
        with self.assertRaises(ValueError):
            projection.generated_data_packet(
                {"task_id": "TASK-1", "claimed_status": "completed"},
                repository="Quantum-L9/example",
                base_sha="1" * 40,
                agent_id="claude-code",
            )

    def test_publisher_reuses_canonical_ingress(self) -> None:
        source = (self.root / "outcome_publisher.py").read_text(encoding="utf-8")
        self.assertNotIn("class PipelineStateStore", source)
        self.assertNotIn("FileOutboxTransport", source)
        self.assertIn("ingest_packet", source)
        self.assertNotIn("GeneratedDataProcessor(", source)

    def test_publication_flags_and_recurrence_are_evidence_derived(self) -> None:
        module = load_module(
            self.root / "outcome_publisher.py",
            "pes_test_outcome_publisher",
        )
        source = inspect.getsource(module.OutcomePublisher.publish)
        self.assertIn(
            "independent_validation_present=independent_validation_present",
            source,
        )
        self.assertIn(
            "designated_authority_approval=designated_authority_approval",
            source,
        )
        self.assertIn("recurrence_counts=dict(recurrence_counts or {})", source)
        signature = inspect.signature(module.OutcomePublisher.publish)
        for name in (
            "independent_validation_present",
            "designated_authority_approval",
            "recurrence_counts",
        ):
            self.assertIn(name, signature.parameters)


if __name__ == "__main__":
    unittest.main()

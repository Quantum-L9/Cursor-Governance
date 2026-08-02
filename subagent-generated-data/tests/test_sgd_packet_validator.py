"""Conformance and negative tests for the packet validator (law §12, §31)."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from runtime.packet_validator import validate_packet

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _valid() -> dict:
    return json.loads((FIXTURES / "valid_packet.json").read_text(encoding="utf-8"))


class ConformanceTests(unittest.TestCase):
    def test_golden_valid_packet_passes(self) -> None:
        result = validate_packet(_valid())
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(result.errors, ())

    def test_empty_assessment_declaration_passes(self) -> None:
        packet = _valid()
        packet["generated_data_units"] = []
        packet["generated_data_assessment"] = {
            "reusable_data_found": False,
            "reason": "task produced only transient information",
        }
        result = validate_packet(packet)
        self.assertTrue(result.ok, result.errors)


class NegativeTests(unittest.TestCase):
    def test_self_promotion_rejected(self) -> None:
        packet = json.loads((FIXTURES / "self_promoting_packet.json").read_text(encoding="utf-8"))
        result = validate_packet(packet)
        self.assertTrue(result.rejected)
        self.assertIn("SGD-003", result.invariants_violated)

    def test_silence_without_assessment_rejected(self) -> None:
        packet = _valid()
        packet["generated_data_units"] = []
        result = validate_packet(packet)
        self.assertTrue(result.rejected)
        self.assertIn("SGD-001", result.invariants_violated)

    def test_reusable_data_found_false_without_reason_rejected(self) -> None:
        packet = _valid()
        packet["generated_data_units"] = []
        packet["generated_data_assessment"] = {"reusable_data_found": False}
        result = validate_packet(packet)
        self.assertTrue(result.rejected)
        self.assertIn("SGD-009", result.invariants_violated)

    def test_observed_unit_without_evidence_rejected(self) -> None:
        packet = _valid()
        packet["generated_data_units"][0]["source_evidence"] = []
        result = validate_packet(packet)
        self.assertTrue(result.rejected)
        self.assertIn("SGD-004", result.invariants_violated)

    def test_unit_without_scope_rejected(self) -> None:
        packet = _valid()
        packet["generated_data_units"][0]["scope"] = {}
        result = validate_packet(packet)
        self.assertTrue(result.rejected)
        self.assertIn("SGD-005", result.invariants_violated)

    def test_reuse_route_without_invalidation_rejected(self) -> None:
        packet = _valid()
        packet["generated_data_units"][0]["invalidation_conditions"] = []
        result = validate_packet(packet)
        self.assertTrue(result.rejected)
        self.assertIn("SGD-007", result.invariants_violated)

    def test_unknown_without_owner_rejected(self) -> None:
        packet = _valid()
        broken = copy.deepcopy(packet)
        broken["unresolved_unknowns"][0].pop("owner")
        result = validate_packet(broken)
        self.assertTrue(result.rejected)
        self.assertIn("SGD-008", result.invariants_violated)

    def test_contested_unit_direct_to_memory_rejected(self) -> None:
        packet = _valid()
        packet["generated_data_units"][0]["epistemic_status"] = "contested"
        result = validate_packet(packet)
        self.assertTrue(result.rejected)
        self.assertIn("SGD-016", result.invariants_violated)


if __name__ == "__main__":
    unittest.main()

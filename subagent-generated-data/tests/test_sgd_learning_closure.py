"""Learning closure tests (law §25)."""

from __future__ import annotations

import unittest

from runtime.learning_closure import CampaignLearningState, evaluate_closure


class LearningClosureTests(unittest.TestCase):
    def test_clean_state_can_seal(self) -> None:
        state = CampaignLearningState(
            campaign_id="camp-1",
            required_packet_ids={"p1"},
            received_packet_ids={"p1"},
        )
        result = evaluate_closure(state)
        self.assertTrue(result.can_seal)
        self.assertEqual(result.failed_requirements, ())

    def test_missing_packet_blocks_seal(self) -> None:
        state = CampaignLearningState(
            campaign_id="camp-1",
            required_packet_ids={"p1", "p2"},
            received_packet_ids={"p1"},
        )
        result = evaluate_closure(state)
        self.assertFalse(result.can_seal)
        self.assertIn("required_packets_received", result.failed_requirements)

    def test_invalid_packet_blocks_schema_and_provenance(self) -> None:
        state = CampaignLearningState(
            campaign_id="camp-1",
            received_packet_ids={"p1"},
            invalid_packet_ids={"p1"},
        )
        result = evaluate_closure(state)
        self.assertFalse(result.can_seal)
        self.assertIn("packets_schema_valid", result.failed_requirements)
        self.assertIn("provenance_validated", result.failed_requirements)

    def test_unprocessed_high_value_blocks_seal(self) -> None:
        state = CampaignLearningState(
            campaign_id="camp-1",
            high_value_unprocessed={"pkt-x"},
        )
        result = evaluate_closure(state)
        self.assertFalse(result.can_seal)
        self.assertEqual(result.unprocessed_high_value_packets, ("pkt-x",))

    def test_rejected_residue_needs_reason(self) -> None:
        state = CampaignLearningState(
            campaign_id="camp-1",
            rejected_without_reason={"u-9"},
        )
        result = evaluate_closure(state)
        self.assertFalse(result.can_seal)
        self.assertIn("rejected_residue_has_reason", result.failed_requirements)


if __name__ == "__main__":
    unittest.main()

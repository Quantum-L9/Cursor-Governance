from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

TEST_FILE = Path(__file__).resolve()
BASE = TEST_FILE.parents[2]
RUNTIME = BASE / "runtime"
FIXTURES = BASE / "tests" / "fixtures"
sys.path.insert(0, str(RUNTIME))
from harvester import SubagentDataHarvester
from learning_closure import (
    LearningClosureEvaluator,
)
from packet_validator import PacketValidator
from promotion_gate import PromotionGate
from routing_engine import RoutingEngine


class GoldenPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.packet = json.loads((FIXTURES / "valid-recon-packet.json").read_text(encoding="utf-8"))

    def test_golden_packet_is_deterministic(self) -> None:
        harvester = SubagentDataHarvester()
        first = harvester.harvest(self.packet).to_dict()
        second = harvester.harvest(self.packet).to_dict()
        self.assertEqual(first, second)

    def test_complete_learning_closure(self) -> None:
        validation = PacketValidator().validate(self.packet).to_dict()
        harvest = SubagentDataHarvester().harvest(self.packet).to_dict()
        routing_engine = RoutingEngine()
        routes = routing_engine.route_many(harvest["harvested_units"])
        promotion_gate = PromotionGate()
        promotions = promotion_gate.evaluate_many(
            harvested_units=harvest["harvested_units"],
            routing_decisions=[route.to_dict() for route in routes],
            independent_validation_present=True,
            designated_authority_approval=True,
            recurrence_counts={unit["unit_id"]: 2 for unit in harvest["harvested_units"]},
        )
        closure = LearningClosureEvaluator().evaluate(
            campaign_id="campaign-001",
            expected_action_ids=["recon-001"],
            packets=[self.packet],
            validation_reports=[validation],
            harvest_results=[harvest],
            routing_decisions=[route.to_dict() for route in routes],
            promotion_results=[promotion.to_dict() for promotion in promotions],
            evidence_archive_complete=True,
        )
        self.assertEqual(
            closure.status,
            "closed",
            closure.to_dict(),
        )

    def test_learning_closure_blocks_missing_packet(
        self,
    ) -> None:
        closure = LearningClosureEvaluator().evaluate(
            campaign_id="campaign-001",
            expected_action_ids=[
                "recon-001",
                "verifier-001",
            ],
            packets=[self.packet],
            validation_reports=[PacketValidator().validate(self.packet).to_dict()],
            harvest_results=[],
            routing_decisions=[],
            promotion_results=[],
            evidence_archive_complete=True,
        )
        self.assertEqual(
            closure.status,
            "blocked",
        )
        failed_checks = {check.check_id for check in closure.checks if not check.passed}
        self.assertIn(
            "SGD-CLOSE-001",
            failed_checks,
        )


if __name__ == "__main__":
    unittest.main()

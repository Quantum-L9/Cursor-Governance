from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

TEST_FILE = Path(__file__).resolve()
BASE = TEST_FILE.parents[2]
RUNTIME = BASE / "runtime"
ADAPTERS = BASE / "adapters"
FIXTURES = BASE / "tests" / "fixtures"
sys.path.insert(0, str(RUNTIME))
sys.path.insert(0, str(ADAPTERS))
from graphiti_memory import (
    FileOutboxTransport,
    GraphitiAdapterError,
    GraphitiMemoryAdapter,
)
from harvester import SubagentDataHarvester
from packet_validator import (
    PacketValidationFailure,
    PacketValidator,
)
from promotion_gate import PromotionGate
from routing_engine import RoutingEngine


class FailClosedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.valid_packet = json.loads(
            (FIXTURES / "valid-recon-packet.json").read_text(encoding="utf-8")
        )

    def test_harvester_rejects_invalid_packet(self) -> None:
        invalid = json.loads(
            (FIXTURES / "invalid-missing-evidence-packet.json").read_text(encoding="utf-8")
        )
        with self.assertRaises(PacketValidationFailure):
            SubagentDataHarvester().harvest(invalid)

    def test_graphiti_rejects_non_memory_route(
        self,
    ) -> None:
        harvest = SubagentDataHarvester().harvest(self.valid_packet)
        unit = harvest.harvested_units[0].to_dict()
        bad_route = {
            "decision_id": "route-bad",
            "unit_id": unit["unit_id"],
            "route": "contracts",
            "destination": "task-contracts",
            "status": "eligible",
            "reason_codes": [],
            "required_authority": "runtime",
            "requires_independent_validation": False,
            "decision_hash": "bad",
        }
        promotion = {
            "promotion_id": "promotion-bad",
            "unit_id": unit["unit_id"],
            "route": "contracts",
            "decision": "promote",
            "risk_class": "low",
            "authority_required": "runtime",
            "reasons": [],
            "conditions": [],
            "promotion_hash": "bad",
        }
        adapter = GraphitiMemoryAdapter(FileOutboxTransport())
        with self.assertRaises(GraphitiAdapterError):
            adapter.compile_candidate(
                harvested_unit=unit,
                routing_decision=bad_route,
                promotion_result=promotion,
                packet=self.valid_packet,
            )

    def test_graphiti_rejects_deferred_promotion(
        self,
    ) -> None:
        harvest = SubagentDataHarvester().harvest(self.valid_packet)
        unit = harvest.harvested_units[0].to_dict()
        route = RoutingEngine().route(unit)[0]
        promotion = PromotionGate().evaluate(
            harvested_unit=unit,
            routing_decision=route.to_dict(),
            independent_validation_present=False,
            recurrence_count=1,
        )
        self.assertNotEqual(
            promotion.decision,
            "promote",
        )
        adapter = GraphitiMemoryAdapter(FileOutboxTransport())
        with self.assertRaises(GraphitiAdapterError):
            adapter.compile_candidate(
                harvested_unit=unit,
                routing_decision=route.to_dict(),
                promotion_result=promotion.to_dict(),
                packet=self.valid_packet,
            )

    def test_outbox_rejects_candidate_id_collision(
        self,
    ) -> None:
        candidate_id = "memcand-collision"
        transport = FileOutboxTransport()
        target = transport.outbox_dir / f"{candidate_id}.json"
        if target.exists():
            target.unlink()
        try:
            transport.deliver(
                {
                    "candidate_id": candidate_id,
                    "value": 1,
                }
            )
            with self.assertRaises(GraphitiAdapterError):
                transport.deliver(
                    {
                        "candidate_id": candidate_id,
                        "value": 2,
                    }
                )
        finally:
            if target.exists():
                target.unlink()

    def test_contested_memory_is_not_eligible(
        self,
    ) -> None:
        packet = copy.deepcopy(self.valid_packet)
        packet["generated_data_units"][0]["epistemic_status"] = "contested"
        harvest = SubagentDataHarvester().harvest(packet)
        unit = harvest.harvested_units[0].to_dict()
        decision = RoutingEngine().route(unit)[0]
        self.assertEqual(
            decision.status,
            "deferred",
        )

    def test_producing_role_cannot_self_promote(
        self,
    ) -> None:
        packet = copy.deepcopy(self.valid_packet)
        packet["generated_data_units"][0]["self_promoted"] = True
        report = PacketValidator().validate(packet)
        self.assertFalse(report.valid)
        codes = {finding.code for finding in report.findings}
        self.assertIn("SGD-SELF-PROMOTION-FORBIDDEN", codes)


if __name__ == "__main__":
    unittest.main()

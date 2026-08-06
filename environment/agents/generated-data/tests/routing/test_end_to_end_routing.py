from __future__ import annotations

import json
import sys
import tempfile
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
    GraphitiMemoryAdapter,
)
from harvester import SubagentDataHarvester
from promotion_gate import PromotionGate
from routing_engine import RoutingEngine


class EndToEndRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.packet = json.loads((FIXTURES / "valid-recon-packet.json").read_text(encoding="utf-8"))

    def test_packet_harvests_two_units(self) -> None:
        result = SubagentDataHarvester().harvest(self.packet)
        self.assertEqual(
            len(result.harvested_units),
            2,
        )
        self.assertEqual(
            result.duplicate_unit_ids,
            (),
        )

    def test_repository_fact_routes_to_memory(self) -> None:
        harvest = SubagentDataHarvester().harvest(self.packet)
        memory_unit = next(
            unit
            for unit in harvest.harvested_units
            if unit.original_unit["primary_class"] == "repository_fact"
        )
        decisions = RoutingEngine().route(memory_unit.to_dict())
        self.assertEqual(len(decisions), 1)
        self.assertEqual(
            decisions[0].route,
            "memory",
        )
        self.assertEqual(
            decisions[0].status,
            "eligible",
        )

    def test_contract_gap_requires_medium_risk_control(
        self,
    ) -> None:
        harvest = SubagentDataHarvester().harvest(self.packet)
        contract_unit = next(
            unit
            for unit in harvest.harvested_units
            if unit.original_unit["primary_class"] == "task_contract_gap"
        )
        route = RoutingEngine().route(contract_unit.to_dict())[0]
        result = PromotionGate().evaluate(
            harvested_unit=contract_unit.to_dict(),
            routing_decision=route.to_dict(),
            independent_validation_present=False,
            recurrence_count=1,
        )
        self.assertEqual(
            result.decision,
            "defer",
        )
        self.assertIn(
            "medium_risk_requires_validation_or_recurrence",
            result.reasons,
        )

    def test_memory_candidate_delivery_to_outbox(
        self,
    ) -> None:
        harvest = SubagentDataHarvester().harvest(self.packet)
        memory_unit = next(
            unit
            for unit in harvest.harvested_units
            if unit.original_unit["primary_class"] == "repository_fact"
        )
        route = RoutingEngine().route(memory_unit.to_dict())[0]
        promotion = PromotionGate().evaluate(
            harvested_unit=memory_unit.to_dict(),
            routing_decision=route.to_dict(),
            independent_validation_present=True,
            recurrence_count=2,
        )
        self.assertEqual(
            promotion.decision,
            "promote",
        )
        # Isolate the outbox in a temp dir so this test is order-independent of
        # any other suite that delivers the same deterministic candidate id.
        with tempfile.TemporaryDirectory() as temp:
            adapter = GraphitiMemoryAdapter(FileOutboxTransport(temp))
            candidate = adapter.compile_candidate(
                harvested_unit=memory_unit.to_dict(),
                routing_decision=route.to_dict(),
                promotion_result=promotion.to_dict(),
                packet=self.packet,
            )
            delivery = adapter.deliver(candidate)
            self.assertEqual(
                delivery.status,
                "enqueued",
            )
            stored_path = Path(delivery.destination_reference)
            self.assertTrue(stored_path.is_file())
            stored = json.loads(stored_path.read_text(encoding="utf-8"))
            self.assertEqual(
                stored["kind"],
                "MemoryCandidate",
            )
            self.assertEqual(
                stored["governance"]["authority_class"],
                "advisory",
            )
            self.assertFalse(stored["governance"]["may_override_repository_state"])


if __name__ == "__main__":
    unittest.main()

"""Routing + golden pipeline tests for the law §29 enforcement sequence."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from runtime.evidence_archive import EvidenceArchive
from runtime.models import (
    EpistemicStatus,
    GeneratedDataClass,
    GeneratedDataUnit,
    PromotionDecision,
    RiskClass,
    RouteName,
    Visibility,
)
from runtime.pipeline import PipelineConfig, process_packet
from runtime.routing_engine import decide

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _valid() -> dict:
    return json.loads((FIXTURES / "valid_packet.json").read_text(encoding="utf-8"))


def _unit(
    unit_id: str,
    cls: GeneratedDataClass,
    *,
    routes: tuple[RouteName, ...],
    status: EpistemicStatus = EpistemicStatus.OBSERVED,
) -> GeneratedDataUnit:
    return GeneratedDataUnit(
        unit_id=unit_id,
        primary_class=cls,
        epistemic_status=status,
        statement=f"statement for {unit_id}",
        scope={"repository": "r"},
        confidence=0.8,
        source_evidence=("evidence",),
        proposed_routes=routes,
        invalidation_conditions=("relevant_path_changed",),
        visibility=Visibility.REPOSITORY_LOCAL,
    )


class GoldenPipelineTests(unittest.TestCase):
    def test_valid_packet_accepted_and_archived(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive = EvidenceArchive(tmp)
            result = process_packet(_valid(), archive=archive)
        self.assertTrue(result.accepted)
        self.assertEqual(result.gate_violations, ())
        self.assertIsNotNone(result.archived_path)

    def test_low_risk_promotes_medium_defers_evidence_retains(self) -> None:
        result = process_packet(_valid())
        by_id = {d.unit_id: d for d in result.routing_decisions}
        # low-risk repository_fact -> promote
        self.assertEqual(by_id["u-repo-fact-1"].promotion_decision, PromotionDecision.PROMOTE)
        # medium-risk execution_procedure with no authority/recurrence -> defer
        self.assertEqual(by_id["u-proc-1"].promotion_decision, PromotionDecision.DEFER)
        # evidence-only -> retain (no future-execution influence)
        self.assertEqual(by_id["u-evidence-1"].promotion_decision, PromotionDecision.RETAIN)

    def test_authority_and_recurrence_promote_medium(self) -> None:
        config = PipelineConfig(authority_granted=True, recurring_unit_ids=frozenset({"u-proc-1"}))
        result = process_packet(_valid(), config=config)
        by_id = {d.unit_id: d for d in result.routing_decisions}
        self.assertEqual(by_id["u-proc-1"].promotion_decision, PromotionDecision.PROMOTE)

    def test_rejected_packet_does_not_route(self) -> None:
        packet = _valid()
        packet["generated_data_units"][0]["scope"] = {}
        result = process_packet(packet)
        self.assertFalse(result.accepted)
        self.assertEqual(result.routing_decisions, ())


class RoutingUnitTests(unittest.TestCase):
    def test_high_risk_defers_without_authority(self) -> None:
        unit = _unit(
            "u-arch",
            GeneratedDataClass.ARCHITECTURE_BOUNDARY,
            routes=(RouteName.ARCHITECTURE,),
        )
        decision = decide(unit, authority_granted=False)
        self.assertEqual(decision.risk_class, RiskClass.HIGH)
        self.assertEqual(decision.promotion_decision, PromotionDecision.DEFER)

    def test_high_risk_promotes_with_authority(self) -> None:
        unit = _unit(
            "u-arch",
            GeneratedDataClass.ARCHITECTURE_BOUNDARY,
            routes=(RouteName.ARCHITECTURE,),
        )
        decision = decide(unit, authority_granted=True)
        self.assertEqual(decision.promotion_decision, PromotionDecision.PROMOTE)
        self.assertTrue(decision.authority_satisfied)

    def test_blocking_conflict_forces_defer(self) -> None:
        unit = _unit(
            "u-fact",
            GeneratedDataClass.REPOSITORY_FACT,
            routes=(RouteName.MEMORY,),
        )
        decision = decide(unit, blocking_conflict_ids=("conflict-001",))
        self.assertEqual(decision.promotion_decision, PromotionDecision.DEFER)

    def test_reject_route_yields_reject_decision(self) -> None:
        unit = _unit(
            "u-noise",
            GeneratedDataClass.REPOSITORY_FACT,
            routes=(RouteName.REJECT,),
        )
        decision = decide(unit)
        self.assertEqual(decision.promotion_decision, PromotionDecision.REJECT)
        self.assertIsNotNone(decision.rejection_reason)


class DedupConflictTests(unittest.TestCase):
    def test_duplicate_units_collapse(self) -> None:
        packet = _valid()
        dup = dict(packet["generated_data_units"][0])
        dup["unit_id"] = "u-repo-fact-dup"
        dup["confidence"] = 0.5
        packet["generated_data_units"].append(dup)
        result = process_packet(packet)
        self.assertTrue(any(link[1] == "u-repo-fact-dup" for link in result.dedup_links))
        routed_ids = {d.unit_id for d in result.routing_decisions}
        self.assertNotIn("u-repo-fact-dup", routed_ids)


if __name__ == "__main__":
    unittest.main()

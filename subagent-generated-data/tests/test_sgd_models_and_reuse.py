"""Model round-trip, reuse tracking, and invalidation tests (law §22, §24)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from runtime.invalidation import evaluate_lifecycle, excluded_from_context
from runtime.models import (
    GeneratedDataUnit,
    LifecycleState,
    SubagentDataPacket,
)
from runtime.reuse_tracking import ReuseEvent, ReuseLedger

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _unit_with(conditions: tuple[str, ...]) -> GeneratedDataUnit:
    from runtime.models import EpistemicStatus, GeneratedDataClass

    return GeneratedDataUnit(
        unit_id="u",
        primary_class=GeneratedDataClass.REPOSITORY_FACT,
        epistemic_status=EpistemicStatus.OBSERVED,
        statement="s",
        scope={"repository": "r"},
        confidence=0.9,
        source_evidence=("e",),
        invalidation_conditions=conditions,
    )


class ModelTests(unittest.TestCase):
    def test_packet_round_trip(self) -> None:
        raw = json.loads((FIXTURES / "valid_packet.json").read_text(encoding="utf-8"))
        packet = SubagentDataPacket.from_dict(raw)
        self.assertEqual(packet.packet_id, "pkt-recon-001")
        self.assertEqual(len(packet.generated_data_units), 3)
        self.assertEqual(len(packet.unresolved_unknowns), 1)
        self.assertEqual(packet.identity.role, "recon")


class InvalidationTests(unittest.TestCase):
    def test_no_matching_event_stays_valid(self) -> None:
        unit = _unit_with(("relevant_path_changed",))
        state = evaluate_lifecycle(unit, frozenset({"dependency_upgraded"}))
        self.assertEqual(state, LifecycleState.VALID)

    def test_matching_event_makes_revalidatable(self) -> None:
        unit = _unit_with(("relevant_path_changed",))
        state = evaluate_lifecycle(unit, frozenset({"relevant_path_changed"}))
        self.assertEqual(state, LifecycleState.STALE_REVALIDATABLE)

    def test_recompute_event(self) -> None:
        unit = _unit_with(("architecture_owner_changed",))
        state = evaluate_lifecycle(unit, frozenset({"architecture_owner_changed"}))
        self.assertEqual(state, LifecycleState.STALE_RECOMPUTE_REQUIRED)

    def test_superseded_and_contested_excluded_from_context(self) -> None:
        self.assertTrue(excluded_from_context(LifecycleState.SUPERSEDED))
        self.assertTrue(excluded_from_context(LifecycleState.CONTESTED))
        self.assertFalse(excluded_from_context(LifecycleState.VALID))


class ReuseTrackingTests(unittest.TestCase):
    def _event(self, unit_id: str, outcome: str, valid: bool = True) -> ReuseEvent:
        return ReuseEvent(
            unit_id=unit_id,
            consuming_campaign="c2",
            consuming_action="a2",
            consuming_agent_role="executor",
            injection_method="context",
            outcome=outcome,
            validity_confirmed=valid,
        )

    def test_reuse_rate_counts_only_promoted(self) -> None:
        ledger = ReuseLedger()
        ledger.record(self._event("u1", "accelerated_execution"))
        rate = ledger.reuse_rate({"u1", "u2"})
        self.assertEqual(rate, 0.5)

    def test_effective_reuse_requires_behavioral_effect(self) -> None:
        ledger = ReuseLedger()
        ledger.record(self._event("u1", "accelerated_execution"))
        ledger.record(self._event("u2", "no_observable_value"))
        self.assertEqual(ledger.effective_reuse_rate(), 0.5)

    def test_repeatedly_valueless_flagged(self) -> None:
        ledger = ReuseLedger()
        ledger.record(self._event("u3", "no_observable_value"))
        ledger.record(self._event("u3", "stale"))
        self.assertIn("u3", ledger.repeatedly_valueless(threshold=2))


if __name__ == "__main__":
    unittest.main()

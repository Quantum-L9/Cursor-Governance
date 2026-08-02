"""Learning closure (law §25): a campaign may not seal until this passes.

Execution completion and learning closure are separate (law §25). This evaluates
the ten closure requirements and reports whether the campaign may seal, plus any
unprocessed high-value packets that block it (SGD-010).
"""

from __future__ import annotations

from dataclasses import dataclass, field

REQUIREMENTS: tuple[str, ...] = (
    "required_packets_received",
    "packets_schema_valid",
    "provenance_validated",
    "generated_units_classified",
    "routing_decisions_recorded",
    "promotion_decisions_recorded",
    "unresolved_unknowns_registered",
    "high_value_conflicts_routed",
    "rejected_residue_has_reason",
    "evidence_archive_complete",
)


@dataclass(frozen=True, slots=True)
class ClosureResult:
    campaign_id: str
    requirements: dict[str, bool]
    can_seal: bool
    failed_requirements: tuple[str, ...]
    unprocessed_high_value_packets: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "campaign_id": self.campaign_id,
            "requirements": dict(self.requirements),
            "can_seal": self.can_seal,
            "failed_requirements": list(self.failed_requirements),
            "unprocessed_high_value_packets": list(self.unprocessed_high_value_packets),
        }


@dataclass
class CampaignLearningState:
    """Accumulated generated-data processing state for one campaign."""

    campaign_id: str
    required_packet_ids: set[str] = field(default_factory=set)
    received_packet_ids: set[str] = field(default_factory=set)
    invalid_packet_ids: set[str] = field(default_factory=set)
    units_classified: bool = True
    routing_recorded: bool = True
    promotion_recorded: bool = True
    unknowns_registered: bool = True
    high_value_conflicts_routed: bool = True
    rejected_without_reason: set[str] = field(default_factory=set)
    evidence_archive_complete: bool = True
    high_value_unprocessed: set[str] = field(default_factory=set)


def evaluate_closure(state: CampaignLearningState) -> ClosureResult:
    requirements = {
        "required_packets_received": state.required_packet_ids <= state.received_packet_ids,
        "packets_schema_valid": not state.invalid_packet_ids,
        "provenance_validated": not state.invalid_packet_ids,
        "generated_units_classified": state.units_classified,
        "routing_decisions_recorded": state.routing_recorded,
        "promotion_decisions_recorded": state.promotion_recorded,
        "unresolved_unknowns_registered": state.unknowns_registered,
        "high_value_conflicts_routed": state.high_value_conflicts_routed,
        "rejected_residue_has_reason": not state.rejected_without_reason,
        "evidence_archive_complete": state.evidence_archive_complete,
    }
    failed = tuple(name for name in REQUIREMENTS if not requirements[name])
    can_seal = not failed and not state.high_value_unprocessed
    return ClosureResult(
        campaign_id=state.campaign_id,
        requirements=requirements,
        can_seal=can_seal,
        failed_requirements=failed,
        unprocessed_high_value_packets=tuple(sorted(state.high_value_unprocessed)),
    )

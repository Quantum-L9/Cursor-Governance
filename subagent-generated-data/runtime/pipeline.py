"""Runtime enforcement sequence (law §29).

subagent artifact submitted -> primary artifact validated -> packet validated ->
packet persisted as evidence -> units harvested -> classified -> duplicates and
conflicts checked -> routes selected -> promotion decisions made -> learning
state updated.

A packet validation failure rejects generated-data processing and blocks learning
closure, but never falsely invalidates a correct primary artifact (law §29).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .classifier import classify
from .conflict_handler import ConflictResult, find_conflicts
from .deduplicator import DedupResult, deduplicate
from .evidence_archive import EvidenceArchive
from .harvester import harvest
from .models import PromotionDecision, SubagentDataPacket
from .packet_validator import ValidationResult, validate_packet
from .promotion_gate import gate_violations
from .routing_engine import RoutingDecision, route_units


@dataclass(frozen=True, slots=True)
class PipelineResult:
    packet_id: str
    accepted: bool
    validation: ValidationResult
    routing_decisions: tuple[RoutingDecision, ...] = ()
    conflicts: tuple[str, ...] = ()
    dedup_links: tuple[tuple[str, str], ...] = ()
    gate_violations: tuple[str, ...] = ()
    archived_path: str | None = None

    @property
    def promoted_unit_ids(self) -> tuple[str, ...]:
        return tuple(
            d.unit_id
            for d in self.routing_decisions
            if d.promotion_decision is PromotionDecision.PROMOTE
        )


@dataclass
class PipelineConfig:
    authority_granted: bool = False
    recurring_unit_ids: frozenset[str] = field(default_factory=frozenset)


def process_packet(
    raw: dict[str, Any],
    *,
    archive: EvidenceArchive | None = None,
    config: PipelineConfig | None = None,
) -> PipelineResult:
    """Run the full law §29 sequence for a single submitted packet."""

    config = config or PipelineConfig()
    packet_id = str(raw.get("packet_id", "")).strip() or "<unknown>"

    validation = validate_packet(raw)
    if validation.rejected:
        # Generated-data processing rejected; primary artifact decision is
        # independent and is not touched here (law §29).
        return PipelineResult(packet_id=packet_id, accepted=False, validation=validation)

    packet = SubagentDataPacket.from_dict(raw)

    archived_path: str | None = None
    if archive is not None:
        archived_path = str(archive.persist(raw).path)

    units = harvest(packet)
    for unit in units:
        classify(unit)  # deterministic classification pass (law §14)

    dedup: DedupResult = deduplicate(units)
    survivors = list(dedup.survivors)

    conflicts: ConflictResult = find_conflicts(survivors)
    blocking_ids = frozenset(conflicts.blocking_unit_ids())

    decisions = route_units(
        survivors,
        authority_granted=config.authority_granted,
        recurring_unit_ids=config.recurring_unit_ids,
        blocking_unit_ids=blocking_ids,
    )
    violations = gate_violations(decisions)

    return PipelineResult(
        packet_id=packet.packet_id,
        accepted=True,
        validation=validation,
        routing_decisions=tuple(decisions),
        conflicts=tuple(c.conflict_id for c in conflicts.conflicts),
        dedup_links=tuple((link.survivor_id, link.duplicate_id) for link in dedup.links),
        gate_violations=tuple(violations),
        archived_path=archived_path,
    )

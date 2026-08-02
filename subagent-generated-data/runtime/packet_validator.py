"""Packet validation gate (law §12) enforcing the SGD invariants (law §31).

A packet that fails validation must not enter downstream routing (law §29). The
validator works on the raw mapping so it can also reject forbidden fields (e.g.
self-promotion, SGD-003) that never appear on the typed model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import (
    EVIDENCE_REQUIRED_STATUSES,
    REUSE_ROUTES,
    EpistemicStatus,
    RouteName,
    SubagentDataPacket,
)

# Fields a producing agent must never populate itself: promotion is the job of
# an independent gate, not the author (SGD-003, law §3.3).
FORBIDDEN_SELF_PROMOTION_FIELDS = ("promotion_decisions", "routing_decisions", "promoted")


@dataclass(frozen=True, slots=True)
class ValidationResult:
    ok: bool
    errors: tuple[str, ...] = ()
    invariants_violated: tuple[str, ...] = ()

    @property
    def rejected(self) -> bool:
        return not self.ok


@dataclass
class _Accumulator:
    errors: list[str] = field(default_factory=list)
    invariants: list[str] = field(default_factory=list)

    def fail(self, invariant: str, message: str) -> None:
        self.errors.append(message)
        if invariant not in self.invariants:
            self.invariants.append(invariant)


def validate_packet(raw: dict[str, Any]) -> ValidationResult:
    """Validate a raw packet mapping. Returns a typed pass/fail result."""

    acc = _Accumulator()

    for forbidden in FORBIDDEN_SELF_PROMOTION_FIELDS:
        if forbidden in raw:
            acc.fail("SGD-003", f"forbidden self-promotion field present: {forbidden!r}")

    try:
        packet = SubagentDataPacket.from_dict(raw)
    except (ValueError, KeyError, TypeError) as exc:
        # Attribute the parse failure to a specific invariant where the raw shape
        # lets us (e.g. an unknown missing its owner is SGD-008, not a generic
        # schema error). Only fall back to SGD-002 when nothing specific fired.
        _validate_unknowns(raw, acc)
        if not acc.errors:
            acc.fail("SGD-002", f"packet does not parse against canonical schema: {exc}")
        return ValidationResult(False, tuple(acc.errors), tuple(acc.invariants))

    _validate_generated_data_assessment(packet, raw, acc)
    _validate_reuse_assessment(packet, acc)
    _validate_units(packet, acc)
    _validate_unknowns(raw, acc)

    return ValidationResult(not acc.errors, tuple(acc.errors), tuple(acc.invariants))


def _validate_generated_data_assessment(
    packet: SubagentDataPacket, raw: dict[str, Any], acc: _Accumulator
) -> None:
    # SGD-001: completion requires either generated units or an explicit
    # "nothing reusable" declaration. Silence is not allowed (law §6).
    if packet.generated_data_units:
        return
    assessment = packet.generated_data_assessment
    if assessment is None:
        acc.fail(
            "SGD-001",
            "no generated_data_units and no generated_data_assessment: "
            "silence is not a valid completion",
        )
        return
    if not assessment.reusable_data_found and not (assessment.reason or "").strip():
        acc.fail(
            "SGD-009",
            "generated_data_assessment.reusable_data_found is false without a reason",
        )


def _validate_reuse_assessment(packet: SubagentDataPacket, acc: _Accumulator) -> None:
    confidence = packet.reuse_assessment.confidence
    if not 0.0 <= confidence <= 1.0:
        acc.fail("SGD-001", f"reuse_assessment.confidence out of range: {confidence}")


def _validate_units(packet: SubagentDataPacket, acc: _Accumulator) -> None:
    seen: set[str] = set()
    for unit in packet.generated_data_units:
        if unit.unit_id in seen:
            acc.fail("SGD-002", f"duplicate unit_id in packet: {unit.unit_id}")
        seen.add(unit.unit_id)

        # SGD-005: explicit scope.
        if not unit.scope:
            acc.fail("SGD-005", f"{unit.unit_id}: reusable unit has no scope")

        # SGD-004: observed/derived facts need inspectable provenance.
        if unit.epistemic_status in EVIDENCE_REQUIRED_STATUSES and not unit.source_evidence:
            acc.fail(
                "SGD-004",
                f"{unit.unit_id}: {unit.epistemic_status} unit has no source_evidence",
            )

        # SGD-006 is structural — from_dict already rejects a missing/invalid
        # epistemic_status; nothing further to check here.

        # SGD-007: any unit routed into future execution must declare when it
        # goes stale. evidence/reject routes do not influence execution.
        reuse_routed = any(route in REUSE_ROUTES for route in unit.proposed_routes)
        if reuse_routed and not unit.invalidation_conditions:
            acc.fail(
                "SGD-007",
                f"{unit.unit_id}: proposes a reuse route with no invalidation_conditions",
            )

        # A contested unit may not be smuggled in as a plain fact for reuse.
        if unit.epistemic_status is EpistemicStatus.CONTESTED and RouteName.MEMORY in (
            unit.proposed_routes
        ):
            acc.fail(
                "SGD-016",
                f"{unit.unit_id}: contested unit proposed directly to memory",
            )


def _validate_unknowns(raw: dict[str, Any], acc: _Accumulator) -> None:
    # SGD-008: every unknown carries a classification and an owner. from_dict
    # enforces this for well-formed entries; guard the raw shape too so a
    # malformed unknown cannot slip through as an empty object.
    for entry in raw.get("unresolved_unknowns") or []:
        if not isinstance(entry, dict):
            acc.fail("SGD-008", "unresolved_unknown entry is not an object")
            continue
        if not str(entry.get("class", "")).strip():
            acc.fail("SGD-008", "unresolved_unknown missing class")
        if not str(entry.get("owner", "")).strip():
            acc.fail("SGD-008", "unresolved_unknown missing owner")

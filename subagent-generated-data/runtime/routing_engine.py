"""Routing and promotion (law §15-§18).

Each unit gets one or more routes and exactly one promotion decision. A unit with
no route is invalid unless the decision is ``reject`` (SGD-017). High-risk units
never auto-promote without designated authority (SGD-014); blocking conflicts
force a defer (SGD-018).
"""

from __future__ import annotations

from dataclasses import dataclass

from .classifier import Classification, classify
from .models import (
    REUSE_ROUTES,
    GeneratedDataUnit,
    PromotionDecision,
    RiskClass,
    RouteName,
)


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    unit_id: str
    routes: tuple[RouteName, ...]
    promotion_decision: PromotionDecision
    risk_class: RiskClass
    authority_required: str | None
    authority_satisfied: bool
    rejection_reason: str | None = None
    blocking_conflict_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "unit_id": self.unit_id,
            "routes": [r.value for r in self.routes],
            "promotion_decision": self.promotion_decision.value,
            "risk_class": self.risk_class.value,
            "authority_required": self.authority_required,
            "authority_satisfied": self.authority_satisfied,
            "rejection_reason": self.rejection_reason,
            "blocking_conflict_ids": list(self.blocking_conflict_ids),
        }


def _select_routes(
    unit: GeneratedDataUnit, classification: Classification
) -> tuple[RouteName, ...]:
    # Honour the agent's proposed routes when they are consistent with the
    # class-derived candidates; otherwise fall back to the deterministic map.
    if unit.proposed_routes:
        allowed = set(classification.candidate_routes) | {RouteName.EVIDENCE, RouteName.REJECT}
        chosen = tuple(r for r in unit.proposed_routes if r in allowed)
        if chosen:
            return chosen
    return classification.candidate_routes


def decide(
    unit: GeneratedDataUnit,
    *,
    authority_granted: bool = False,
    recurrence: bool = False,
    blocking_conflict_ids: tuple[str, ...] = (),
) -> RoutingDecision:
    """Produce the routing + promotion decision for a single unit."""

    classification = classify(unit)
    routes = _select_routes(unit, classification)

    if not routes:
        return RoutingDecision(
            unit_id=unit.unit_id,
            routes=(RouteName.REJECT,),
            promotion_decision=PromotionDecision.REJECT,
            risk_class=classification.risk_class,
            authority_required=classification.authority_required,
            authority_satisfied=False,
            rejection_reason="no valid destination route",
        )

    if routes == (RouteName.REJECT,):
        return RoutingDecision(
            unit_id=unit.unit_id,
            routes=routes,
            promotion_decision=PromotionDecision.REJECT,
            risk_class=classification.risk_class,
            authority_required=classification.authority_required,
            authority_satisfied=False,
            rejection_reason="unit routed to reject",
        )

    reuse_routed = any(r in REUSE_ROUTES for r in routes)
    decision = _promotion_decision(
        classification.risk_class,
        reuse_routed=reuse_routed,
        authority_granted=authority_granted,
        recurrence=recurrence,
        blocking=bool(blocking_conflict_ids),
    )
    authority_satisfied = decision is PromotionDecision.PROMOTE and (
        classification.risk_class is not RiskClass.HIGH or authority_granted
    )
    return RoutingDecision(
        unit_id=unit.unit_id,
        routes=routes,
        promotion_decision=decision,
        risk_class=classification.risk_class,
        authority_required=classification.authority_required,
        authority_satisfied=authority_satisfied,
        blocking_conflict_ids=blocking_conflict_ids,
    )


def _promotion_decision(
    risk: RiskClass,
    *,
    reuse_routed: bool,
    authority_granted: bool,
    recurrence: bool,
    blocking: bool,
) -> PromotionDecision:
    if blocking:
        return PromotionDecision.DEFER  # SGD-018: blocking conflict stops promotion
    if not reuse_routed:
        return PromotionDecision.RETAIN  # evidence-only lives in the archive
    if risk is RiskClass.HIGH:
        # SGD-014: high-risk requires designated authority; otherwise defer.
        return PromotionDecision.PROMOTE if authority_granted else PromotionDecision.DEFER
    if risk is RiskClass.MEDIUM:
        # Independent validation or recurrence required (law §18).
        return (
            PromotionDecision.PROMOTE
            if (authority_granted or recurrence)
            else PromotionDecision.DEFER
        )
    return PromotionDecision.PROMOTE  # low risk, runtime validation suffices


def route_units(
    units: list[GeneratedDataUnit],
    *,
    authority_granted: bool = False,
    recurring_unit_ids: frozenset[str] = frozenset(),
    blocking_unit_ids: frozenset[str] = frozenset(),
) -> list[RoutingDecision]:
    decisions: list[RoutingDecision] = []
    for unit in units:
        conflict_ids = ("blocking-conflict",) if unit.unit_id in blocking_unit_ids else ()
        decisions.append(
            decide(
                unit,
                authority_granted=authority_granted,
                recurrence=unit.unit_id in recurring_unit_ids,
                blocking_conflict_ids=conflict_ids,
            )
        )
    return decisions

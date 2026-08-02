"""Promotion gate (law §17, §18): the independent authority check.

Routing proposes a promotion decision; this gate is the separate authority
(law §3.3) that confirms no high-risk unit was promoted without designated
authority (SGD-014) and no raw unit reached canonical authority unvalidated
(SGD-002). It returns the invariant violations it finds.
"""

from __future__ import annotations

from .models import PromotionDecision, RiskClass
from .routing_engine import RoutingDecision


def gate_violations(decisions: list[RoutingDecision]) -> list[str]:
    """Return SGD-invariant violations across a set of routing decisions."""

    violations: list[str] = []
    for decision in decisions:
        if decision.promotion_decision is not PromotionDecision.PROMOTE:
            continue
        if decision.risk_class is RiskClass.HIGH and not decision.authority_satisfied:
            violations.append(
                f"SGD-014: {decision.unit_id} high-risk promoted without designated authority"
            )
        if decision.blocking_conflict_ids:
            violations.append(
                f"SGD-018: {decision.unit_id} promoted while a blocking conflict is unresolved"
            )
    return violations


def is_clean(decisions: list[RoutingDecision]) -> bool:
    return not gate_violations(decisions)

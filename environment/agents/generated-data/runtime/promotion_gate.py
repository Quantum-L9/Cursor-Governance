from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


class PromotionFailure(ValueError):
    """Raised when a promotion result cannot be determined safely."""


@dataclass(frozen=True)
class PromotionResult:
    promotion_id: str
    unit_id: str
    route: str
    decision: str
    risk_class: str
    authority_required: str
    reasons: tuple[str, ...]
    conditions: tuple[str, ...]
    promotion_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "promotion_id": self.promotion_id,
            "unit_id": self.unit_id,
            "route": self.route,
            "decision": self.decision,
            "risk_class": self.risk_class,
            "authority_required": self.authority_required,
            "reasons": list(self.reasons),
            "conditions": list(self.conditions),
            "promotion_hash": self.promotion_hash,
        }


class PromotionGate:
    """Apply L9 promotion-risk rules to routing decisions."""

    HIGH_RISK_ROUTES = {
        "architecture",
    }
    MEDIUM_RISK_ROUTES = {
        "contracts",
        "validation",
        "patterns",
        "memory",
    }
    LOW_RISK_ROUTES = {
        "opportunities",
        "evidence",
    }

    def evaluate(
        self,
        *,
        harvested_unit: Mapping[str, Any],
        routing_decision: Mapping[str, Any],
        independent_validation_present: bool = False,
        designated_authority_approval: bool = False,
        recurrence_count: int = 1,
    ) -> PromotionResult:
        unit_id = self._required_string(
            harvested_unit,
            "unit_id",
        )
        route = self._required_string(
            routing_decision,
            "route",
        )
        route_status = self._required_string(
            routing_decision,
            "status",
        )
        classification = harvested_unit.get(
            "classification",
        )
        original = harvested_unit.get("original_unit")
        if not isinstance(classification, Mapping):
            raise PromotionFailure("classification must be an object")
        if not isinstance(original, Mapping):
            raise PromotionFailure("original_unit must be an object")
        confidence = self._confidence(original)
        epistemic_status = str(
            classification.get(
                "epistemic_status",
                "",
            )
        )
        reuse_risk = str(
            classification.get(
                "risk_of_incorrect_reuse",
                "critical",
            )
        )
        authority_sensitivity = str(
            classification.get(
                "authority_sensitivity",
                "high",
            )
        )
        risk_class = self._risk_class(
            route=route,
            authority_sensitivity=authority_sensitivity,
            reuse_risk=reuse_risk,
        )
        early = self._early_routing_decision(
            unit_id=unit_id,
            route=route,
            route_status=route_status,
            risk_class=risk_class,
            routing_decision=routing_decision,
        )
        if early is not None:
            return early
        reasons: list[str] = []
        conditions: list[str] = []
        self._apply_epistemic_checks(
            epistemic_status=epistemic_status,
            confidence=confidence,
            reasons=reasons,
            conditions=conditions,
        )
        deferred = self._defer_for_high_or_medium_risk(
            unit_id=unit_id,
            route=route,
            risk_class=risk_class,
            reasons=reasons,
            conditions=conditions,
            independent_validation_present=independent_validation_present,
            designated_authority_approval=designated_authority_approval,
            recurrence_count=recurrence_count,
            route_requires_independent_validation=self._requires_independent_validation(
                routing_decision
            ),
        )
        if deferred is not None:
            return deferred
        if confidence < 0.75 and route != "evidence":
            return self._result(
                unit_id=unit_id,
                route=route,
                decision="retain",
                risk_class=risk_class,
                authority_required="runtime",
                reasons=("confidence_supports_evidence_only",),
                conditions=("reassess_after_additional_evidence",),
            )
        return self._result(
            unit_id=unit_id,
            route=route,
            decision="promote",
            risk_class=risk_class,
            authority_required=str(
                routing_decision.get(
                    "required_authority",
                    "runtime",
                )
            ),
            reasons=(
                "routing_eligible",
                "promotion_controls_satisfied",
            ),
            conditions=(),
        )

    def _early_routing_decision(
        self,
        *,
        unit_id: str,
        route: str,
        route_status: str,
        risk_class: str,
        routing_decision: Mapping[str, Any],
    ) -> PromotionResult | None:
        if route_status == "rejected":
            return self._result(
                unit_id=unit_id,
                route=route,
                decision="reject",
                risk_class=risk_class,
                authority_required="none",
                reasons=("routing_rejected",),
                conditions=(),
            )
        if route_status == "deferred":
            return self._result(
                unit_id=unit_id,
                route=route,
                decision="defer",
                risk_class=risk_class,
                authority_required=str(
                    routing_decision.get(
                        "required_authority",
                        "runtime",
                    )
                ),
                reasons=("routing_deferred",),
                conditions=tuple(
                    routing_decision.get(
                        "reason_codes",
                        [],
                    )
                ),
            )
        return None

    @staticmethod
    def _apply_epistemic_checks(
        *,
        epistemic_status: str,
        confidence: float,
        reasons: list[str],
        conditions: list[str],
    ) -> None:
        if epistemic_status in {
            "hypothesized",
            "contested",
            "unresolved",
        }:
            reasons.append("epistemic_status_not_promotable")
            conditions.append("resolve_or_reclassify_epistemic_status")
        if confidence < 0.5:
            reasons.append("confidence_below_minimum")
            conditions.append("collect_stronger_evidence")

    def _defer_for_high_or_medium_risk(
        self,
        *,
        unit_id: str,
        route: str,
        risk_class: str,
        reasons: list[str],
        conditions: list[str],
        independent_validation_present: bool,
        designated_authority_approval: bool,
        recurrence_count: int,
        route_requires_independent_validation: bool = False,
    ) -> PromotionResult | None:
        if risk_class == "high":
            if not independent_validation_present:
                conditions.append("independent_validation_required")
            if not designated_authority_approval:
                conditions.append("designated_authority_approval_required")
            if conditions:
                reasons.append("high_risk_promotion_controls_missing")
                return self._result(
                    unit_id=unit_id,
                    route=route,
                    decision="defer",
                    risk_class=risk_class,
                    authority_required="designated_authority",
                    reasons=tuple(sorted(set(reasons))),
                    conditions=tuple(sorted(set(conditions))),
                )
        if risk_class == "medium" or route_requires_independent_validation:
            if not independent_validation_present and recurrence_count < 2:
                return self._result(
                    unit_id=unit_id,
                    route=route,
                    decision="defer",
                    risk_class=risk_class,
                    authority_required=("independent_validator_or_recurrence"),
                    reasons=("medium_risk_requires_validation_or_recurrence",),
                    conditions=(
                        "provide_independent_validation",
                        "or_observe_second_confirming_occurrence",
                    ),
                )
        return None

    def evaluate_many(
        self,
        *,
        harvested_units: list[Mapping[str, Any]],
        routing_decisions: list[Mapping[str, Any]],
        independent_validation_present: bool = False,
        designated_authority_approval: bool = False,
        recurrence_counts: Mapping[str, int] | None = None,
    ) -> list[PromotionResult]:
        by_unit = {str(unit["unit_id"]): unit for unit in harvested_units}
        recurrence_counts = recurrence_counts or {}
        results: list[PromotionResult] = []
        for decision in routing_decisions:
            unit_id = str(decision["unit_id"])
            unit = by_unit.get(unit_id)
            if unit is None:
                raise PromotionFailure(f"Routing decision references unknown unit {unit_id!r}")
            results.append(
                self.evaluate(
                    harvested_unit=unit,
                    routing_decision=decision,
                    independent_validation_present=(independent_validation_present),
                    designated_authority_approval=(designated_authority_approval),
                    recurrence_count=int(
                        recurrence_counts.get(
                            unit_id,
                            1,
                        )
                    ),
                )
            )
        return results

    def _risk_class(
        self,
        *,
        route: str,
        authority_sensitivity: str,
        reuse_risk: str,
    ) -> str:
        if (
            route in self.HIGH_RISK_ROUTES
            or authority_sensitivity == "high"
            or reuse_risk in {"high", "critical"}
        ):
            return "high"
        if (
            route in self.MEDIUM_RISK_ROUTES
            or authority_sensitivity == "medium"
            or reuse_risk == "medium"
        ):
            return "medium"
        return "low"

    @staticmethod
    def _requires_independent_validation(routing_decision: Mapping[str, Any]) -> bool:
        raw = routing_decision.get("requires_independent_validation")
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str):
            return raw.strip().lower() in {"1", "true", "yes"}
        return False

    @staticmethod
    def _confidence(
        original: Mapping[str, Any],
    ) -> float:
        try:
            value = float(original.get("confidence", 0))
        except (TypeError, ValueError):
            value = 0.0
        return max(0.0, min(1.0, value))

    @staticmethod
    def _result(
        *,
        unit_id: str,
        route: str,
        decision: str,
        risk_class: str,
        authority_required: str,
        reasons: tuple[str, ...],
        conditions: tuple[str, ...],
    ) -> PromotionResult:
        payload = {
            "unit_id": unit_id,
            "route": route,
            "decision": decision,
            "risk_class": risk_class,
            "authority_required": authority_required,
            "reasons": list(reasons),
            "conditions": list(conditions),
        }
        digest = hashlib.sha256(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        return PromotionResult(
            promotion_id=f"promotion-{digest[:20]}",
            unit_id=unit_id,
            route=route,
            decision=decision,
            risk_class=risk_class,
            authority_required=authority_required,
            reasons=reasons,
            conditions=conditions,
            promotion_hash=digest,
        )

    @staticmethod
    def _required_string(
        value: Mapping[str, Any],
        field_name: str,
    ) -> str:
        raw = value.get(field_name)
        if not isinstance(raw, str) or not raw.strip():
            raise PromotionFailure(f"{field_name!r} must be a non-empty string")
        return raw.strip()


def main(argv: list[str] | None = None) -> int:
    raise SystemExit("promotion_gate file-path CLI is disabled; use PromotionGate APIs")


if __name__ == "__main__":
    raise SystemExit(main())

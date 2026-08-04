from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any


class LearningClosureFailure(ValueError):
    """Raised when a closure report cannot be computed."""


@dataclass(frozen=True)
class ClosureCheck:
    check_id: str
    passed: bool
    blocking: bool
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "passed": self.passed,
            "blocking": self.blocking,
            "message": self.message,
        }


@dataclass(frozen=True)
class LearningClosureResult:
    closure_id: str
    campaign_id: str
    status: str
    checks: tuple[ClosureCheck, ...]
    unresolved_high_value_units: tuple[str, ...]
    unresolved_unknown_ids: tuple[str, ...]
    closure_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "closure_id": self.closure_id,
            "campaign_id": self.campaign_id,
            "status": self.status,
            "checks": [check.to_dict() for check in self.checks],
            "unresolved_high_value_units": list(self.unresolved_high_value_units),
            "unresolved_unknown_ids": list(self.unresolved_unknown_ids),
            "closure_hash": self.closure_hash,
        }


class LearningClosureEvaluator:
    """Determine whether a campaign may seal its learning lifecycle."""

    def evaluate(
        self,
        *,
        campaign_id: str,
        expected_action_ids: Iterable[str],
        packets: Iterable[Mapping[str, Any]],
        validation_reports: Iterable[Mapping[str, Any]],
        harvest_results: Iterable[Mapping[str, Any]],
        routing_decisions: Iterable[Mapping[str, Any]],
        promotion_results: Iterable[Mapping[str, Any]],
        evidence_archive_complete: bool,
    ) -> LearningClosureResult:
        expected_actions = set(expected_action_ids)
        packet_list = list(packets)
        validation_list = list(validation_reports)
        harvest_list = list(harvest_results)
        route_list = list(routing_decisions)
        promotion_list = list(promotion_results)
        missing_actions = self._missing_actions(expected_actions, packet_list)
        invalid_or_unvalidated = self._invalid_or_unvalidated_packets(packet_list, validation_list)
        harvested_unit_ids, rejected_units_have_reasons = self._harvest_state(harvest_list)
        routed_unit_ids = {
            str(decision.get("unit_id")) for decision in route_list if decision.get("unit_id")
        }
        unrouted_units = sorted(harvested_unit_ids - routed_unit_ids)
        promoted_unit_ids = {
            str(result.get("unit_id")) for result in promotion_list if result.get("unit_id")
        }
        units_without_promotion_decision = sorted(routed_unit_ids - promoted_unit_ids)
        high_value_unresolved = self._high_value_unresolved(promotion_list)
        unresolved_unknown_ids = self._unresolved_unknown_ids(packet_list)
        checks = self._build_checks(
            missing_actions=missing_actions,
            invalid_or_unvalidated=invalid_or_unvalidated,
            unrouted_units=unrouted_units,
            units_without_promotion_decision=units_without_promotion_decision,
            unresolved_unknown_ids=unresolved_unknown_ids,
            rejected_units_have_reasons=rejected_units_have_reasons,
            evidence_archive_complete=evidence_archive_complete,
            high_value_unresolved=high_value_unresolved,
        )
        status = (
            "closed" if all(check.passed or not check.blocking for check in checks) else "blocked"
        )
        payload = {
            "campaign_id": campaign_id,
            "status": status,
            "checks": [check.to_dict() for check in checks],
            "unresolved_high_value_units": sorted(high_value_unresolved),
            "unresolved_unknown_ids": sorted(unresolved_unknown_ids),
        }
        digest = hashlib.sha256(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        return LearningClosureResult(
            closure_id=f"closure-{digest[:20]}",
            campaign_id=campaign_id,
            status=status,
            checks=checks,
            unresolved_high_value_units=tuple(sorted(high_value_unresolved)),
            unresolved_unknown_ids=tuple(sorted(unresolved_unknown_ids)),
            closure_hash=digest,
        )

    @staticmethod
    def _missing_actions(
        expected_actions: set[str],
        packet_list: list[Mapping[str, Any]],
    ) -> list[str]:
        packet_actions = {
            str(packet.get("identity", {}).get("action_id"))
            for packet in packet_list
            if isinstance(packet.get("identity"), Mapping)
        }
        return sorted(expected_actions - packet_actions)

    @staticmethod
    def _invalid_or_unvalidated_packets(
        packet_list: list[Mapping[str, Any]],
        validation_list: list[Mapping[str, Any]],
    ) -> list[str]:
        packet_ids = {
            str(packet.get("packet_id")) for packet in packet_list if packet.get("packet_id")
        }
        valid_packet_ids = {
            str(report.get("packet_id"))
            for report in validation_list
            if report.get("valid") is True
        }
        return sorted(packet_ids - valid_packet_ids)

    @staticmethod
    def _harvest_state(
        harvest_list: list[Mapping[str, Any]],
    ) -> tuple[set[str], bool]:
        harvested_unit_ids: set[str] = set()
        rejected_units_have_reasons = True
        for result in harvest_list:
            for unit in result.get("harvested_units", []):
                if isinstance(unit, Mapping) and unit.get("unit_id"):
                    harvested_unit_ids.add(str(unit["unit_id"]))
            for rejected in result.get("rejected_units", []):
                if not isinstance(rejected, Mapping) or not rejected.get("reason"):
                    rejected_units_have_reasons = False
        return harvested_unit_ids, rejected_units_have_reasons

    @staticmethod
    def _high_value_unresolved(
        promotion_list: list[Mapping[str, Any]],
    ) -> set[str]:
        high_value_unresolved: set[str] = set()
        for result in promotion_list:
            if not isinstance(result, Mapping):
                continue
            if result.get("risk_class") in {"medium", "high"} and result.get("decision") == "defer":
                high_value_unresolved.add(str(result.get("unit_id")))
        return high_value_unresolved

    @staticmethod
    def _unresolved_unknown_ids(
        packet_list: list[Mapping[str, Any]],
    ) -> set[str]:
        unresolved_unknown_ids: set[str] = set()
        for packet in packet_list:
            unknowns = packet.get("unresolved_unknowns", [])
            if not isinstance(unknowns, list):
                continue
            for unknown in unknowns:
                if not isinstance(unknown, Mapping):
                    continue
                if not unknown.get("owner") or not unknown.get("next_action"):
                    unresolved_unknown_ids.add(
                        str(
                            unknown.get(
                                "unknown_id",
                                "unknown",
                            )
                        )
                    )
        return unresolved_unknown_ids

    @staticmethod
    def _build_checks(
        *,
        missing_actions: list[str],
        invalid_or_unvalidated: list[str],
        unrouted_units: list[str],
        units_without_promotion_decision: list[str],
        unresolved_unknown_ids: set[str],
        rejected_units_have_reasons: bool,
        evidence_archive_complete: bool,
        high_value_unresolved: set[str],
    ) -> tuple[ClosureCheck, ...]:
        return (
            ClosureCheck(
                check_id="SGD-CLOSE-001",
                passed=not missing_actions,
                blocking=True,
                message=(
                    "All required subagent packets received"
                    if not missing_actions
                    else ("Missing packets for actions: " + ", ".join(missing_actions))
                ),
            ),
            ClosureCheck(
                check_id="SGD-CLOSE-002",
                passed=not invalid_or_unvalidated,
                blocking=True,
                message=(
                    "All packets validated"
                    if not invalid_or_unvalidated
                    else ("Invalid or unvalidated packets: " + ", ".join(invalid_or_unvalidated))
                ),
            ),
            ClosureCheck(
                check_id="SGD-CLOSE-003",
                passed=not unrouted_units,
                blocking=True,
                message=(
                    "All harvested units routed"
                    if not unrouted_units
                    else ("Unrouted units: " + ", ".join(unrouted_units))
                ),
            ),
            ClosureCheck(
                check_id="SGD-CLOSE-004",
                passed=not units_without_promotion_decision,
                blocking=True,
                message=(
                    "All routed units have promotion decisions"
                    if not units_without_promotion_decision
                    else (
                        "Units missing promotion decisions: "
                        + ", ".join(units_without_promotion_decision)
                    )
                ),
            ),
            ClosureCheck(
                check_id="SGD-CLOSE-005",
                passed=not unresolved_unknown_ids,
                blocking=True,
                message=(
                    "All unresolved unknowns have owners and next actions"
                    if not unresolved_unknown_ids
                    else (
                        "Unowned unresolved unknowns: " + ", ".join(sorted(unresolved_unknown_ids))
                    )
                ),
            ),
            ClosureCheck(
                check_id="SGD-CLOSE-006",
                passed=rejected_units_have_reasons,
                blocking=True,
                message=(
                    "All rejected units have reasons"
                    if rejected_units_have_reasons
                    else "One or more rejected units lack a reason"
                ),
            ),
            ClosureCheck(
                check_id="SGD-CLOSE-007",
                passed=evidence_archive_complete,
                blocking=True,
                message=(
                    "Evidence archive is complete"
                    if evidence_archive_complete
                    else "Evidence archive is incomplete"
                ),
            ),
            ClosureCheck(
                check_id="SGD-CLOSE-008",
                passed=not high_value_unresolved,
                blocking=True,
                message=(
                    "No high-value promotion decision remains unresolved"
                    if not high_value_unresolved
                    else (
                        "Deferred high-value units require resolution: "
                        + ", ".join(sorted(high_value_unresolved))
                    )
                ),
            ),
        )


def main(argv: list[str] | None = None) -> int:
    raise SystemExit(
        "learning_closure file-path CLI is disabled; use LearningClosureEvaluator APIs"
    )


if __name__ == "__main__":
    raise SystemExit(main())

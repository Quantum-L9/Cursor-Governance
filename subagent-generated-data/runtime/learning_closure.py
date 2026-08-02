from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
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
        packet_actions = {
            str(packet.get("identity", {}).get("action_id"))
            for packet in packet_list
            if isinstance(packet.get("identity"), Mapping)
        }
        missing_actions = sorted(expected_actions - packet_actions)
        packet_ids = {
            str(packet.get("packet_id")) for packet in packet_list if packet.get("packet_id")
        }
        valid_packet_ids = {
            str(report.get("packet_id"))
            for report in validation_list
            if report.get("valid") is True
        }
        invalid_or_unvalidated = sorted(packet_ids - valid_packet_ids)
        harvested_unit_ids: set[str] = set()
        rejected_units_have_reasons = True
        for result in harvest_list:
            for unit in result.get(
                "harvested_units",
                [],
            ):
                if isinstance(unit, Mapping) and unit.get("unit_id"):
                    harvested_unit_ids.add(str(unit["unit_id"]))
            for rejected in result.get(
                "rejected_units",
                [],
            ):
                if not isinstance(rejected, Mapping):
                    rejected_units_have_reasons = False
                elif not rejected.get("reason"):
                    rejected_units_have_reasons = False
        routed_unit_ids = {
            str(decision.get("unit_id")) for decision in route_list if decision.get("unit_id")
        }
        unrouted_units = sorted(harvested_unit_ids - routed_unit_ids)
        promoted_unit_ids = {
            str(result.get("unit_id")) for result in promotion_list if result.get("unit_id")
        }
        units_without_promotion_decision = sorted(routed_unit_ids - promoted_unit_ids)
        high_value_unresolved: set[str] = set()
        for result in promotion_list:
            if not isinstance(result, Mapping):
                continue
            if result.get("risk_class") in {"medium", "high"} and result.get("decision") == "defer":
                high_value_unresolved.add(str(result.get("unit_id")))
        unresolved_unknown_ids: set[str] = set()
        for packet in packet_list:
            unknowns = packet.get(
                "unresolved_unknowns",
                [],
            )
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
        checks = (
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


def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate campaign learning closure.")
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--expected-actions", required=True)
    parser.add_argument("--packets", required=True)
    parser.add_argument("--validation-reports", required=True)
    parser.add_argument("--harvest-results", required=True)
    parser.add_argument("--routing-decisions", required=True)
    parser.add_argument("--promotion-results", required=True)
    parser.add_argument(
        "--evidence-archive-complete",
        action="store_true",
    )
    args = parser.parse_args()
    result = LearningClosureEvaluator().evaluate(
        campaign_id=args.campaign_id,
        expected_action_ids=load_json(args.expected_actions),
        packets=load_json(args.packets),
        validation_reports=load_json(args.validation_reports),
        harvest_results=load_json(args.harvest_results),
        routing_decisions=load_json(args.routing_decisions),
        promotion_results=load_json(args.promotion_results),
        evidence_archive_complete=(args.evidence_archive_complete),
    )
    print(
        json.dumps(
            result.to_dict(),
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result.status == "closed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

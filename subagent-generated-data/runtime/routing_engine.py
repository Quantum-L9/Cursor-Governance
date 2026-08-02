from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:
    raise RuntimeError("routing_engine.py requires the 'PyYAML' package") from exc
RUNTIME_DIR = Path(__file__).resolve().parent
BASE_DIR = RUNTIME_DIR.parent
ROUTES_DIR = BASE_DIR / "routes"


class RoutingFailure(ValueError):
    """Raised when no safe routing decision can be produced."""


@dataclass(frozen=True)
class RoutingDecision:
    decision_id: str
    unit_id: str
    route: str
    destination: str
    status: str
    reason_codes: tuple[str, ...]
    required_authority: str
    requires_independent_validation: bool
    decision_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "unit_id": self.unit_id,
            "route": self.route,
            "destination": self.destination,
            "status": self.status,
            "reason_codes": list(self.reason_codes),
            "required_authority": self.required_authority,
            "requires_independent_validation": (self.requires_independent_validation),
            "decision_hash": self.decision_hash,
        }


class RoutingEngine:
    """Route harvested generated-data units using declarative route files."""

    def __init__(
        self,
        *,
        routes_dir: str | Path = ROUTES_DIR,
    ) -> None:
        self.routes_dir = Path(routes_dir)
        self.routes = self._load_routes(self.routes_dir)

    def route(
        self,
        harvested_unit: Mapping[str, Any],
    ) -> list[RoutingDecision]:
        original = harvested_unit.get("original_unit")
        classification = harvested_unit.get("classification")
        if not isinstance(original, Mapping):
            raise RoutingFailure("harvested_unit.original_unit must be an object")
        if not isinstance(classification, Mapping):
            raise RoutingFailure("harvested_unit.classification must be an object")
        unit_id = self._required_string(
            harvested_unit,
            "unit_id",
        )
        primary_class = self._required_string(
            classification,
            "primary_class",
        )
        epistemic_status = self._required_string(
            classification,
            "epistemic_status",
        )
        risk = self._required_string(
            classification,
            "risk_of_incorrect_reuse",
        )
        requested_routes = classification.get(
            "normalized_routes",
            [],
        )
        if not isinstance(requested_routes, list):
            requested_routes = list(requested_routes)
        decisions: list[RoutingDecision] = []
        for route_name in requested_routes:
            route_name = str(route_name)
            route = self.routes.get(route_name)
            if route is None:
                decisions.append(
                    self._decision(
                        unit_id=unit_id,
                        route=route_name,
                        destination="none",
                        status="rejected",
                        reason_codes=("route_not_registered",),
                        required_authority="none",
                        requires_independent_validation=False,
                    )
                )
                continue
            accepted_classes = set(
                route.get(
                    "accepted_primary_classes",
                    [],
                )
            )
            if primary_class not in accepted_classes:
                decisions.append(
                    self._decision(
                        unit_id=unit_id,
                        route=route_name,
                        destination=str(route["destination"]),
                        status="rejected",
                        reason_codes=("class_not_accepted_by_route",),
                        required_authority=str(
                            route.get(
                                "promotion_authority",
                                "runtime",
                            )
                        ),
                        requires_independent_validation=bool(
                            route.get(
                                "independent_validation_required",
                                False,
                            )
                        ),
                    )
                )
                continue
            forbidden_statuses = set(
                route.get(
                    "forbidden_epistemic_statuses",
                    [],
                )
            )
            if epistemic_status in forbidden_statuses:
                decisions.append(
                    self._decision(
                        unit_id=unit_id,
                        route=route_name,
                        destination=str(route["destination"]),
                        status="deferred",
                        reason_codes=("epistemic_status_not_promotable",),
                        required_authority=str(
                            route.get(
                                "promotion_authority",
                                "runtime",
                            )
                        ),
                        requires_independent_validation=True,
                    )
                )
                continue
            allowed_risks = set(
                route.get(
                    "allowed_risk_levels",
                    ["low", "medium"],
                )
            )
            if risk not in allowed_risks:
                decisions.append(
                    self._decision(
                        unit_id=unit_id,
                        route=route_name,
                        destination=str(route["destination"]),
                        status="deferred",
                        reason_codes=("risk_exceeds_route_threshold",),
                        required_authority=str(
                            route.get(
                                "promotion_authority",
                                "runtime",
                            )
                        ),
                        requires_independent_validation=True,
                    )
                )
                continue
            required_fields = route.get(
                "required_unit_fields",
                [],
            )
            missing = [field_name for field_name in required_fields if not original.get(field_name)]
            if missing:
                decisions.append(
                    self._decision(
                        unit_id=unit_id,
                        route=route_name,
                        destination=str(route["destination"]),
                        status="deferred",
                        reason_codes=tuple(f"missing_{field_name}" for field_name in missing),
                        required_authority=str(
                            route.get(
                                "promotion_authority",
                                "runtime",
                            )
                        ),
                        requires_independent_validation=bool(
                            route.get(
                                "independent_validation_required",
                                False,
                            )
                        ),
                    )
                )
                continue
            decisions.append(
                self._decision(
                    unit_id=unit_id,
                    route=route_name,
                    destination=str(route["destination"]),
                    status="eligible",
                    reason_codes=(
                        "class_accepted",
                        "epistemic_status_accepted",
                        "risk_accepted",
                        "required_fields_present",
                    ),
                    required_authority=str(
                        route.get(
                            "promotion_authority",
                            "runtime",
                        )
                    ),
                    requires_independent_validation=bool(
                        route.get(
                            "independent_validation_required",
                            False,
                        )
                    ),
                )
            )
        if not decisions:
            decisions.append(
                self._decision(
                    unit_id=unit_id,
                    route="reject",
                    destination="evidence_archive",
                    status="rejected",
                    reason_codes=("no_route_requested",),
                    required_authority="runtime",
                    requires_independent_validation=False,
                )
            )
        return decisions

    def route_many(
        self,
        harvested_units: Iterable[Mapping[str, Any]],
    ) -> list[RoutingDecision]:
        decisions: list[RoutingDecision] = []
        for unit in harvested_units:
            decisions.extend(self.route(unit))
        return decisions

    def validate_routes(self) -> list[str]:
        errors: list[str] = []
        required_fields = {
            "route_id",
            "schema_version",
            "destination",
            "accepted_primary_classes",
            "forbidden_epistemic_statuses",
            "allowed_risk_levels",
            "required_unit_fields",
            "promotion_authority",
            "independent_validation_required",
        }
        for route_name, route in self.routes.items():
            missing = sorted(required_fields - set(route))
            if missing:
                errors.append(f"{route_name}: missing fields " + ", ".join(missing))
            if route.get("route_id") != route_name:
                errors.append(f"{route_name}: route_id must equal filename stem")
        return errors

    @staticmethod
    def _decision(
        *,
        unit_id: str,
        route: str,
        destination: str,
        status: str,
        reason_codes: tuple[str, ...],
        required_authority: str,
        requires_independent_validation: bool,
    ) -> RoutingDecision:
        payload = {
            "unit_id": unit_id,
            "route": route,
            "destination": destination,
            "status": status,
            "reason_codes": list(reason_codes),
            "required_authority": required_authority,
            "requires_independent_validation": (requires_independent_validation),
        }
        decision_hash = hashlib.sha256(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        return RoutingDecision(
            decision_id=f"route-{decision_hash[:20]}",
            unit_id=unit_id,
            route=route,
            destination=destination,
            status=status,
            reason_codes=reason_codes,
            required_authority=required_authority,
            requires_independent_validation=(requires_independent_validation),
            decision_hash=decision_hash,
        )

    @staticmethod
    def _load_routes(
        routes_dir: Path,
    ) -> dict[str, Mapping[str, Any]]:
        routes: dict[str, Mapping[str, Any]] = {}
        for path in sorted(routes_dir.glob("*.yaml")):
            with path.open("r", encoding="utf-8") as handle:
                payload = yaml.safe_load(handle)
            if not isinstance(payload, Mapping):
                raise RoutingFailure(f"Route file must contain an object: {path}")
            routes[path.stem] = payload
        return routes

    @staticmethod
    def _required_string(
        value: Mapping[str, Any],
        field_name: str,
    ) -> str:
        raw = value.get(field_name)
        if not isinstance(raw, str) or not raw.strip():
            raise RoutingFailure(f"{field_name!r} must be a non-empty string")
        return raw.strip()


def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    parser = argparse.ArgumentParser(description="Route harvested generated-data units.")
    parser.add_argument("harvest_result", nargs="?")
    parser.add_argument(
        "--routes-dir",
        default=str(ROUTES_DIR),
    )
    parser.add_argument(
        "--validate-routes",
        action="store_true",
    )
    args = parser.parse_args()
    engine = RoutingEngine(
        routes_dir=args.routes_dir,
    )
    if args.validate_routes:
        errors = engine.validate_routes()
        print(
            json.dumps(
                {
                    "valid": not errors,
                    "errors": errors,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0 if not errors else 1
    if not args.harvest_result:
        parser.error("harvest_result is required unless --validate-routes is used")
    payload = load_json(args.harvest_result)
    units = payload.get("harvested_units", [])
    decisions = engine.route_many(units)
    print(
        json.dumps(
            [decision.to_dict() for decision in decisions],
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

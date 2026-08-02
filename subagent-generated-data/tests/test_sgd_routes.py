"""Route/classifier consistency + routing invariant tests (law §15, §16, SGD-017)."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml
from runtime.classifier import CLASS_TO_ROUTES
from runtime.models import RouteName

ROOT = Path(__file__).resolve().parent.parent
ROUTES_FILE = ROOT / "routes" / "canonical-routes.yaml"

# Routes that do not carry a class payload (no `accepts` matching required).
_NON_ACCEPTING = {RouteName.EVIDENCE.value, RouteName.REJECT.value}


class RouteRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = yaml.safe_load(ROUTES_FILE.read_text(encoding="utf-8"))
        self.routes = self.registry["routes"]

    def test_all_nine_canonical_routes_present(self) -> None:
        self.assertEqual(set(self.routes), {r.value for r in RouteName})

    def test_classifier_targets_are_declared_routes(self) -> None:
        for cls, routes in CLASS_TO_ROUTES.items():
            for route in routes:
                self.assertIn(route.value, self.routes, f"{cls} -> undeclared route {route}")

    def test_classifier_routes_accept_their_class(self) -> None:
        for cls, routes in CLASS_TO_ROUTES.items():
            for route in routes:
                if route.value in _NON_ACCEPTING:
                    continue
                accepts = self.routes[route.value].get("accepts") or []
                self.assertIn(
                    cls.value,
                    accepts,
                    f"route {route.value} does not accept class {cls.value}",
                )

    def test_reject_route_requires_reason(self) -> None:
        self.assertTrue(self.routes["reject"].get("requires_reason"))

    def test_evidence_route_not_injected_into_context(self) -> None:
        self.assertFalse(self.routes["evidence"].get("injects_into_future_context", True))

    def test_architecture_route_requires_authority(self) -> None:
        self.assertTrue(self.routes["architecture"].get("requires_designated_authority"))


if __name__ == "__main__":
    unittest.main()

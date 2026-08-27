from __future__ import annotations

import unittest
from pathlib import Path

from autonomy.adapters.conformance import AdapterConformance
from autonomy.adapters.protocol import AdapterConfig
from autonomy.policy_loader import load_example, load_policy

ROOT = Path(__file__).resolve().parents[2]


class PeerNeutralAutonomyTests(unittest.TestCase):
    def _report(self, payload: dict):
        return AdapterConformance(load_policy("adapter-requirements"), ROOT).run(
            AdapterConfig.from_dict(payload)
        )

    def test_current_examples_bind_canonical_peer_and_surface(self) -> None:
        for name, peer_ref, surface in (
            ("adapters/cursor.json", "cursor", "cursor-ide"),
            ("adapters/claude-code.json", "claude-code", "claude-cli"),
        ):
            config = AdapterConfig.from_dict(load_example(name))
            self.assertEqual((config.peer_ref, config.surface), (peer_ref, surface))
            self.assertEqual(self._report(load_example(name)).status.value, "PASS")

    def test_string_false_cannot_become_true(self) -> None:
        payload = load_example("adapters/cursor.json")
        payload["supports_heartbeat"] = "false"
        with self.assertRaises(ValueError):
            AdapterConfig.from_dict(payload)

    def test_missing_boolean_fails_closed(self) -> None:
        payload = load_example("adapters/cursor.json")
        payload.pop("supports_human_gate")
        with self.assertRaises(ValueError):
            AdapterConfig.from_dict(payload)

    def test_missing_provider_binary_is_not_root_autonomy_conformance(self) -> None:
        payload = load_example("adapters/claude-code.json")
        payload["executable"] = "definitely-not-installed-l9-provider"
        self.assertEqual(self._report(payload).status.value, "PASS")

    def test_optional_surface_capabilities_do_not_block_registration(self) -> None:
        payload = load_example("adapters/cursor.json")
        payload["supports_background_agents"] = False
        payload["supports_independent_review"] = False
        report = self._report(payload)
        self.assertEqual(report.status.value, "PASS")
        optional = [c for c in report.checks if c.check_id in {"ADAPTER-006", "ADAPTER-011"}]
        self.assertTrue(optional)
        self.assertTrue(all(not check.blocking for check in optional))

    def test_optional_capability_becomes_blocking_when_work_requires_it(self) -> None:
        payload = load_example("adapters/cursor.json")
        payload["supports_background_agents"] = False
        config = AdapterConfig.from_dict(payload)
        conformance = AdapterConformance(load_policy("adapter-requirements"), ROOT)
        with self.assertRaises(ValueError):
            conformance.assert_surface_capabilities(config, ["background_agent"])

    def test_policy_is_executable_law(self) -> None:
        payload = load_example("adapters/cursor.json")
        requirements = load_policy("adapter-requirements")
        requirements["mandatory"] = dict(requirements["mandatory"])
        requirements["mandatory"]["supports_heartbeat"] = False
        report = AdapterConformance(requirements, ROOT).run(AdapterConfig.from_dict(payload))
        heartbeat = next(c for c in report.checks if c.check_id == "ADAPTER-009")
        self.assertFalse(heartbeat.passed)
        self.assertEqual(report.status.value, "FAIL")

    def test_unregistered_peer_fails_closed(self) -> None:
        payload = load_example("adapters/cursor.json")
        payload["peer_ref"] = "unknown-peer"
        self.assertEqual(self._report(payload).status.value, "FAIL")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from autonomy.adapters.conformance import AdapterConformance
from autonomy.adapters.protocol import AdapterConfig
from autonomy.policy_loader import load_example, load_policy

ROOT = Path(__file__).resolve().parents[2]


def _schema(name: str) -> Draft202012Validator:
    path = ROOT / "autonomy/schemas" / name
    return Draft202012Validator(json.loads(path.read_text(encoding="utf-8")))


class PeerNeutralAutonomyTests(unittest.TestCase):
    def _report(self, payload: dict):
        return AdapterConformance(load_policy("adapter-requirements"), ROOT).run(
            AdapterConfig.from_dict(payload)
        )

    def _adapter_002(self, payload: dict):
        report = self._report(payload)
        return next(check for check in report.checks if check.check_id == "ADAPTER-002")

    def test_current_examples_bind_canonical_peer_and_surface(self) -> None:
        for name, peer_ref, surface in (
            ("adapters/cursor.json", "cursor", "cursor-ide"),
            ("adapters/claude-code.json", "claude-code", "claude-code-cli"),
        ):
            config = AdapterConfig.from_dict(load_example(name))
            self.assertEqual((config.peer_ref, config.surface), (peer_ref, surface))
            report = self._report(load_example(name))
            self.assertEqual(report.status.value, "PASS")
            binding = next(check for check in report.checks if check.check_id == "ADAPTER-002")
            self.assertTrue(binding.passed)

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

    def test_examples_and_reports_match_their_declared_schemas(self) -> None:
        config_schema = _schema("adapter-config.schema.json")
        report_schema = _schema("conformance-report.schema.json")
        for name in ("adapters/cursor.json", "adapters/claude-code.json"):
            with self.subTest(example=name):
                payload = load_example(name)
                self.assertEqual(sorted(config_schema.iter_errors(payload), key=str), [])
                report = self._report(payload).to_dict()
                self.assertEqual(sorted(report_schema.iter_errors(report), key=str), [])

    def test_unregistered_peer_fails_closed(self) -> None:
        payload = load_example("adapters/cursor.json")
        payload["peer_ref"] = "unknown-peer"
        report = self._report(payload)
        self.assertEqual(report.status.value, "FAIL")
        binding = next(check for check in report.checks if check.check_id == "ADAPTER-002")
        self.assertFalse(binding.passed)

    def test_nonexistent_provider_or_profile_fails_adapter_002(self) -> None:
        provider = load_example("adapters/cursor.json")
        provider["provider_ref"] = "missing-provider"
        self.assertFalse(self._adapter_002(provider).passed)
        profile = load_example("adapters/cursor.json")
        profile["execution_profile_ref"] = "missing-profile"
        self.assertFalse(self._adapter_002(profile).passed)

    def test_ambiguous_surface_without_coordinates_fails_adapter_002(self) -> None:
        payload = load_example("adapters/cursor.json")
        payload.pop("provider_ref")
        payload.pop("execution_profile_ref")
        self.assertFalse(self._adapter_002(payload).passed)

    def test_malformed_or_unavailable_registry_fails_closed(self) -> None:
        payload = load_example("adapters/cursor.json")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            conformance = AdapterConformance(load_policy("adapter-requirements"), root)
            unavailable = conformance.run(AdapterConfig.from_dict(payload))
            unavailable_check = next(
                check for check in unavailable.checks if check.check_id == "ADAPTER-002"
            )
            self.assertFalse(unavailable_check.passed)
            self.assertEqual(unavailable.status.value, "FAIL")
            registry = root / "environment" / "agents"
            schema_dir = registry / "schemas"
            schema_dir.mkdir(parents=True)
            (registry / "PEER_RUNTIME_BINDINGS.yaml").write_text("[]\n", encoding="utf-8")
            (schema_dir / "peer-runtime-bindings.schema.json").write_text(
                '{"type": "object"}\n',
                encoding="utf-8",
            )
            malformed = conformance.run(AdapterConfig.from_dict(payload))
            malformed_check = next(
                check for check in malformed.checks if check.check_id == "ADAPTER-002"
            )
            self.assertFalse(malformed_check.passed)
            self.assertEqual(malformed.status.value, "FAIL")


if __name__ == "__main__":
    unittest.main()

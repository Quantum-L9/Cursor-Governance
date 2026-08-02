from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

import yaml

TEST_FILE = Path(__file__).resolve()
BASE = TEST_FILE.parents[2]
RUNTIME = BASE / "runtime"
ADAPTERS = BASE / "adapters"
ROUTES = BASE / "routes"
FIXTURES = BASE / "tests" / "fixtures"
sys.path.insert(0, str(RUNTIME))
sys.path.insert(0, str(ADAPTERS))
from graphiti_memory import FileOutboxTransport
from l9_python import L9PythonRepositoryAdapter
from odoo import OdooRepositoryAdapter
from packet_validator import PacketValidator
from routing_engine import RoutingEngine


class Wave3ConformanceTests(unittest.TestCase):
    def test_all_python_files_parse(self) -> None:
        for directory in (RUNTIME, ADAPTERS):
            for path in sorted(directory.glob("*.py")):
                with self.subTest(path=path):
                    ast.parse(path.read_text(encoding="utf-8"))

    def test_all_routes_are_valid_yaml(self) -> None:
        for path in sorted(ROUTES.glob("*.yaml")):
            with self.subTest(path=path):
                payload = yaml.safe_load(path.read_text(encoding="utf-8"))
                self.assertIsInstance(payload, dict)
                self.assertEqual(
                    payload["route_id"],
                    path.stem,
                )

    def test_route_engine_conformance(self) -> None:
        errors = RoutingEngine().validate_routes()
        self.assertEqual(errors, [])

    def test_valid_fixture_passes_packet_validation(
        self,
    ) -> None:
        report = PacketValidator().validate_file(FIXTURES / "valid-recon-packet.json")
        self.assertTrue(
            report.valid,
            report.to_dict(),
        )

    def test_invalid_fixture_fails_packet_validation(
        self,
    ) -> None:
        report = PacketValidator().validate_file(FIXTURES / "invalid-missing-evidence-packet.json")
        self.assertFalse(report.valid)
        codes = {finding.code for finding in report.findings}
        self.assertIn(
            "SGD-EVIDENCE-REQUIRED",
            codes,
        )

    def test_file_outbox_is_idempotent(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as temp:
            transport = FileOutboxTransport(temp)
            payload = {
                "candidate_id": "memcand-idempotent",
                "value": 1,
            }
            first = transport.deliver(payload)
            second = transport.deliver(payload)
            self.assertEqual(
                first["status"],
                "enqueued",
            )
            self.assertEqual(
                second["status"],
                "already_enqueued",
            )

    def test_repository_adapters_have_distinct_policy(
        self,
    ) -> None:
        self.assertTrue(L9PythonRepositoryAdapter().VALIDATION_COMMANDS)
        self.assertEqual(
            OdooRepositoryAdapter().VALIDATION_AUTHORITY["typing"],
            "pyright_basic_editor_guardrail",
        )


if __name__ == "__main__":
    unittest.main()

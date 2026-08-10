from __future__ import annotations

import json
import unittest
from pathlib import Path

from adapters.common.imports import load_module
from jsonschema import Draft202012Validator

SUBSYSTEM = Path(__file__).resolve().parents[1]
REPO_ROOT = SUBSYSTEM.parents[1]


def _readiness_module():
    return load_module(
        SUBSYSTEM / "integrations/bootstrap/peer_readiness.py",
        "pes_test_peer_readiness",
    )


def _context_module():
    return load_module(
        SUBSYSTEM / "integrations/bootstrap/peer_context.py",
        "pes_test_peer_context",
    )


class ExecutablePeerBindingTests(unittest.TestCase):
    def _validator(self):
        schema = json.loads(
            (SUBSYSTEM / "conformance/schemas/executable-peer-readiness.schema.json").read_text()
        )
        Draft202012Validator.check_schema(schema)
        return Draft202012Validator(schema)

    def test_ready_binding_validates_and_passes(self) -> None:
        readiness = _readiness_module().build_readiness(
            SUBSYSTEM, REPO_ROOT, "cursor", "cursor-ide", "cursor-foreground"
        )
        errors = list(self._validator().iter_errors(readiness))
        self.assertEqual(errors, [], errors)
        self.assertEqual(readiness["status"], "READY")
        self.assertTrue(all(v == "PASS" for v in readiness["checks"].values()))
        self.assertEqual(readiness["identity"]["principal_id"], "cursor-memory-client")

    def test_dormant_adapter_binding_is_blocked_not_ready(self) -> None:
        # codex-cloud is dormant: a hypothetical binding must probe BLOCKED.
        readiness = _readiness_module().build_readiness(
            SUBSYSTEM, REPO_ROOT, "codex", "codex-cloud", "codex-cloud"
        )
        errors = list(self._validator().iter_errors(readiness))
        self.assertEqual(errors, [], errors)
        self.assertEqual(readiness["status"], "BLOCKED")
        self.assertEqual(readiness["checks"]["adapter_probe"], "FAIL")

    def test_readiness_is_deterministic_for_fixed_clock(self) -> None:
        import datetime as dt

        fixed = dt.datetime(2026, 8, 10, tzinfo=dt.UTC)
        first = _readiness_module().build_readiness(
            SUBSYSTEM, REPO_ROOT, "cursor", "cursor-ide", "cursor-foreground", now=fixed
        )
        second = _readiness_module().build_readiness(
            SUBSYSTEM, REPO_ROOT, "cursor", "cursor-ide", "cursor-foreground", now=fixed
        )
        self.assertEqual(first["receipt_digest"], second["receipt_digest"])

    def test_context_composes_identity_adapter_autonomy_readiness(self) -> None:
        context = _context_module().build_context(
            SUBSYSTEM, REPO_ROOT, "cursor", "cursor-ide", "cursor-foreground"
        )
        self.assertEqual(context["schema"], "l9.executable-peer-context.v1")
        self.assertEqual(context["agent"]["role"], "orchestrator")
        self.assertEqual(
            context["program_execution"]["contract_family"], "program-execution-system.v2"
        )
        self.assertTrue(context["autonomy"]["canonical"])
        self.assertEqual(context["readiness"]["status"], "READY")


if __name__ == "__main__":
    unittest.main()

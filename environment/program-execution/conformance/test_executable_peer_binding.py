from __future__ import annotations

import unittest
from pathlib import Path

from adapters.common.imports import load_module

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
    def test_ready_binding_validates_and_passes(self) -> None:
        readiness = _readiness_module().build_readiness(
            SUBSYSTEM,
            REPO_ROOT,
            "cursor",
            "cursor-ide",
            "cursor-foreground",
            "worker-default",
        )
        self.assertEqual(readiness["schema"], "l9.executable-peer-readiness.v2")
        self.assertEqual(readiness["identity"]["principal_id"], "cursor-memory-client")
        self.assertEqual(readiness["checks"]["identity_binding"], "PASS")
        self.assertEqual(readiness["checks"]["provider_conformance"], "PASS")
        self.assertEqual(readiness["checks"]["execution_profile"], "PASS")
        self.assertEqual(readiness["checks"]["provider_routable"], "PASS")
        # Unit construction does not supply a live provider probe receipt.
        self.assertEqual(readiness["status"], "BLOCKED")
        self.assertEqual(readiness["blocked_reason"], "provider_probe")

    def test_dormant_adapter_binding_is_blocked_not_ready(self) -> None:
        readiness = _readiness_module().build_readiness(
            SUBSYSTEM,
            REPO_ROOT,
            "codex",
            "codex-cloud",
            "codex-cloud",
            "worker-default",
        )
        self.assertEqual(readiness["schema"], "l9.executable-peer-readiness.v2")
        self.assertEqual(readiness["status"], "BLOCKED")
        self.assertEqual(readiness["checks"]["provider_routable"], "FAIL")

    def test_readiness_is_deterministic_for_fixed_clock(self) -> None:
        import datetime as dt

        fixed = dt.datetime(2026, 8, 10, tzinfo=dt.UTC)
        first = _readiness_module().build_readiness(
            SUBSYSTEM,
            REPO_ROOT,
            "cursor",
            "cursor-ide",
            "cursor-foreground",
            "worker-default",
            now=fixed,
        )
        second = _readiness_module().build_readiness(
            SUBSYSTEM,
            REPO_ROOT,
            "cursor",
            "cursor-ide",
            "cursor-foreground",
            "worker-default",
            now=fixed,
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
        self.assertIn(context["readiness"]["status"], {"READY", "BLOCKED"})
        self.assertTrue(context["readiness"]["receipt_digest"])


if __name__ == "__main__":
    unittest.main()

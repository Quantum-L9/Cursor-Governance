#!/usr/bin/env python3
# L9_META
#   l9_schema: 1
#   repo: Quantum-L9/Cursor-Governance
#   path: environment/agents/tools/test_peer_execution.py
#   layer: test
#   owner: governance-control-plane
#   status: active
#   version: 1.0.0
#   updated: 2026-08-10
"""Regression tests for the peer-execution conformance validator + probe.

Positive: the live repository is a coherent peer topology (all rules pass) and
every executable peer probes READY. Negative: a peer whose program adapter is
absent from the execution registry FAILS, proving the validator bites.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
REPO_ROOT = TOOLS.parents[2]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PeerExecutionConformanceTests(unittest.TestCase):
    def test_live_repo_is_coherent(self) -> None:
        conformance = _load("peer_execution_conformance")
        report = conformance.validate(REPO_ROOT)
        self.assertEqual(report["status"], "PASS", report["errors"])
        self.assertIn("codex", report["executable_peers"])
        self.assertIn("gemini", report["executable_peers"])
        self.assertIn("manus", report["executable_peers"])

    def test_unregistered_program_adapter_fails(self) -> None:
        conformance = _load("peer_execution_conformance")
        model = conformance.PeerExecutionModel(REPO_ROOT)
        # Point an executable peer at an adapter that is not registered.
        model.agents["codex"]["program_execution"]["adapters"] = ["ghost-adapter"]
        errors: list[str] = []
        conformance._check_program_mapping(model, errors)
        self.assertTrue(any("ghost-adapter" in item for item in errors))

    def test_role_authority_rejects_worker_for_reviewer(self) -> None:
        conformance = _load("peer_execution_conformance")
        model = conformance.PeerExecutionModel(REPO_ROOT)
        # A reviewer routed to a worker_host adapter must be rejected (s.14).
        model.agents["gemini"]["program_execution"]["adapters"] = ["codex-cloud"]
        errors: list[str] = []
        conformance._check_role_authority(model, errors)
        self.assertTrue(any("[R6]" in item for item in errors))


class PeerExecutionProbeTests(unittest.TestCase):
    def test_every_executable_peer_is_ready(self) -> None:
        probe = _load("peer_execution_probe")
        report = probe.probe(REPO_ROOT, REPO_ROOT)
        self.assertEqual(report["status"], "PASS")
        peers = {item["peer"]: item["program_execution_ready"] for item in report["peers"]}
        self.assertTrue(all(peers.values()), peers)
        self.assertEqual(set(peers), {"cursor", "claude-code", "codex", "gemini", "manus"})


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
# L9_META
#   l9_schema: 1
#   repo: Quantum-L9/Cursor-Governance
#   path: environment/agents/tools/test_executable_peers.py
#   layer: test
#   owner: governance-control-plane
#   status: active
#   version: 1.0.0
#   updated: 2026-08-10
"""Regression tests for the Executable Peer Contract validator (E1-E15).

Positive: the live repo is coherent and only Wave A (cursor, claude-code) is
enabled. Negatives: each targeted rule bites when its invariant is broken.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
REPO_ROOT = TOOLS.parents[2]


def _load():
    spec = importlib.util.spec_from_file_location(
        "validate_executable_peers", TOOLS / "validate_executable_peers.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExecutablePeerContractTests(unittest.TestCase):
    def test_live_repo_wave_a_only(self) -> None:
        module = _load()
        report = module.validate(REPO_ROOT)
        self.assertEqual(report["status"], "PASS", report["errors"])
        self.assertEqual(set(report["executable_peers"]), {"cursor", "claude-code"})

    def test_e2_enabled_without_binding(self) -> None:
        module = _load()
        model = module.ExecutablePeerModel(REPO_ROOT)
        model.agents["codex"]["execution"] = {"enabled": True, "bindings": []}
        errors: list[str] = []
        module._check_execution_shape(model, errors)
        self.assertTrue(any("[E2]" in e for e in errors), errors)

    def test_e9_binding_to_dormant_adapter(self) -> None:
        module = _load()
        model = module.ExecutablePeerModel(REPO_ROOT)
        model.agents["codex"]["execution"] = {
            "enabled": True,
            "bindings": [{"surface": "codex-cloud", "adapter_id": "codex-cloud"}],
        }
        errors: list[str] = []
        module._check_bindings(model, errors)
        self.assertTrue(any("[E9]" in e for e in errors), errors)

    def test_e15_non_contract_execution_key(self) -> None:
        module = _load()
        model = module.ExecutablePeerModel(REPO_ROOT)
        model.agents["cursor"]["execution"]["status"] = "READY"
        errors: list[str] = []
        module._check_execution_shape(model, errors)
        self.assertTrue(any("[E15]" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()

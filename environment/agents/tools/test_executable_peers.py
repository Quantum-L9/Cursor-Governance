#!/usr/bin/env python3
# L9_META
#   l9_schema: 1
#   repo: Quantum-L9/Cursor-Governance
#   path: environment/agents/tools/test_executable_peers.py
#   layer: test
#   owner: governance-control-plane
#   status: active
#   version: 2.0.0
#   updated: 2026-08-12
"""Regression tests for the Executable Peer Contract validator (E1-E15).

Positive: the live repo is coherent and only Wave A (cursor, claude-code) has
execution.required. Negatives: each targeted rule bites when its invariant is
broken. Also gates that governed readers no longer consume agent_registry.execution.
"""

from __future__ import annotations

import importlib.util
import re
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

    def test_bindings_schema_only_passes(self) -> None:
        module = _load()
        report = module.validate_bindings_schema(REPO_ROOT)
        self.assertEqual(report["status"], "PASS", report["errors"])
        self.assertEqual(report["peer_count"], 5)

    def test_e1_missing_bindings_fails_closed(self) -> None:
        module = _load()
        # Non-repo root has no environment/agents/PEER_RUNTIME_BINDINGS.yaml.
        report = module.validate(REPO_ROOT / "environment" / "agents" / "schemas")
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("[E1]" in e for e in report["errors"]), report["errors"])

    def test_e3_active_agent_omitted(self) -> None:
        module = _load()
        model = module.ExecutablePeerModel(REPO_ROOT)
        del model.peers["codex"]
        errors: list[str] = []
        module._check_registry_coverage(model, errors)
        self.assertTrue(any("[E3]" in e and "codex" in e for e in errors), errors)

    def test_e4_unknown_agent_ref(self) -> None:
        module = _load()
        model = module.ExecutablePeerModel(REPO_ROOT)
        model.peers["cursor"]["agent_ref"] = "not-an-agent"
        errors: list[str] = []
        module._check_agent_refs(model, errors)
        self.assertTrue(any("[E4]" in e for e in errors), errors)

    def test_e6_required_without_binding(self) -> None:
        module = _load()
        model = module.ExecutablePeerModel(REPO_ROOT)
        model.peers["codex"]["execution"] = {"required": True, "bindings": []}
        errors: list[str] = []
        module._check_execution_shape(model, errors)
        self.assertTrue(any("[E6]" in e for e in errors), errors)

    def test_e7_unknown_surface(self) -> None:
        module = _load()
        model = module.ExecutablePeerModel(REPO_ROOT)
        model.peers["cursor"]["execution"]["bindings"] = [
            {"surface": "not-a-surface", "adapter_id": "cursor-foreground"}
        ]
        errors: list[str] = []
        module._check_bindings(model, errors)
        self.assertTrue(any("[E7]" in e for e in errors), errors)

    def test_e8_unknown_adapter(self) -> None:
        module = _load()
        model = module.ExecutablePeerModel(REPO_ROOT)
        model.peers["cursor"]["execution"]["bindings"] = [
            {"surface": "cursor-ide", "adapter_id": "no-such-adapter"}
        ]
        errors: list[str] = []
        module._check_bindings(model, errors)
        self.assertTrue(any("[E8]" in e for e in errors), errors)

    def test_e12_binding_to_dormant_adapter(self) -> None:
        module = _load()
        model = module.ExecutablePeerModel(REPO_ROOT)
        model.peers["codex"]["execution"] = {
            "required": True,
            "bindings": [{"surface": "codex-cloud", "adapter_id": "codex-cloud"}],
        }
        errors: list[str] = []
        module._check_bindings(model, errors)
        self.assertTrue(any("[E12]" in e for e in errors), errors)

    def test_e14_missing_roles_manifest(self) -> None:
        module = _load()
        model = module.ExecutablePeerModel(REPO_ROOT)
        model.peers["cursor"]["subagents"] = {
            "enabled": True,
            "roles_manifest": "environment/agents/does-not-exist.yaml",
            "deployment": {"readiness_required": False},
        }
        errors: list[str] = []
        module._check_no_copied_autonomy_and_carriers(model, errors)
        self.assertTrue(any("[E14]" in e and "roles manifest" in e for e in errors), errors)

    def test_e15_duplicate_peer_binding(self) -> None:
        module = _load()
        model = module.ExecutablePeerModel(REPO_ROOT)
        model.peers["cursor"]["execution"]["bindings"] = [
            {"surface": "cursor-ide", "adapter_id": "cursor-foreground"},
            {"surface": "cursor-ide", "adapter_id": "cursor-foreground"},
        ]
        errors: list[str] = []
        module._check_duplicates_and_identity_plane(model, errors)
        self.assertTrue(any("[E15]" in e and "duplicate" in e for e in errors), errors)

    def test_e15_registry_must_not_carry_execution(self) -> None:
        module = _load()
        model = module.ExecutablePeerModel(REPO_ROOT)
        model.agents["cursor"]["execution"] = {"required": True, "bindings": []}
        errors: list[str] = []
        module._check_duplicates_and_identity_plane(model, errors)
        self.assertTrue(any("[E15]" in e and "agent_registry" in e for e in errors), errors)

    def test_no_dual_read_of_registry_execution(self) -> None:
        validator = (REPO_ROOT / "environment/agents/tools/validate_executable_peers.py").read_text(
            encoding="utf-8"
        )
        probe = (
            REPO_ROOT / "environment/program-execution/scripts/probe_executable_peers.py"
        ).read_text(encoding="utf-8")
        # Validator may load agent_registry for identity FKs only.
        self.assertNotIn('agent.get("execution")', validator)
        self.assertNotRegex(validator, r"""agents\[.*\]\.get\(\s*['\"]execution['\"]""")
        # Probe must read bindings only — never agent_registry.
        self.assertIn("PEER_RUNTIME_BINDINGS.yaml", probe)
        self.assertNotIn("agent_registry.yaml", probe)
        self.assertIsNotNone(re.search(r"execution\.required|get\(\"required\"\)", probe))


if __name__ == "__main__":
    unittest.main()

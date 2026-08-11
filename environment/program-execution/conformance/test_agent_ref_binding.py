from __future__ import annotations

import unittest
from pathlib import Path

import yaml
from adapters.common.imports import load_module

SUBSYSTEM = Path(__file__).resolve().parents[1]
REPO_ROOT = SUBSYSTEM.parents[1]


class AgentRefBindingTests(unittest.TestCase):
    def test_agent_registry_descriptors_declare_matching_agent_ref(self) -> None:
        registry = yaml.safe_load(
            (SUBSYSTEM / "registry/EXECUTION_ADAPTER_REGISTRY.yaml").read_text(encoding="utf-8")
        )
        agents = yaml.safe_load(
            (REPO_ROOT / "environment/agents/agent_registry.yaml").read_text(encoding="utf-8")
        )["agents"]
        checked = 0
        for entry in registry["adapters"]:
            descriptor = yaml.safe_load(
                (SUBSYSTEM / str(entry["descriptor"])).read_text(encoding="utf-8")
            )
            identity = descriptor.get("identity") or {}
            if identity.get("binding") != "agent_registry":
                self.assertIsNone(identity.get("agent_ref"))
                continue
            agent_ref = identity.get("agent_ref")
            self.assertIsNotNone(agent_ref, f"{entry['adapter_id']} missing agent_ref")
            self.assertIn(agent_ref, agents, f"{entry['adapter_id']} agent_ref not registered")
            checked += 1
        self.assertGreater(checked, 0)

    def test_agent_ref_for_resolver_matches_descriptor(self) -> None:
        binding = load_module(
            SUBSYSTEM / "integrations/agent-identity/identity_binding.py",
            "pes_test_agent_ref_resolver",
        )
        self.assertEqual(binding.agent_ref_for(SUBSYSTEM, "cursor-foreground"), "cursor")
        self.assertEqual(binding.agent_ref_for(SUBSYSTEM, "claude-code-direct"), "claude-code")
        # external_receipt adapters bind to controller contract, not the registry.
        self.assertIsNone(binding.agent_ref_for(SUBSYSTEM, "chatgpt-manual-handoff"))


if __name__ == "__main__":
    unittest.main()

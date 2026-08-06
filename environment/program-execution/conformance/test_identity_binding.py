from __future__ import annotations

import unittest
from pathlib import Path

from adapters.common.imports import load_module


class IdentityBindingTests(unittest.TestCase):
    def test_chatgpt_has_no_implicit_registry_identity(self) -> None:
        path = Path(__file__).resolve().parents[1] / "integrations/agent-identity"
        reader_module = load_module(
            path / "registry_reader.py",
            "pes_test_registry_reader",
        )
        binding_module = load_module(
            path / "identity_binding.py",
            "pes_test_identity_binding",
        )
        repository = Path(__file__).resolve().parents[3]
        reader = reader_module.AgentRegistryReader(repository)
        binding = binding_module.bind_identity(reader, "chatgpt-manual-handoff")
        self.assertEqual(binding["binding"], "controller_contract")
        self.assertIsNone(binding["agent_id"])


if __name__ == "__main__":
    unittest.main()

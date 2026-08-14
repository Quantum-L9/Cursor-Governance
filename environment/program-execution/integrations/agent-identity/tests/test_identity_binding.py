from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml
from adapters.common.imports import load_module


class AgentIdentityIntegrationTests(unittest.TestCase):
    def test_registered_cursor_identity_is_reused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            registry = repository / "environment/agents/agent_registry.yaml"
            registry.parent.mkdir(parents=True)
            registry.write_text(
                yaml.safe_dump(
                    {
                        "agents": {
                            "cursor": {
                                "agent_id": "cursor",
                                "principal_id": "cursor-memory-client",
                                "source": "cursor",
                                "status": "active",
                            }
                        }
                    }
                )
            )
            root = Path(__file__).resolve().parents[1]
            reader_module = load_module(
                root / "registry_reader.py",
                "pes_test_identity_registry_reader",
            )
            binding_module = load_module(
                root / "identity_binding.py",
                "pes_test_identity_binding_integration",
            )
            reader = reader_module.AgentRegistryReader(repository)
            # The descriptor's identity.agent_ref foreign key is passed in by the
            # caller (resolved via agent_ref_for); the hardcoded map is gone.
            value = binding_module.bind_identity(reader, agent_ref="cursor")
            self.assertEqual(value["agent_id"], "cursor")


if __name__ == "__main__":
    unittest.main()

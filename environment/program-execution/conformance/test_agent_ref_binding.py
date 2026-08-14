from __future__ import annotations

import unittest
from pathlib import Path

import yaml

SUBSYSTEM = Path(__file__).resolve().parents[1]
REPO_ROOT = SUBSYSTEM.parents[1]


class PeerBindingIdentityTests(unittest.TestCase):
    def test_peer_provider_descriptors_do_not_embed_agent_ref(self) -> None:
        registry = yaml.safe_load(
            (SUBSYSTEM / "registry/EXECUTION_ADAPTER_REGISTRY.yaml").read_text(encoding="utf-8")
        )
        checked = 0
        for entry in registry["adapters"]:
            descriptor = yaml.safe_load(
                (SUBSYSTEM / str(entry["descriptor"])).read_text(encoding="utf-8")
            )
            identity = descriptor.get("identity") or {}
            if identity.get("binding") != "peer_runtime_binding":
                continue
            self.assertNotIn("agent_ref", identity)
            checked += 1
        self.assertGreater(checked, 0)

    def test_peer_bindings_own_agent_provider_profile_correlation(self) -> None:
        bindings = yaml.safe_load(
            (REPO_ROOT / "environment/agents/PEER_RUNTIME_BINDINGS.yaml").read_text(
                encoding="utf-8"
            )
        )
        for peer_key, peer in bindings["peers"].items():
            self.assertEqual(peer["agent_ref"], peer_key)
            for binding in (peer.get("execution") or {}).get("bindings") or []:
                self.assertTrue(binding["provider_ref"])
                self.assertTrue(binding["execution_profile_ref"])
                self.assertNotIn("adapter_id", binding)


if __name__ == "__main__":
    unittest.main()

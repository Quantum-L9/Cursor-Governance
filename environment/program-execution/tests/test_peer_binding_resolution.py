from __future__ import annotations

import unittest
from pathlib import Path

from peer_execution.bindings import resolve_peer_binding

ROOT = Path(__file__).resolve().parents[3]


class PeerBindingResolutionTests(unittest.TestCase):
    def test_valid_full_tuple_resolves(self) -> None:
        binding = resolve_peer_binding(
            ROOT, "gemini", "gemini-cli", "gemini-review", "reviewer-default"
        )
        self.assertEqual(binding.agent_ref, "gemini")
        self.assertEqual(binding.surface, "gemini-cli")
        self.assertEqual(binding.provider_ref, "gemini-review")
        self.assertEqual(binding.execution_profile_ref, "reviewer-default")
        self.assertEqual(binding.autonomy_provider_ref, "root-autonomy-control-plane")

    def test_cross_wired_provider_fails(self) -> None:
        with self.assertRaises(ValueError):
            resolve_peer_binding(
                ROOT, "gemini", "gemini-cli", "claude-code-direct", "reviewer-default"
            )

    def test_cross_wired_profile_fails(self) -> None:
        with self.assertRaises(ValueError):
            resolve_peer_binding(
                ROOT, "gemini", "gemini-cli", "gemini-review", "worker-default"
            )

    def test_surface_only_must_resolve_uniquely(self) -> None:
        with self.assertRaises(ValueError):
            resolve_peer_binding(ROOT, "cursor", "cursor-ide")


if __name__ == "__main__":
    unittest.main()

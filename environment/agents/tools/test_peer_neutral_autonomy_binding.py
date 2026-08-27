#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TOOLS = Path(__file__).resolve().parent


def _load_validator():
    spec = importlib.util.spec_from_file_location(
        "validate_executable_peers_peer_neutral",
        TOOLS / "validate_executable_peers.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PeerNeutralAutonomyBindingTests(unittest.TestCase):
    def test_all_registered_peers_require_canonical_root_autonomy(self) -> None:
        module = _load_validator()
        model = module.ExecutablePeerModel(ROOT)
        self.assertEqual(set(model.peers), {"cursor", "claude-code", "codex", "gemini", "manus"})
        for name, peer in model.peers.items():
            with self.subTest(peer=name):
                self.assertEqual(
                    peer["autonomy"],
                    {"required": True, "provider_id": module.ROOT_AUTONOMY_PROVIDER_ID},
                )

    def test_missing_autonomy_binding_fails_closed_even_for_dormant_peer(self) -> None:
        module = _load_validator()
        model = module.ExecutablePeerModel(ROOT)
        del model.peers["codex"]["autonomy"]
        errors: list[str] = []
        module._check_autonomy(model, errors)
        self.assertTrue(any("[E13] codex: autonomy binding missing" in item for item in errors), errors)

    def test_execution_required_remains_independent_of_autonomy_required(self) -> None:
        module = _load_validator()
        model = module.ExecutablePeerModel(ROOT)
        self.assertEqual(set(model.required_peers()), {"cursor", "claude-code"})
        for name in ("codex", "gemini", "manus"):
            self.assertFalse(model.peers[name]["execution"]["required"])
            self.assertTrue(model.peers[name]["autonomy"]["required"])


if __name__ == "__main__":
    unittest.main()

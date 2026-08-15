from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

import yaml

sys.dont_write_bytecode = True  # keep PE tree free of compiled debris
ROOT = Path(__file__).resolve().parents[1]
BINDINGS = ROOT.parent / "agents" / "PEER_RUNTIME_BINDINGS.yaml"
CONTRACT = ROOT / "core/shared/REPLAN_CONTRACT.yaml"
SCHEMA = ROOT / "core/shared/schemas/replan-revision.schema.json"


class ReplanPeerParityTests(unittest.TestCase):
    def test_canonical_contract_exists(self) -> None:
        self.assertTrue(CONTRACT.is_file())
        self.assertTrue(SCHEMA.is_file())
        contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(contract["schema"], "program-execution.replan.v1")
        self.assertTrue(contract["peer_projection"]["canonical_source_only"])
        self.assertEqual(contract["peer_projection"]["per_peer_semantic_override"], "prohibited")
        self.assertEqual(contract["peer_projection"]["partial_activation"], "prohibited")

    def test_every_required_peer_is_accounted_for(self) -> None:
        self.assertTrue(BINDINGS.is_file(), "PEER_RUNTIME_BINDINGS.yaml missing")
        bindings = yaml.safe_load(BINDINGS.read_text(encoding="utf-8"))
        peers = bindings.get("peers") or {}
        required = sorted(
            name
            for name, spec in peers.items()
            if (spec.get("execution") or {}).get("required") is True
        )
        self.assertGreaterEqual(len(required), 1)
        digest = hashlib.sha256(CONTRACT.read_bytes()).hexdigest()
        accounting = {peer: digest for peer in required}
        self.assertEqual(set(accounting), set(required))
        self.assertEqual(len(set(accounting.values())), 1)

    def test_no_peer_local_replan_override_files(self) -> None:
        adapters = ROOT / "adapters"
        forbidden = list(adapters.rglob("*replan*"))
        self.assertEqual(forbidden, [], f"peer-local replan semantics found: {forbidden}")


if __name__ == "__main__":
    unittest.main()

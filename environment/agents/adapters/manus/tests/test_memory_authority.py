#!/usr/bin/env python3
"""Safety tests for the connector-scoped Manus memory authority materializer."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ADAPTER = Path(__file__).resolve().parents[1]
REPOSITORY = ADAPTER.parents[3]
for root in (str(REPOSITORY), str(ADAPTER)):
    if root not in sys.path:
        sys.path.insert(0, root)

import materialize_memory_authority as authority  # noqa: E402


class ManusMemoryAuthorityTests(unittest.TestCase):
    @staticmethod
    def _scoped_authority() -> dict[str, object]:
        return {
            "agents_door_secret": "d" * 24,
            "agent_signing_keys": {"manus": "m" * 24},
        }

    def test_materializes_only_manus_scoped_files_under_private_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "authority"
            output.mkdir(mode=0o700)
            authority.materialize(REPOSITORY, output, self._scoped_authority())
            tokens = json.loads((output / "agent_tokens.local.json").read_text(encoding="utf-8"))
            grants = json.loads((output / "agent_grants.json").read_text(encoding="utf-8"))
            self.assertEqual(set(tokens), {"agents_door_secret", "agent_signing_keys"})
            self.assertEqual(set(tokens["agent_signing_keys"]), {"manus"})
            self.assertEqual(set(grants), {"grants"})
            self.assertEqual(set(grants["grants"]), {"manus"})
            self.assertEqual((output / "agent_tokens.local.json").stat().st_mode & 0o777, 0o600)
            self.assertEqual((output / "agent_grants.json").stat().st_mode & 0o777, 0o600)

    def test_refuses_human_or_peer_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "authority"
            output.mkdir(mode=0o700)
            human = self._scoped_authority() | {"human_door_secret": "h" * 24}
            with self.assertRaises(authority.AuthorityMaterializationError):
                authority.materialize(REPOSITORY, output, human)
            peer = {
                "agents_door_secret": "d" * 24,
                "agent_signing_keys": {"manus": "m" * 24, "cursor": "c" * 24},
            }
            with self.assertRaises(authority.AuthorityMaterializationError):
                authority.materialize(REPOSITORY, output, peer)

    def test_refuses_a_non_private_runtime_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "authority"
            output.mkdir(mode=0o755)
            with self.assertRaises(authority.AuthorityMaterializationError):
                authority.materialize(REPOSITORY, output, self._scoped_authority())

    def test_public_scoped_tokens_rejects_peer_maps(self) -> None:
        peer = {
            "agents_door_secret": "d" * 24,
            "agent_signing_keys": {"manus": "m" * 24, "cursor": "c" * 24},
        }
        with self.assertRaises(authority.AuthorityMaterializationError):
            authority.scoped_tokens(peer)
        self.assertEqual(
            authority.scoped_tokens(self._scoped_authority())["agent_signing_keys"],
            {"manus": "m" * 24},
        )


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""No Manus credential output; canonical-only pure historical grant assurance."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import unittest.mock as mock
from pathlib import Path

ADAPTER = Path(__file__).resolve().parents[1]
REPOSITORY = ADAPTER.parents[3]
for root in (str(REPOSITORY), str(ADAPTER)):
    if root not in sys.path:
        sys.path.insert(0, root)

import materialize_memory_authority as authority  # noqa: E402


class ManusMemoryAuthorityTests(unittest.TestCase):
    def test_pure_grants_reuse_canonical_assurance_and_do_not_write(self) -> None:
        with mock.patch("builtins.open", wraps=open) as opened:
            grants = authority._manus_grants(REPOSITORY)
        self.assertEqual(set(grants["grants"]), {"manus"})
        self.assertEqual(grants["grants"]["manus"]["user_id"], "manus_agent")
        self.assertFalse(grants["grants"]["manus"].get("is_admin", False))
        for call in opened.call_args_list:
            if len(call.args) > 1:
                self.assertNotIn("w", str(call.args[1]))

    def test_materialization_refuses_before_path_resolution_or_io(self) -> None:
        with (
            mock.patch.object(Path, "resolve", side_effect=AssertionError("no resolve")),
            mock.patch("builtins.open", side_effect=AssertionError("no file I/O")),
        ):
            with self.assertRaisesRegex(authority.AuthorityMaterializationError, "retired"):
                authority.materialize(Path("/unread"), Path("/unwritten"), object())

    def test_human_peer_and_scoped_legacy_tokens_all_refuse(self) -> None:
        for raw in (
            {"human_door_secret": "h" * 24},
            {"agents_door_secret": "d" * 24, "agent_signing_keys": {"manus": "m" * 24}},
            {"agents_door_secret": "d" * 24, "agent_signing_keys": {"cursor": "c" * 24}},
        ):
            with self.assertRaisesRegex(authority.AuthorityMaterializationError, "retired"):
                authority.scoped_tokens(raw)

    def test_cli_refuses_without_reading_stdin_or_creating_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "not-created"
            result = subprocess.run(
                [
                    str(REPOSITORY / ".venv/bin/python"),
                    "-B",
                    str(ADAPTER / "materialize_memory_authority.py"),
                    "--governance",
                    "/missing",
                    "--output-directory",
                    str(output),
                ],
                input="not JSON and must never be parsed",
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("UPSTREAM_BLOCKED", result.stderr)
            self.assertNotIn("not JSON", result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertFalse(output.exists())

    def test_main_does_not_read_authority_stream(self) -> None:
        with mock.patch("sys.stdin.read", side_effect=AssertionError("must not read authority")):
            self.assertEqual(
                authority.main(["--governance", "/missing", "--output-directory", "/missing"]), 2
            )


if __name__ == "__main__":
    unittest.main()

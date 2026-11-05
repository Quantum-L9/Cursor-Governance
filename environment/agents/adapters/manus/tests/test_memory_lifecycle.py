#!/usr/bin/env python3
"""Blocked Manus lifecycle performs no Memory, filesystem or subprocess work."""

from __future__ import annotations

import ast
import os
import sys
import unittest
import unittest.mock as mock
from pathlib import Path

ADAPTER = Path(__file__).resolve().parents[1]
REPOSITORY = ADAPTER.parents[3]
for root in (str(REPOSITORY), str(ADAPTER)):
    if root not in sys.path:
        sys.path.insert(0, root)

import memory_lifecycle as lifecycle  # noqa: E402


class ManusMemoryLifecycleTests(unittest.TestCase):
    def test_inherited_complete_legacy_authority_never_means_native_ready(self) -> None:
        env = {name: "synthetic-stale-value" for name in lifecycle._LEGACY_AUTHORITY_NAMES}
        env.update(L9_MEMORY_AGENT_ID="cursor", USER_ID="foreign", L9_MEMORY_SOURCE="cursor")
        report = lifecycle.signed_agent_door_status(env)
        self.assertEqual(report["status"], "UPSTREAM_BLOCKED")
        self.assertEqual(report["native_client"], "UNBOUND")
        self.assertEqual(report["live"], "UNKNOWN")
        self.assertEqual(report["authentication"], "unverified")
        self.assertEqual(
            report["legacy_environment_present"], list(lifecycle._LEGACY_AUTHORITY_NAMES)
        )
        self.assertNotIn("synthetic-stale-value", str(report))
        self.assertNotIn("foreign", str(report))
        self.assertFalse(report["coding_session_requires_memory"])

    def test_missing_or_present_authority_is_always_refused(self) -> None:
        for env in ({}, {name: "stale" for name in lifecycle._LEGACY_AUTHORITY_NAMES}):
            with self.subTest(env_names=list(env)):
                self.assertEqual(lifecycle.native_memory_status(env)["status"], "UPSTREAM_BLOCKED")
                with self.assertRaisesRegex(lifecycle.MemoryAccessError, "UPSTREAM_BLOCKED"):
                    lifecycle.require_signed_agent_door(env)

    def test_status_reads_names_not_values(self) -> None:
        class NamesOnly(dict):
            def get(self, *args, **kwargs):
                raise AssertionError("status must not inspect a value")

            def __getitem__(self, key):
                raise AssertionError("status must not inspect a value")

        report = lifecycle.native_memory_status(NamesOnly(L9_MEMORY_AGENT_ASSERTION=object()))
        self.assertEqual(report["legacy_environment_present"], ["L9_MEMORY_AGENT_ASSERTION"])

    def test_start_and_close_refuse_before_any_io_or_content_inspection(self) -> None:
        bomb = object()
        with (
            mock.patch.dict(os.environ, {"L9_MEMORY_AGENT_ASSERTION": "stale"}, clear=True),
            mock.patch("builtins.open", side_effect=AssertionError("no file I/O")),
            mock.patch.object(Path, "resolve", side_effect=AssertionError("no fs resolution")),
            mock.patch.object(Path, "read_text", side_effect=AssertionError("no read")),
            mock.patch("subprocess.run", side_effect=AssertionError("no subprocess")),
            mock.patch("tempfile.mkstemp", side_effect=AssertionError("no temporary transcript")),
        ):
            start = lifecycle.start_session(workspace=bomb, task=bomb, session_id=bomb)
            close = lifecycle.close_session_from_manus(
                workspace=bomb, session_id=bomb, summary=bomb, next_action=bomb
            )
        self.assertEqual(start["operation"], "health-only-start")
        self.assertEqual(close["operation"], "close")
        for report in (start, close):
            self.assertEqual(report["status"], "UPSTREAM_BLOCKED")
            self.assertNotIn("session_state_path", report)
            self.assertNotIn("record_ids", report)
            self.assertNotIn("receipt_id", report)
            self.assertNotIn("summary", report)

    def test_lifecycle_has_no_shared_memory_cli_or_native_api_import(self) -> None:
        tree = ast.parse((ADAPTER / "memory_lifecycle.py").read_text(encoding="utf-8"))
        modules = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        self.assertFalse(
            any(
                name and name.startswith(("ops.memory", "ops.graphiti", "l9_graphite_memory"))
                for name in modules
            )
        )
        text = (ADAPTER / "memory_lifecycle.py").read_text(encoding="utf-8")
        self.assertNotIn("canonical_hydrate(", text)
        self.assertNotIn("tempfile.", text)
        self.assertNotIn("subprocess.", text)

    def test_session_identifier_compatibility_is_bounded(self) -> None:
        self.assertEqual(lifecycle.validate_session_id("manus_42.1"), "manus_42.1")
        for value in ("../unexpected", "x" * 121, "", None):
            with self.assertRaises(ValueError):
                lifecycle.validate_session_id(value)


if __name__ == "__main__":
    unittest.main()

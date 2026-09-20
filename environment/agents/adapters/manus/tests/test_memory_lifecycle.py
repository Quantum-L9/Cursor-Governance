#!/usr/bin/env python3
"""Safety tests for the Manus canonical lifecycle wrapper."""

from __future__ import annotations

import os
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

import memory_lifecycle as lifecycle  # noqa: E402


class ManusMemoryLifecycleTests(unittest.TestCase):
    def _ready_env(self) -> dict[str, str]:
        return {
            "L9_MEMORY_AGENT_ID": "manus",
            "USER_ID": "manus_agent",
            "L9_MEMORY_SOURCE": "manus",
            "L9_MEMORY_AGENTS_DOOR_SECRET": "test-door",
            "L9_MEMORY_AGENT_ASSERTION": "test-assertion",
            "L9_MEMORY_AGENT_SIGNING_KEYS_JSON": '{"manus":"test-key"}',
            "L9_MEMORY_AGENT_GRANTS_JSON": '{"manus":{"user_id":"manus_agent"}}',
        }

    def test_signed_agent_status_reports_names_only(self) -> None:
        ready = lifecycle.signed_agent_door_status(self._ready_env())
        self.assertEqual(ready["status"], "ready")
        self.assertEqual(ready["missing"], [])
        self.assertEqual(ready["agent_id"], "manus")
        self.assertNotIn("test-door", str(ready))
        self.assertNotIn("test-assertion", str(ready))

    def test_signed_agent_status_refuses_human_door_and_missing_assertion(self) -> None:
        env = self._ready_env()
        env.pop("L9_MEMORY_AGENT_ASSERTION")
        env["L9_MEMORY_HUMAN_DOOR_SECRET"] = "human-only"
        blocked = lifecycle.signed_agent_door_status(env)
        self.assertEqual(blocked["status"], "unavailable")
        self.assertEqual(blocked["missing"], ["L9_MEMORY_AGENT_ASSERTION"])
        self.assertTrue(any("human memory door" in error for error in blocked["errors"]))
        with self.assertRaises(lifecycle.MemoryAccessError):
            lifecycle.require_signed_agent_door(env)

    def test_start_and_close_refuse_before_any_memory_call_without_signed_door(self) -> None:
        env = {
            "L9_MEMORY_AGENT_ID": "manus",
            "USER_ID": "manus_agent",
            "L9_MEMORY_SOURCE": "manus",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch.object(lifecycle, "canonical_hydrate") as hydrate:
                with self.assertRaises(lifecycle.MemoryAccessError):
                    lifecycle.start_session(
                        workspace=REPOSITORY,
                        task="guard test",
                        session_id="guard-test",
                    )
                hydrate.assert_not_called()
            with mock.patch.object(lifecycle, "close_session") as close:
                with self.assertRaises(lifecycle.MemoryAccessError):
                    lifecycle.close_session_from_manus(
                        workspace=REPOSITORY,
                        session_id="guard-test",
                        summary="guard test",
                        next_action="stop before memory I/O",
                    )
                close.assert_not_called()

    def test_close_source_is_private_and_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as runtime:
            with mock.patch.dict(os.environ, {"XDG_RUNTIME_DIR": runtime}, clear=False):
                source = lifecycle._close_transcript(summary="completed", next_action="resume")
            try:
                self.assertEqual(source.parent, Path(runtime))
                self.assertEqual(source.stat().st_mode & 0o777, 0o600)
                self.assertIn("assistant: completed", source.read_text(encoding="utf-8"))
            finally:
                source.unlink(missing_ok=True)

    def test_session_identifier_is_bounded_and_safe(self) -> None:
        self.assertEqual(lifecycle.validate_session_id("manus_42.1"), "manus_42.1")
        with self.assertRaises(ValueError):
            lifecycle.validate_session_id("../unexpected")
        with self.assertRaises(ValueError):
            lifecycle.validate_session_id("x" * 121)


if __name__ == "__main__":
    unittest.main()

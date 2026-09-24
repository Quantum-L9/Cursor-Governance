#!/usr/bin/env python3
"""Runtime writer-identity enforcement (policy layer only — Graphiti front door)."""

from __future__ import annotations

import sys
import unittest.mock
from pathlib import Path

CLAUDE_DIR = Path(__file__).resolve().parent.parent
MEM = CLAUDE_DIR / "memory"
sys.path.insert(0, str(MEM))

import memory_state as st  # noqa: E402
from errors import MemoryWriteDenied  # noqa: E402

CLAUDE = {
    "agent_id": "claude-code-desktop",
    "user_id": "claude_code_desktop_agent",
    "namespace": "cursor-governance",
}


class ValidateMemoryWriter(unittest.TestCase):
    def test_distinct_claude_writer_shared_namespace_passes(self) -> None:
        st.validate_memory_writer(dict(CLAUDE))

    def test_missing_namespace_denies_write(self) -> None:
        ident = {"agent_id": "claude-code-desktop", "user_id": "claude_code_desktop_agent"}
        with self.assertRaises(MemoryWriteDenied):
            st.validate_memory_writer(ident)

    def test_missing_agent_id_denies_write(self) -> None:
        ident = {
            "agent_id": "",
            "user_id": "claude_code_desktop_agent",
            "namespace": "cursor-governance",
        }
        with self.assertRaises(MemoryWriteDenied):
            st.validate_memory_writer(ident)

    def test_missing_user_id_denies_write(self) -> None:
        ident = {"agent_id": "claude-code-desktop", "user_id": "", "namespace": "cursor-governance"}
        with self.assertRaises(MemoryWriteDenied):
            st.validate_memory_writer(ident)

    def test_cursor_agent_agent_id_denies_claude_write(self) -> None:
        ident = {**CLAUDE, "agent_id": "cursor_agent"}
        with self.assertRaises(MemoryWriteDenied):
            st.validate_memory_writer(ident)

    def test_cursor_agent_user_id_denies_claude_write(self) -> None:
        ident = {**CLAUDE, "user_id": "cursor_agent"}
        with self.assertRaises(MemoryWriteDenied):
            st.validate_memory_writer(ident)

    def test_cursor_dash_agent_variant_denied(self) -> None:
        ident = {**CLAUDE, "agent_id": "cursor-agent"}
        with self.assertRaises(MemoryWriteDenied):
            st.validate_memory_writer(ident)


class ResolveWriterIdentity(unittest.TestCase):
    def test_unset_identity_denies_when_require_explicit(self) -> None:
        with unittest.mock.patch.dict("os.environ", {}, clear=True):
            ident = st.resolve_writer_identity(require_explicit=True)
        self.assertEqual(ident, {"agent_id": "", "user_id": ""})
        ident["namespace"] = "cursor-governance"
        with self.assertRaises(MemoryWriteDenied):
            st.validate_memory_writer(ident)

    def test_there_is_no_default_identity_in_any_mode(self) -> None:
        """A default would attribute a write to a surface that did not run."""
        with unittest.mock.patch.dict("os.environ", {}, clear=True):
            ident = st.resolve_writer_identity(require_explicit=False)
        self.assertEqual(ident, {"agent_id": "", "user_id": ""})

    def test_the_identity_is_derived_and_configured_values_are_ignored(self) -> None:
        configured = {"L9_MEMORY_AGENT_ID": "claude-code", "USER_ID": "claude_code_agent"}
        desktop = {**configured, "CLAUDECODE": "1"}
        with unittest.mock.patch.dict("os.environ", desktop, clear=True):
            ident = st.resolve_writer_identity(require_explicit=True)
        self.assertEqual(
            ident, {"agent_id": "claude-code-desktop", "user_id": "claude_code_desktop_agent"}
        )
        mobile = {
            **desktop,
            "CLAUDE_CODE_REMOTE": "true",
            "CLAUDE_CODE_ENTRYPOINT": "remote_mobile",
        }
        with unittest.mock.patch.dict("os.environ", mobile, clear=True):
            ident = st.resolve_writer_identity(require_explicit=True)
        self.assertEqual(
            ident, {"agent_id": "claude-code-mobile", "user_id": "claude_code_mobile_agent"}
        )

    def test_the_retired_single_identity_is_denied(self) -> None:
        with unittest.mock.patch.dict(
            "os.environ", {"L9_MEMORY_AGENT_ID": "claude-code"}, clear=True
        ):
            ident = st.resolve_writer_identity(require_explicit=True)
        self.assertEqual(ident, {"agent_id": "", "user_id": ""})


class NoHttpSideDoor(unittest.TestCase):
    def test_memory_client_deleted(self) -> None:
        self.assertFalse((MEM / "memory_client.py").exists())

    def test_memory_bridge_present_and_legacy_bridge_gone(self) -> None:
        self.assertTrue((MEM / "memory_bridge.py").is_file())
        self.assertFalse((MEM / "graphiti_bridge.py").exists())


if __name__ == "__main__":
    unittest.main()

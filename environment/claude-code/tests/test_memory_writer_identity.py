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
    "agent_id": "claude-code",
    "user_id": "claude_code_agent",
    "namespace": "cursor-governance",
}


class ValidateMemoryWriter(unittest.TestCase):
    def test_distinct_claude_writer_shared_namespace_passes(self) -> None:
        st.validate_memory_writer(dict(CLAUDE))

    def test_missing_namespace_denies_write(self) -> None:
        ident = {"agent_id": "claude-code", "user_id": "claude_code_agent"}
        with self.assertRaises(MemoryWriteDenied):
            st.validate_memory_writer(ident)

    def test_missing_agent_id_denies_write(self) -> None:
        ident = {"agent_id": "", "user_id": "claude_code_agent", "namespace": "cursor-governance"}
        with self.assertRaises(MemoryWriteDenied):
            st.validate_memory_writer(ident)

    def test_missing_user_id_denies_write(self) -> None:
        ident = {"agent_id": "claude-code", "user_id": "", "namespace": "cursor-governance"}
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

    def test_defaults_apply_only_in_bootstrap_mode(self) -> None:
        with unittest.mock.patch.dict("os.environ", {}, clear=True):
            ident = st.resolve_writer_identity(require_explicit=False)
        self.assertEqual(ident, {"agent_id": "claude-code", "user_id": "claude_code_agent"})

    def test_explicit_env_is_read_verbatim(self) -> None:
        env = {"L9_MEMORY_AGENT_ID": "claude-code", "USER_ID": "claude_code_agent"}
        with unittest.mock.patch.dict("os.environ", env, clear=True):
            ident = st.resolve_writer_identity(require_explicit=True)
        self.assertEqual(ident, {"agent_id": "claude-code", "user_id": "claude_code_agent"})


class NoHttpSideDoor(unittest.TestCase):
    def test_memory_client_deleted(self) -> None:
        self.assertFalse((MEM / "memory_client.py").exists())

    def test_graphiti_bridge_present(self) -> None:
        self.assertTrue((MEM / "graphiti_bridge.py").is_file())


if __name__ == "__main__":
    unittest.main()

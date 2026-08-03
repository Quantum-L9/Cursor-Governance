#!/usr/bin/env python3
"""Runtime writer-identity enforcement on the memory write path (M1).

Network-free: exercises the pure attribution policy in ``memory_state`` and the
client-side guard in ``memory_client`` with ``tool_call`` patched out, so the
suite is green with or without a reachable memory server. Proves that writes
carrying missing or Cursor-reserved identity are denied while reads stay open.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

CLAUDE_DIR = Path(__file__).resolve().parent.parent
MEM = CLAUDE_DIR / "memory"
sys.path.insert(0, str(MEM))

import memory_client as mc  # noqa: E402
import memory_state as st  # noqa: E402
from errors import MemoryWriteDenied  # noqa: E402

CLAUDE = {
    "agent_id": "claude-code",
    "user_id": "claude_code_agent",
    "namespace": "cursor-governance",
}


class ValidateMemoryWriter(unittest.TestCase):
    def test_distinct_claude_writer_shared_namespace_passes(self) -> None:
        # A fully-attributed Claude identity on the shared namespace is allowed.
        self.assertIsNone(st.validate_memory_writer(dict(CLAUDE)))

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
        with mock.patch.dict("os.environ", {}, clear=True):
            ident = st.resolve_writer_identity(require_explicit=True)
        self.assertEqual(ident, {"agent_id": "", "user_id": ""})
        ident["namespace"] = "cursor-governance"
        with self.assertRaises(MemoryWriteDenied):
            st.validate_memory_writer(ident)

    def test_defaults_apply_only_in_bootstrap_mode(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True):
            ident = st.resolve_writer_identity(require_explicit=False)
        self.assertEqual(ident, {"agent_id": "claude-code", "user_id": "claude_code_agent"})

    def test_explicit_env_is_read_verbatim(self) -> None:
        env = {"L9_MEMORY_AGENT_ID": "claude-code", "USER_ID": "claude_code_agent"}
        with mock.patch.dict("os.environ", env, clear=True):
            ident = st.resolve_writer_identity(require_explicit=True)
        self.assertEqual(ident, {"agent_id": "claude-code", "user_id": "claude_code_agent"})


class ClientWriteGuard(unittest.TestCase):
    """The guard fires on writes (ingest/phase_lock) but never on reads."""

    def test_ingest_denies_reserved_identity_without_network(self) -> None:
        env = {"L9_MEMORY_AGENT_ID": "cursor_agent", "USER_ID": "claude_code_agent"}
        with (
            mock.patch.dict("os.environ", env, clear=True),
            mock.patch.object(mc, "tool_call") as tool_call,
        ):
            with self.assertRaises(MemoryWriteDenied):
                mc.ingest({"namespace": "cursor-governance", "content": "x"})
            tool_call.assert_not_called()  # denied before the network POST

    def test_phase_lock_denies_missing_identity_without_network(self) -> None:
        with (
            mock.patch.dict("os.environ", {}, clear=True),
            mock.patch.object(mc, "tool_call") as tool_call,
        ):
            with self.assertRaises(MemoryWriteDenied):
                mc.phase_lock("cursor-governance", "sig")
            tool_call.assert_not_called()

    def test_memory_read_remains_available_when_write_identity_fails(self) -> None:
        # Reserved identity blocks writes but must NOT block reads.
        env = {"L9_MEMORY_AGENT_ID": "cursor_agent", "USER_ID": "cursor_agent"}
        sentinel = {"results": []}
        with (
            mock.patch.dict("os.environ", env, clear=True),
            mock.patch.object(mc, "tool_call", return_value=sentinel) as tool_call,
        ):
            self.assertEqual(mc.search("q", ["cursor-governance"]), sentinel)
            tool_call.assert_called_once()


if __name__ == "__main__":
    unittest.main()

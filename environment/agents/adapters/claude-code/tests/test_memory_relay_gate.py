#!/usr/bin/env python3
"""The Stop gate for relay-carrier hook records (CANONICAL_LAW §8.11).

A relay entry is owed to the shared store from the moment a hook queues it.
``memory_writeback._relay_gate`` blocks the Stop with the exact connector calls
while any entry lacks an acknowledgement, clears once each is acked with a
connector receipt id, and stops blocking (but keeps announcing) after
``RELAY_MAX_ASKS`` requests per entry so a session that cannot reach the
connector is never trapped.
"""

from __future__ import annotations

import importlib.util
import io
import sys
import types
import unittest
import unittest.mock as mock
import uuid
from contextlib import redirect_stderr
from pathlib import Path

CLAUDE_DIR = Path(__file__).resolve().parent.parent
HOOKS = CLAUDE_DIR / "hooks"
MEM = CLAUDE_DIR / "memory"
for _p in (str(MEM), str(HOOKS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

REPO_ROOT = CLAUDE_DIR.parents[3]


def _tree_relay() -> types.ModuleType:
    """The relay module from the tree under test, never the SSOT's copy."""
    spec = importlib.util.spec_from_file_location(
        "ops.memory.relay", REPO_ROOT / "ops/memory/relay.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RelayGateTests(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile

        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "repo"
        (self.root / ".git").mkdir(parents=True)
        self.gov = Path(self._tmp.name) / "governance"
        (self.gov / ".git").mkdir(parents=True)
        self.relay = _tree_relay()
        import memory_writeback as wb  # noqa: PLC0415

        self.wb = wb
        self._patches = [
            mock.patch.dict(sys.modules, {"ops.memory.relay": self.relay}),
            mock.patch.object(wb.mb, "ensure_importable", lambda *a, **k: REPO_ROOT),
            mock.patch.object(wb.mb, "find_governance_root", lambda *a, **k: self.gov),
            mock.patch.object(wb, "_shared_workspace_roots", lambda ws, cap=64: [self.root]),
        ]
        for patcher in self._patches:
            patcher.start()

    def tearDown(self) -> None:
        for patcher in reversed(self._patches):
            patcher.stop()
        self._tmp.cleanup()

    def _queue(self, content: str = "c") -> str:
        entry = self.relay.enqueue(
            self.root,
            surface="pr-publish",
            operation="write",
            arguments={"namespace": "cursor-governance", "content": content},
        )
        return str(entry["id"])

    def test_nothing_owed_does_not_block(self) -> None:
        self.assertIsNone(self.wb._relay_gate(self.root))

    def test_owed_entry_blocks_with_the_connector_call_and_ack(self) -> None:
        ident = self._queue()
        reason = self.wb._relay_gate(self.root)
        self.assertIsNotNone(reason)
        assert reason is not None
        self.assertIn("memory.write_agent", reason)
        self.assertIn(f"python -m ops.memory.relay ack {ident}", reason)

    def test_acked_entry_clears_the_gate(self) -> None:
        ident = self._queue()
        self.assertIsNotNone(self.wb._relay_gate(self.root))
        self.relay.ack(self.root, ident, str(uuid.uuid4()))
        self.assertIsNone(self.wb._relay_gate(self.root))

    def test_gate_stops_blocking_after_max_asks_but_keeps_announcing(self) -> None:
        self._queue()
        for _ in range(self.wb.RELAY_MAX_ASKS):
            self.assertIsNotNone(self.wb._relay_gate(self.root))
        err = io.StringIO()
        with redirect_stderr(err):
            self.assertIsNone(self.wb._relay_gate(self.root))
        self.assertIn("STILL OWED", err.getvalue())
        self.assertEqual(len(self.relay.pending(self.root)), 1, "the entry stays owed")

    def test_a_new_entry_blocks_again_after_an_old_one_is_exhausted(self) -> None:
        self._queue("old")
        for _ in range(self.wb.RELAY_MAX_ASKS):
            self.wb._relay_gate(self.root)
        new = self._queue("new")
        with redirect_stderr(io.StringIO()):
            reason = self.wb._relay_gate(self.root)
        self.assertIsNotNone(reason)
        assert reason is not None
        self.assertIn(new, reason)

    def test_the_governance_writers_outbox_is_scanned_too(self) -> None:
        """Review finding on #1008: governance_handoff_writeback queues under the
        governance clone, which a consumer workspace's roots do not include."""
        entry = self.relay.enqueue(
            self.gov,
            surface="claude-governance-handoff",
            operation="write",
            arguments={"namespace": "cursor-governance", "content": "friction"},
        )
        reason = self.wb._relay_gate(self.root)
        self.assertIsNotNone(reason)
        assert reason is not None
        self.assertIn(str(entry["id"]), reason)


if __name__ == "__main__":
    unittest.main()

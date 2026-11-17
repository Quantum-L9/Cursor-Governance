#!/usr/bin/env python3
"""The Stop gate for relay-carrier hook records (CANONICAL_LAW §8.11).

A relay entry is owed to the shared store from the moment a hook queues it.
``memory_writeback._relay_gate`` blocks the Stop with the exact connector calls
while any entry lacks an acknowledgement, clears once each is acked with a
connector receipt id, and stops blocking (but keeps announcing) after
``RELAY_MAX_ASKS`` requests per entry so a session that cannot reach the
connector is never trapped. An entry the connector refused (``relay refuse``)
never blocks but is announced on every Stop until a later ack supersedes it.
"""

from __future__ import annotations

import importlib.util
import io
import json
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
            mock.patch.object(wb.mb, "ensure_importable", return_value=REPO_ROOT),
            mock.patch.object(wb.mb, "find_governance_root", return_value=self.gov),
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

    def _refuse(self, ident: str) -> str:
        receipt = str(uuid.uuid4())
        self.relay.refuse(self.root, ident, receipt, "namespace did not match any write grant")
        return receipt

    def _main(self, stop_output: str = "") -> dict:
        """Run the Stop hook's ``main`` with ``_stop`` printing ``stop_output``."""

        def fake_stop(_event: dict) -> int:
            if stop_output:
                print(stop_output)
            return 0

        out = io.StringIO()
        with (
            mock.patch.object(sys, "stdin", io.StringIO('{"session_id": "s"}')),
            mock.patch.object(sys, "stdout", out),
            mock.patch.object(self.wb, "_stop", fake_stop),
            mock.patch.object(self.wb.st, "workspace_root", return_value=self.root),
        ):
            self.assertEqual(self.wb.main(), 0)
        text = out.getvalue().strip()
        return json.loads(text) if text else {}

    def test_refused_entry_no_longer_blocks(self) -> None:
        ident = self._queue()
        self.assertIsNotNone(self.wb._relay_gate(self.root))
        receipt = self._refuse(ident)
        self.assertIsNone(self.wb._relay_gate(self.root))
        notice = self.wb._relay_refusal_notice(self.root)
        assert notice is not None
        self.assertIn("REFUSED by the connector, not blocking", notice)
        self.assertIn(ident, notice)
        self.assertIn(receipt, notice)

    def test_refused_only_stop_announces_to_the_user(self) -> None:
        """Copilot review on #1018: stderr reaches no one, so a refused-only Stop
        must still emit a user-visible systemMessage, and must not block."""
        ident = self._queue()
        receipt = self._refuse(ident)
        payload = self._main()
        self.assertNotIn("decision", payload)
        self.assertIn(ident, payload["systemMessage"])
        self.assertIn(receipt, payload["systemMessage"])

    def test_refusal_notice_merges_into_an_existing_system_message(self) -> None:
        ident = self._queue()
        self._refuse(ident)
        payload = self._main(json.dumps({"systemMessage": "write-back announced"}))
        self.assertTrue(payload["systemMessage"].startswith("write-back announced\n\n"))
        self.assertIn(ident, payload["systemMessage"])

    def test_refusal_notice_rides_alongside_a_block_once(self) -> None:
        refused = self._queue("refused")
        self._refuse(refused)
        owed = self._queue("owed")
        reason = self.wb._relay_gate(self.root)
        assert reason is not None
        self.assertIn(f"python -m ops.memory.relay ack {owed}", reason)
        self.assertNotIn(f"python -m ops.memory.relay ack {refused}", reason)
        payload = self._main(json.dumps({"decision": "block", "reason": reason}))
        self.assertEqual(payload["decision"], "block")
        self.assertEqual(payload["reason"], reason, "the block reason is left as the gate wrote it")
        self.assertEqual(payload["systemMessage"].count(f"[{refused}]"), 1)

    def test_subagent_stop_carries_no_refusal_notice(self) -> None:
        self._refuse(self._queue())
        out = io.StringIO()
        with (
            mock.patch.object(sys, "stdin", io.StringIO('{"session_id": "s"}')),
            mock.patch.object(sys, "stdout", out),
            mock.patch.object(self.wb, "_stop", lambda _e: 0),
            mock.patch.object(self.wb.pp, "is_subagent", return_value=True),
        ):
            self.assertEqual(self.wb.main(), 0)
        self.assertEqual(out.getvalue(), "")

    def test_unparseable_stop_output_is_never_rewritten(self) -> None:
        self._refuse(self._queue())
        err = io.StringIO()
        with redirect_stderr(err):
            merged = self.wb._with_notice("not json\n", "NOTICE")
        self.assertEqual(merged, "not json\n")
        self.assertIn("NOTICE", err.getvalue())

    def test_refused_entry_stays_listed_on_every_stop(self) -> None:
        ident = self._queue()
        self._refuse(ident)
        for _ in range(self.wb.RELAY_MAX_ASKS + 2):
            self.assertIsNone(self.wb._relay_gate(self.root))
            self.assertIn(ident, self._main().get("systemMessage", ""), "never silently dropped")
        self.assertEqual([r["id"] for r in self.relay.pending(self.root)], [ident])

    def test_ack_after_refusal_clears_it(self) -> None:
        ident = self._queue()
        self._refuse(ident)
        self.relay.ack(self.root, ident, str(uuid.uuid4()))
        self.assertIsNone(self.wb._relay_gate(self.root))
        self.assertIsNone(self.wb._relay_refusal_notice(self.root))
        self.assertEqual(self._main(), {}, "nothing to announce once acked")
        self.assertEqual(self.relay.pending(self.root), [])

    def test_block_reason_names_the_refuse_verb(self) -> None:
        ident = self._queue()
        reason = self.wb._relay_gate(self.root)
        assert reason is not None
        self.assertIn(f"python -m ops.memory.relay refuse {ident} --receipt <receipt_id>", reason)

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

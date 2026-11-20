#!/usr/bin/env python3
"""The Stop gate for relay-carrier hook records (CANONICAL_LAW §8.11 as amended).

A relay entry is owed to the shared store from the moment a hook queues it.
Since ADR-0055 (operator decision 2026-11-17) ``memory_writeback._relay_gate``
never blocks a Stop and never asks the agent for a connector call: on a hosted
surface it drains the outbox through the hosted transport; otherwise it keeps
the entries and prints at most one non-blocking notice per session.
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

    def _gate(self, marker: Path | None = None) -> tuple[object, str]:
        err = io.StringIO()
        with redirect_stderr(err):
            result = self.wb._relay_gate(self.root, marker)
        return result, err.getvalue()

    def test_nothing_owed_does_not_block_or_announce(self) -> None:
        result, err = self._gate()
        self.assertIsNone(result)
        self.assertEqual(err, "")

    def test_owed_entries_never_block_and_ask_for_no_connector_call(self) -> None:
        """ADR-0055 operator amendment: the relay gate never blocks a turn."""
        ident = self._queue()
        result, err = self._gate()
        self.assertIsNone(result, "the relay gate must never return a block reason")
        self.assertIn("1 hook record(s) still owed", err)
        self.assertNotIn("memory.write_agent", err)
        self.assertNotIn("ack", err.replace("acked", ""))
        self.assertEqual([row["id"] for row in self.relay.pending(self.root)], [ident])

    def test_the_notice_is_printed_at_most_once_per_session(self) -> None:
        self._queue("a")
        marker = Path(self._tmp.name) / "state" / "sess.relay-notice"
        _, first = self._gate(marker)
        self._queue("b")
        _, second = self._gate(marker)
        self.assertEqual(first.count("still owed"), 1)
        self.assertEqual(second, "")
        self.assertEqual(len(self.relay.pending(self.root)), 2, "entries are kept")

    def test_existing_entries_are_kept_across_stops(self) -> None:
        idents = {self._queue("x"), self._queue("y")}
        for _ in range(5):
            self._gate()
        self.assertEqual({row["id"] for row in self.relay.pending(self.root)}, idents)

    def test_the_governance_writers_outbox_is_counted_too(self) -> None:
        """Review finding on #1008: governance_handoff_writeback queues under the
        governance clone, which a consumer workspace's roots do not include."""
        self.relay.enqueue(
            self.gov,
            surface="claude-governance-handoff",
            operation="write",
            arguments={"namespace": "cursor-governance", "content": "friction"},
        )
        result, err = self._gate()
        self.assertIsNone(result)
        self.assertIn(str(self.gov.resolve()), err)


class _FakeHostedResult:
    def __init__(self, verdict: str, receipt_id: str | None = None, reason: str | None = None):
        self.verdict = verdict
        self.receipt_id = receipt_id
        self.reason = reason

    @property
    def ok(self) -> bool:
        return self.verdict == "ok"

    @property
    def refused(self) -> bool:
        return self.verdict == "refused"


class _FakeHostedTransport:
    """Answers per entry content: ``ok-*`` acks, ``refuse-*`` refuses, else down."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def call(self, operation: str, arguments: dict) -> _FakeHostedResult:
        self.calls.append((operation, dict(arguments)))
        content = str(arguments.get("content", ""))
        if content.startswith("ok"):
            return _FakeHostedResult("ok", receipt_id=str(uuid.uuid4()))
        if content.startswith("refuse"):
            return _FakeHostedResult("refused", reason="rejected: namespace not granted")
        return _FakeHostedResult("unavailable", reason="URLError reaching the endpoint")


class HostedDrainGateTests(RelayGateTests):
    # Inherits the relay-gate tests with entries the fake transport cannot carry
    # ("c", "a", "x", "friction"): a failed drain leaves the relay contract intact.

    """ADR-0055: on a hosted surface the Stop hook drains before it asks."""

    def setUp(self) -> None:
        super().setUp()
        self.transport = _FakeHostedTransport()
        self.active = mock.Mock(return_value=True)
        for patcher in (
            mock.patch.object(self.wb, "_hosted_carrier_active", self.active),
            mock.patch.object(self.wb, "_hosted_transport", lambda: self.transport),
        ):
            patcher.start()
            self._patches.append(patcher)

    def test_drained_entries_are_acked_and_nothing_is_announced(self) -> None:
        first, second = self._queue("ok-1"), self._queue("ok-2")
        result, err = self._gate()
        self.assertIsNone(result)
        self.assertNotIn("still owed", err)
        self.assertEqual(self.relay.pending(self.root), [])
        self.assertEqual(set(self.relay.acks(self.root)), {first, second})

    def test_a_refusal_is_settled_not_asked_for(self) -> None:
        refused = self._queue("refuse-1")
        result, _err = self._gate()
        self.assertIsNone(result)
        self.assertIn("namespace not granted", self.relay.rejects(self.root)[refused]["refusal"])

    def test_only_what_is_still_owed_is_announced(self) -> None:
        self._queue("ok-1")
        owed = self._queue("down-1")
        result, err = self._gate()
        self.assertIsNone(result)
        self.assertIn("1 hook record(s) still owed", err)
        self.assertEqual([row["id"] for row in self.relay.pending(self.root)], [owed])

    def test_an_empty_outbox_asks_nothing_and_resolves_no_carrier(self) -> None:
        result, err = self._gate()
        self.assertIsNone(result)
        self.assertEqual(err, "")
        self.active.assert_not_called()
        self.assertEqual(self.transport.calls, [])

    def test_a_relay_surface_does_not_drain(self) -> None:
        self.active.return_value = False
        self._queue("ok-1")
        result, err = self._gate()
        self.assertIsNone(result)
        self.assertIn("still owed", err)
        self.assertEqual(self.transport.calls, [])


if __name__ == "__main__":
    unittest.main()

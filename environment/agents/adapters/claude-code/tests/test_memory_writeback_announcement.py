#!/usr/bin/env python3
"""The Stop write-back announces what it wrote — and what it failed to write.

The close writes durable memory from a Stop hook whose stderr no one sees, so
writes and failures alike were silent: a dead close path (the receipt-key
mismatch) went unnoticed. These pin the audit contract: every durable write and
every failure produces one formal, user-visible announcement naming exactly
what was written and how to verify it; an idempotent skip stays silent; a
non-write outcome is announced once, not every turn. No new memory write.
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import types
import unittest
import unittest.mock as mock
from contextlib import redirect_stdout
from pathlib import Path

CLAUDE_DIR = Path(__file__).resolve().parent.parent
HOOKS = CLAUDE_DIR / "hooks"
MEM = CLAUDE_DIR / "memory"
for _p in (str(MEM), str(HOOKS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import memory_state as st  # noqa: E402

SESSION = "sess-announce"


def _written_report() -> dict:
    return {
        "status": "closed_canonically",
        "group_id": "website-bot",
        "writes": [
            {"kind": "session_continuation", "written": True, "record_id": "rec-cont-1"},
            {"kind": "close", "written": True, "record_id": "rec-close-1"},
        ],
        "pickup": {
            "active_objective": "Ship the checkout flow",
            "next_action": "Merge PR #12 after review",
            "blockers": ["waiting on API key"],
            "decisions": ["use Stripe"],
            "unfinished_work": ["refund path"],
        },
    }


class ComposeAnnouncementTest(unittest.TestCase):
    def setUp(self) -> None:
        sys.modules.pop("memory_writeback", None)
        import memory_writeback as wb  # noqa: PLC0415

        self.wb = wb
        self.repo = Path("/work/website-bot")

    def test_a_write_names_what_was_written_and_how_to_verify(self) -> None:
        text = self.wb.compose_announcement(SESSION, [(self.repo, _written_report())], [])
        assert text is not None
        self.assertIn("L9 MEMORY WRITE-BACK — WRITTEN", text)
        self.assertIn("namespace website-bot: closed_canonically", text)
        self.assertIn("session_continuation: written, id rec-cont-1", text)
        self.assertIn("close: written, id rec-close-1", text)
        for fragment in (
            "Ship the checkout flow",
            "waiting on API key",
            "use Stripe",
            "refund path",
        ):
            self.assertIn(fragment, text)
        self.assertIn(f"ops.memory.cli search {SESSION} --tag session_continuation", text)

    def test_an_idempotent_skip_announces_nothing(self) -> None:
        skipped = {"status": "idempotent_skip", "writes": []}
        self.assertIsNone(self.wb.compose_announcement(SESSION, [(self.repo, skipped)], []))

    def test_a_failed_close_is_announced_as_failed(self) -> None:
        failed = {
            "status": "close_incomplete",
            "group_id": "website-bot",
            "writes": [{"kind": "session_continuation", "written": False, "status": "TIMEOUT"}],
        }
        text = self.wb.compose_announcement(SESSION, [(self.repo, failed)], [])
        assert text is not None
        self.assertIn("— FAILED", text)
        self.assertIn("NOT written (TIMEOUT)", text)
        self.assertNotIn("verify (any later session)", text, "nothing to verify")

    def test_a_partial_close_says_partial(self) -> None:
        failed = {"status": "error", "writes": []}
        text = self.wb.compose_announcement(
            SESSION, [(self.repo, _written_report()), (Path("/work/api"), failed)], []
        )
        assert text is not None
        self.assertIn("— PARTIAL", text)

    def test_a_deferred_root_is_named(self) -> None:
        text = self.wb.compose_announcement(SESSION, [], ["/work/api"])
        assert text is not None
        self.assertIn("api: NOT closed", text)


class HookAnnouncementTest(unittest.TestCase):
    """End to end through main(): stdout carries a Stop-hook systemMessage."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.workspace = Path(self._tmp.name).resolve()
        (self.workspace / ".git").mkdir()

    def _run(self, *, prefetched: bool, report: dict | None = None) -> tuple[str, dict]:
        stub = types.ModuleType("ops.graphiti.hydration.close_session")
        stub.close_session = lambda **_kw: report or {"status": "idempotent_skip", "writes": []}
        env = {"CLAUDE_PROJECT_DIR": str(self.workspace), "L9_MEMORY_AGENT_ID": "claude-code"}
        with (
            mock.patch.dict(sys.modules, {"ops.graphiti.hydration.close_session": stub}),
            mock.patch.dict("os.environ", env, clear=False),
        ):
            contract = st.load_contract()
            if prefetched:
                receipt_id = st.resolve_receipt_id(event={"session_id": SESSION})
                st.write_receipt(
                    contract,
                    receipt_id,
                    {
                        "status": "prefetched",
                        "degraded": False,
                        "hydrated_roots": [str(self.workspace)],
                    },
                )
            sys.modules.pop("memory_writeback", None)
            import memory_writeback as wb  # noqa: PLC0415

            out = io.StringIO()
            with (
                mock.patch.object(sys, "stdin", io.StringIO(json.dumps({"session_id": SESSION}))),
                redirect_stdout(out),
            ):
                self.assertEqual(wb.main(), 0)
            receipt = json.loads(
                st.receipt_path(contract, f"{SESSION}{wb.WRITEBACK_RECEIPT_SUFFIX}").read_text(
                    encoding="utf-8"
                )
            )
        return out.getvalue(), receipt

    def test_a_durable_write_is_announced_and_kept_in_the_receipt(self) -> None:
        stdout, receipt = self._run(prefetched=True, report=_written_report())
        message = json.loads(stdout)["systemMessage"]
        self.assertIn("L9 MEMORY WRITE-BACK — WRITTEN", message)
        self.assertEqual(receipt["announcement"], message)

    def test_an_idempotent_skip_prints_nothing(self) -> None:
        stdout, _ = self._run(prefetched=True)
        self.assertEqual(stdout, "")

    def test_a_missing_prefetch_is_announced_once_not_every_turn(self) -> None:
        first, _ = self._run(prefetched=False)
        self.assertIn("NOT WRITTEN", json.loads(first)["systemMessage"])
        second, receipt = self._run(prefetched=False)
        self.assertEqual(second, "", "an unchanged failure is not re-announced every turn")
        self.assertIn("NOT WRITTEN", receipt["announcement"], "the receipt keeps it")


if __name__ == "__main__":
    unittest.main()

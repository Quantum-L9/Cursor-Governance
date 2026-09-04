"""ReceiptChain: one chain per runtime root, safe across processes."""

from __future__ import annotations

import multiprocessing
import tempfile
import unittest

from peer_execution.models import LifecycleReceipt
from peer_execution.receipts import ReceiptChain, ReceiptChainError

_PROGRAM_DIGEST = "sha256:" + "a" * 64


def _receipt(previous: str | None, phase: str = "probe") -> LifecycleReceipt:
    return LifecycleReceipt.create(
        adapter_id="adapter-a",
        adapter_version="1.0.0",
        phase=phase,
        program_lock_digest=_PROGRAM_DIGEST,
        status="PASS",
        previous_receipt_digest=previous,
    )


def _append_many(root: str, count: int) -> None:
    chain = ReceiptChain(root)
    for _ in range(count):
        # Retry on a lost race: another process advanced the chain between
        # this process reading the tail and appending. The lock makes the
        # read+append atomic, so a mismatch can only come from a stale
        # receipt built before the lock -- rebuild it and try again.
        while True:
            try:
                chain.append(_receipt(chain.last_digest()))
                break
            except ValueError as exc:
                if "previous digest mismatch" not in str(exc):
                    raise


class ReceiptChainTests(unittest.TestCase):
    def test_concurrent_processes_extend_one_valid_chain(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workers = [
                multiprocessing.Process(target=_append_many, args=(raw, 25)) for _ in range(4)
            ]
            for worker in workers:
                worker.start()
            for worker in workers:
                worker.join(timeout=120)
                self.assertEqual(worker.exitcode, 0)
            chain = ReceiptChain(raw)
            self.assertEqual(chain.verify(), [])
            lines = chain.path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 100)

    def test_partial_tail_is_refused_not_parsed_around(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            chain = ReceiptChain(raw)
            chain.append(_receipt(None))
            with chain.path.open("a", encoding="utf-8") as handle:
                handle.write('{"receipt_digest": "sha256:' + "c" * 40)  # no newline
            with self.assertRaises(ReceiptChainError) as ctx:
                chain.last_digest()
            self.assertIn("partial line", str(ctx.exception))
            with self.assertRaises(ReceiptChainError):
                chain.append(_receipt("sha256:" + "0" * 64))
            errors = chain.verify()
            self.assertTrue(any("partial line" in error for error in errors), errors)

    def test_unparseable_line_is_named_by_verify(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            chain = ReceiptChain(raw)
            chain.append(_receipt(None))
            with chain.path.open("a", encoding="utf-8") as handle:
                handle.write("not json\n")
            errors = chain.verify()
            self.assertTrue(any(error.startswith("line 2: not JSON") for error in errors), errors)

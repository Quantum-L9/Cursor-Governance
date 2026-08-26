"""T-004 (generic runner) regressions: a cancel request is not terminal
cancellation, termination must be confirmed by an observed terminal status,
and an unacknowledged cancellation is reported `unconfirmed` (retry-blocking),
never converted to optimistic success."""

from __future__ import annotations

import unittest

from peer_execution.runner import run_to_terminal


class _Receipt:
    def __init__(self, status: str) -> None:
        self.status = status

    def to_dict(self) -> dict[str, str]:
        return {"status": self.status}


class _Adapter:
    def __init__(
        self,
        *,
        cancel_status: str,
        status_after_cancel: str = "RUNNING",
        cancellation_seconds: int = 1,
    ) -> None:
        self.execution_profile = {
            "timeout_budget": {
                "dispatch_seconds": 1,
                "poll_seconds": 1,
                "cancellation_seconds": cancellation_seconds,
            }
        }
        self._cancel_status = cancel_status
        self._status_after_cancel = status_after_cancel
        self.cancelled = False
        self.status_calls = 0

    def status(self, dispatch_id: str) -> _Receipt:
        del dispatch_id
        self.status_calls += 1
        if self.cancelled:
            return _Receipt(self._status_after_cancel)
        return _Receipt("RUNNING")

    def cancel(self, dispatch_id: str) -> _Receipt:
        del dispatch_id
        self.cancelled = True
        return _Receipt(self._cancel_status)


class RunnerCancellationTests(unittest.TestCase):
    def test_unacknowledged_cancellation_is_unconfirmed(self) -> None:
        adapter = _Adapter(cancel_status="RUNNING", status_after_cancel="RUNNING")
        outcome = run_to_terminal(adapter, "dispatch-1", "RUNNING")
        self.assertEqual(outcome.status, "FAIL")
        self.assertTrue(outcome.timed_out)
        self.assertEqual(outcome.termination, "unconfirmed")
        self.assertEqual(outcome.to_dict()["termination"], "unconfirmed")

    def test_host_acknowledged_cancellation_is_confirmed(self) -> None:
        adapter = _Adapter(cancel_status="RUNNING", status_after_cancel="CANCELLED")
        outcome = run_to_terminal(adapter, "dispatch-1", "RUNNING")
        self.assertEqual(outcome.status, "FAIL")
        self.assertTrue(outcome.timed_out)
        self.assertEqual(outcome.termination, "confirmed")
        self.assertIn({"status": "CANCELLED"}, list(outcome.status_receipts))

    def test_synchronous_provider_termination_is_confirmed(self) -> None:
        adapter = _Adapter(cancel_status="CANCELLED")
        outcome = run_to_terminal(adapter, "dispatch-1", "RUNNING")
        self.assertEqual(outcome.termination, "confirmed")
        self.assertEqual(outcome.cancel_receipt, {"status": "CANCELLED"})

    def test_unsupported_cancellation_stays_truthful(self) -> None:
        adapter = _Adapter(cancel_status="UNSUPPORTED")
        outcome = run_to_terminal(adapter, "dispatch-1", "RUNNING")
        self.assertEqual(outcome.termination, "unsupported")
        self.assertTrue(outcome.timed_out)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

_TERMINAL = {"PASS", "FAIL", "BLOCKED", "CANCELLED", "UNSUPPORTED"}


@dataclass(frozen=True)
class ProviderRunOutcome:
    status: str
    status_receipts: tuple[dict[str, Any], ...]
    cancel_receipt: dict[str, Any] | None = None
    timed_out: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "status_receipts": [dict(item) for item in self.status_receipts],
            "cancel_receipt": (
                dict(self.cancel_receipt) if self.cancel_receipt is not None else None
            ),
            "timed_out": self.timed_out,
        }


def run_to_terminal(
    adapter: Any,
    dispatch_id: str,
    initial_status: str,
) -> ProviderRunOutcome:
    """Apply the canonical timeout/poll policy to one already-dispatched attempt."""

    timeout_budget = adapter.execution_profile.get("timeout_budget") or {}
    dispatch_seconds = int(timeout_budget.get("dispatch_seconds") or 1800)
    poll_seconds = int(timeout_budget.get("poll_seconds") or 30)
    if dispatch_seconds <= 0 or poll_seconds <= 0:
        raise ValueError("execution profile timeout values must be positive")

    receipts: list[dict[str, Any]] = []
    status = str(initial_status)
    deadline = time.monotonic() + dispatch_seconds
    while status not in _TERMINAL:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            cancel = adapter.cancel(dispatch_id)
            cancel_value = cancel.to_dict()
            return ProviderRunOutcome(
                status="FAIL",
                status_receipts=tuple(receipts),
                cancel_receipt=cancel_value,
                timed_out=True,
            )
        time.sleep(min(poll_seconds, remaining))
        receipt = adapter.status(dispatch_id)
        value = receipt.to_dict()
        receipts.append(value)
        status = str(receipt.status)

    return ProviderRunOutcome(
        status=status,
        status_receipts=tuple(receipts),
    )

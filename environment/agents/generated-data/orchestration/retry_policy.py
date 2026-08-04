"""Deterministic retry classification and backoff decisions.

The delivery worker classifies a failure, then asks the policy whether to retry
and, if so, when. Permanent rejections never retry; transient/timeout failures
retry with exponential backoff up to a bounded attempt ceiling.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any


class RetryClass(StrEnum):
    TRANSIENT = "transient"
    TIMEOUT = "timeout"
    PERMANENT_REJECTION = "permanent_rejection"
    UNKNOWN = "unknown"


RETRYABLE_CLASSES: frozenset[RetryClass] = frozenset(
    {RetryClass.TRANSIENT, RetryClass.TIMEOUT, RetryClass.UNKNOWN}
)


@dataclass(frozen=True)
class RetryDecision:
    retry: bool
    failure_class: str
    attempt_number: int
    max_attempts: int
    next_attempt_at: str | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "retry": self.retry,
            "failure_class": self.failure_class,
            "attempt_number": self.attempt_number,
            "max_attempts": self.max_attempts,
            "next_attempt_at": self.next_attempt_at,
            "reason": self.reason,
        }


class RetryPolicy:
    """Bounded exponential-backoff retry policy."""

    def __init__(
        self,
        *,
        max_attempts: int = 5,
        base_delay_seconds: float = 2.0,
        max_delay_seconds: float = 3600.0,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        self.max_attempts = max_attempts
        self.base_delay_seconds = base_delay_seconds
        self.max_delay_seconds = max_delay_seconds

    def classify_exception(self, exc: BaseException) -> RetryClass:
        if isinstance(exc, subprocess.TimeoutExpired) or isinstance(exc, TimeoutError):
            return RetryClass.TIMEOUT
        if isinstance(exc, (ValueError, KeyError)):
            # Malformed local data will not fix itself on retry.
            return RetryClass.PERMANENT_REJECTION
        return RetryClass.TRANSIENT

    def decide(
        self,
        *,
        job_id: str,
        attempt_number: int,
        failure_class: RetryClass,
    ) -> RetryDecision:
        if failure_class not in RETRYABLE_CLASSES:
            return RetryDecision(
                retry=False,
                failure_class=failure_class.value,
                attempt_number=attempt_number,
                max_attempts=self.max_attempts,
                next_attempt_at=None,
                reason="failure_class_is_not_retryable",
            )
        if attempt_number >= self.max_attempts:
            return RetryDecision(
                retry=False,
                failure_class=failure_class.value,
                attempt_number=attempt_number,
                max_attempts=self.max_attempts,
                next_attempt_at=None,
                reason="max_attempts_exhausted",
            )
        delay = min(
            self.max_delay_seconds,
            self.base_delay_seconds * (2 ** max(0, attempt_number - 1)),
        )
        next_at = datetime.now(UTC) + timedelta(seconds=delay)
        return RetryDecision(
            retry=True,
            failure_class=failure_class.value,
            attempt_number=attempt_number,
            max_attempts=self.max_attempts,
            next_attempt_at=next_at.isoformat().replace("+00:00", "Z"),
            reason="scheduled_backoff",
        )

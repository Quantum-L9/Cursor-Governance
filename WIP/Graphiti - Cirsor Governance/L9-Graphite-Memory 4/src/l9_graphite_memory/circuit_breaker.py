"""Circuit breaker for Graphiti MCP calls — extracted from graphiti 2/memory_tool.py."""

from __future__ import annotations

import logging
import os
import time
from typing import Optional

log = logging.getLogger("graphiti.circuit")

CB_FAILURE_THRESHOLD = int(os.environ.get("MEMORY_CB_FAILURES", "5"))
CB_RECOVERY_SECS = int(os.environ.get("MEMORY_CB_RECOVERY", "60"))


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = CB_FAILURE_THRESHOLD,
        recovery_timeout: float = CB_RECOVERY_SECS,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"

    def record_success(self) -> None:
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            log.warning("Circuit breaker OPEN after %d failures", self.failure_count)

    def can_execute(self) -> bool:
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if self.last_failure_time and (time.time() - self.last_failure_time) > self.recovery_timeout:
                self.state = "HALF_OPEN"
                log.info("Circuit breaker HALF_OPEN — testing recovery")
                return True
            return False
        return True

    def status(self) -> dict:
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "last_failure": self.last_failure_time,
        }

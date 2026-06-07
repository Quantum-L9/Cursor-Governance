"""Rate limiter for Graphiti writes — extracted from graphiti 2/memory_tool.py."""

from __future__ import annotations

import logging
import os
import time
from collections import deque

log = logging.getLogger("graphiti.rate_limit")

RATE_LIMIT_PER_MIN = int(os.environ.get("MEMORY_RATE_LIMIT_MIN", "10"))
RATE_LIMIT_PER_HR = int(os.environ.get("MEMORY_RATE_LIMIT_HR", "200"))


class RateLimiter:
    def __init__(self, per_min: int = RATE_LIMIT_PER_MIN, per_hr: int = RATE_LIMIT_PER_HR) -> None:
        self.per_min = per_min
        self.per_hr = per_hr
        self._minute_window: deque[float] = deque()
        self._hour_window: deque[float] = deque()

    def allow(self) -> bool:
        now = time.time()
        while self._minute_window and (now - self._minute_window[0]) > 60:
            self._minute_window.popleft()
        while self._hour_window and (now - self._hour_window[0]) > 3600:
            self._hour_window.popleft()
        if len(self._minute_window) >= self.per_min:
            log.warning("Rate limit: %d writes/min", self.per_min)
            return False
        if len(self._hour_window) >= self.per_hr:
            log.warning("Rate limit: %d writes/hr", self.per_hr)
            return False
        return True

    def record(self) -> None:
        now = time.time()
        self._minute_window.append(now)
        self._hour_window.append(now)

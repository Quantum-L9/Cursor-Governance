from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from .models import CapabilityReceipt, LifecycleReceipt, ProbeContext


class ExecutionAdapter(Protocol):
    def probe(self, context: ProbeContext) -> CapabilityReceipt:
        pass

    def prepare(self, contract: Mapping[str, Any]) -> LifecycleReceipt:
        pass

    def dispatch(self, prepared: Mapping[str, Any]) -> LifecycleReceipt:
        pass

    def status(self, dispatch_id: str) -> LifecycleReceipt:
        pass

    def collect(self, dispatch_id: str) -> Mapping[str, Any]:
        pass

    def cancel(self, dispatch_id: str) -> LifecycleReceipt:
        pass

    def cleanup(self, dispatch_id: str) -> LifecycleReceipt:
        pass

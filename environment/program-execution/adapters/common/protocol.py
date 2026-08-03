from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from .models import CapabilityReceipt, LifecycleReceipt, ProbeContext


class ExecutionAdapter(Protocol):
    def probe(self, context: ProbeContext) -> CapabilityReceipt:
        # Empty: typing.Protocol structural hook — no runtime body.
        pass

    def prepare(self, contract: Mapping[str, Any]) -> LifecycleReceipt:
        # Empty: typing.Protocol structural hook — no runtime body.
        pass

    def dispatch(self, prepared: Mapping[str, Any]) -> LifecycleReceipt:
        # Empty: typing.Protocol structural hook — no runtime body.
        pass

    def status(self, dispatch_id: str) -> LifecycleReceipt:
        # Empty: typing.Protocol structural hook — no runtime body.
        pass

    def collect(self, dispatch_id: str) -> Mapping[str, Any]:
        # Empty: typing.Protocol structural hook — no runtime body.
        pass

    def cancel(self, dispatch_id: str) -> LifecycleReceipt:
        # Empty: typing.Protocol structural hook — no runtime body.
        pass

    def cleanup(self, dispatch_id: str) -> LifecycleReceipt:
        # Empty: typing.Protocol structural hook — no runtime body.
        pass

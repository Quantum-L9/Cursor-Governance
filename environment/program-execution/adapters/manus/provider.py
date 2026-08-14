from __future__ import annotations

import os
from pathlib import Path

from peer_execution.provider import ProviderInvocation, ProviderProbe


class ManusCloudProvider:
    provider_id = "manus-cloud"

    def __init__(self, runtime_root: str | Path, repository_root: str | Path) -> None:
        self.repository_root = Path(repository_root).resolve()

    def probe(self, context) -> ProviderProbe:
        enabled = os.environ.get("L9_MANUS_MANUAL_HANDOFF") == "1"
        identity = context.metadata.get("producer_identity")
        return ProviderProbe(
            status="BLOCKED",
            blocked_reason="Manus execution transport is not implemented",
            evidence=(
                {
                    "type": "manual_handoff",
                    "enabled": enabled,
                    "identity_bound": bool(identity),
                    "transport_implemented": False,
                },
            ),
            observed_capabilities=(),
        )

    def invoke(self, request) -> ProviderInvocation:
        return ProviderInvocation(
            status="BLOCKED",
            evidence=({"type": "transport_missing", "provider_ref": self.provider_id},),
        )

    def poll(self, request, state) -> ProviderInvocation:
        return ProviderInvocation(status="BLOCKED", state=state)

    def cancel(self, request, state) -> ProviderInvocation:
        return ProviderInvocation(status="UNSUPPORTED", state=state)


PROVIDER_CLASS = ManusCloudProvider

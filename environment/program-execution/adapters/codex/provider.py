from __future__ import annotations

import shutil
from pathlib import Path

from peer_execution.provider import ProviderInvocation, ProviderProbe


class CodexCloudProvider:
    provider_id = "codex-cloud"

    def __init__(self, runtime_root: str | Path, repository_root: str | Path) -> None:
        self.repository_root = Path(repository_root).resolve()

    def probe(self, context) -> ProviderProbe:
        executable = shutil.which("codex")
        return ProviderProbe(
            status="BLOCKED",
            blocked_reason="Codex execution transport is not implemented",
            evidence=(
                {"type": "executable", "path": executable},
                {"type": "transport_implemented", "value": False},
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


PROVIDER_CLASS = CodexCloudProvider

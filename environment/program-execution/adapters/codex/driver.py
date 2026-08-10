from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from adapters.common.base import BaseExecutionAdapter


class CodexCloudAdapter(BaseExecutionAdapter):
    """Codex implementer worker host.

    Honest coverage adapter for the ``codex`` agent identity (role
    ``implementer``). The Controller resolves work to this adapter, but no
    automated Codex execution transport ships inside this repository, so the
    probe reports BLOCKED until a ``codex`` executable (or an equivalent
    transport) is provisioned. It never widens Controller authority and never
    writes memory directly.
    """

    adapter_id = "codex-cloud"
    adapter_version = "1.0.0"
    capabilities = ("inspect", "local_write", "artifact_production")
    cancellation = "unsupported"

    def __init__(self, runtime_root: str | Path, repository_root: str | Path) -> None:
        super().__init__(runtime_root)
        self.repository_root = Path(repository_root).resolve()

    def _probe_status(self, context):
        executable = shutil.which("codex")
        missing = []
        if executable is None:
            missing.append("codex")
        evidence = [
            {"type": "executable", "path": executable},
            {"type": "missing", "items": missing},
        ]
        reason = None
        if missing:
            reason = "Codex executable or execution transport is unavailable"
        return ("PASS" if not missing else "BLOCKED", reason, evidence)

    def _dispatch_record(self, record: dict[str, Any]):
        # Dormant coverage adapter: no live transport is wired, so dispatch is
        # never a silent success. A fresh probe is still required before this
        # runs, so reaching here means a transport was provisioned but a driver
        # bridge has not yet been implemented.
        return "BLOCKED", [{"type": "transport_missing", "adapter_id": self.adapter_id}]

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from adapters.common.base import BaseExecutionAdapter


class GeminiReviewAdapter(BaseExecutionAdapter):
    """Gemini independent verifier.

    Honest coverage adapter for the ``gemini`` agent identity (role
    ``reviewer``). A reviewer performs independent verification, so this is a
    ``verifier`` adapter — it can never mutate a worker's worktree and never
    self-verifies its own work. No automated Gemini transport ships in this
    repository, so the probe reports BLOCKED until one is provisioned.
    """

    adapter_id = "gemini-review"
    adapter_version = "1.0.0"
    capabilities = ("verify",)
    cancellation = "unsupported"

    def __init__(self, runtime_root: str | Path, repository_root: str | Path) -> None:
        super().__init__(runtime_root)
        self.repository_root = Path(repository_root).resolve()

    def _probe_status(self, context):
        executable = shutil.which("gemini")
        missing = []
        if executable is None:
            missing.append("gemini")
        evidence = [
            {"type": "executable", "path": executable},
            {"type": "missing", "items": missing},
        ]
        reason = None
        if missing:
            reason = "Gemini executable or verification transport is unavailable"
        return ("PASS" if not missing else "BLOCKED", reason, evidence)

    def _dispatch_record(self, record: dict[str, Any]):
        return "BLOCKED", [{"type": "transport_missing", "adapter_id": self.adapter_id}]

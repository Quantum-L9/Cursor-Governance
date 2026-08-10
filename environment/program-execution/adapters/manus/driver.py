from __future__ import annotations

import os
from typing import Any

from adapters.common.base import BaseExecutionAdapter


class ManusCloudAdapter(BaseExecutionAdapter):
    """Manus research-builder worker host (manual handoff).

    Honest coverage adapter for the ``manus`` agent identity (role
    ``researcher-builder``). Manus is a cloud surface with no automated
    Controller execution transport, so — like the ChatGPT manual-handoff
    adapter — it is a manual-handoff worker host: it is enabled only when an
    explicit transport flag and an external producer identity are present.
    Absent those, the probe reports BLOCKED. Authority is research plus
    explicitly permitted artifact production; it never widens Controller
    authority and never writes memory directly.
    """

    adapter_id = "manus-cloud"
    adapter_version = "1.0.0"
    capabilities = ("inspect", "artifact_production")
    cancellation = "unsupported"

    def _probe_status(self, context):
        enabled = os.environ.get("L9_MANUS_MANUAL_HANDOFF") == "1"
        identity = context.metadata.get("producer_identity")
        passed = enabled and isinstance(identity, str) and bool(identity)
        reason = None
        if not passed:
            reason = "Manus handoff requires L9_MANUS_MANUAL_HANDOFF=1 and an external identity"
        evidence = [
            {
                "type": "manual_handoff",
                "enabled": enabled,
                "identity_bound": bool(identity),
            }
        ]
        return ("PASS" if passed else "BLOCKED", reason, evidence)

    def _dispatch_record(self, record: dict[str, Any]):
        return "BLOCKED", [{"type": "transport_missing", "adapter_id": self.adapter_id}]

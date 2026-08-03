from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from adapters.common.base import BaseExecutionAdapter
from adapters.common.imports import load_module


class ChatGPTManualHandoffAdapter(BaseExecutionAdapter):
    adapter_id = "chatgpt-manual-handoff"
    capabilities = ("inspect", "artifact_production")
    cancellation = "unsupported"

    def _probe_status(self, context):
        enabled = os.environ.get("L9_CHATGPT_MANUAL_HANDOFF") == "1"
        identity = context.metadata.get("producer_identity")
        passed = enabled and isinstance(identity, str) and bool(identity)
        reason = None
        if not passed:
            reason = "Manual handoff requires L9_CHATGPT_MANUAL_HANDOFF=1 and an external identity"
        return (
            "PASS" if passed else "BLOCKED",
            reason,
            [
                {
                    "type": "manual_handoff",
                    "enabled": enabled,
                    "identity_bound": bool(identity),
                }
            ],
        )

    def _dispatch_record(self, record: dict[str, Any]):
        contract = record["contract"]
        renderer = load_module(
            Path(__file__).with_name("envelope_renderer.py"),
            "pes_chatgpt_envelope_renderer",
        )
        envelope = renderer.render_envelope(
            contract,
            artifacts=list(contract.get("source_artifacts") or []),
            producer_identity=str(contract["external_producer_identity"]),
        )
        root = Path(self.runtime.root) / "chatgpt-handoffs"
        root.mkdir(parents=True, exist_ok=True)
        path = root / f"{record['dispatch_id']}.envelope.json"
        path.write_text(
            json.dumps(envelope, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        record["host_envelope"] = envelope
        return "RUNNING", [{"type": "manual_handoff_envelope", "path": str(path)}]

    def status(self, dispatch_id: str):
        record = self.runtime.load(dispatch_id)
        returned = Path(self.runtime.root) / "chatgpt-handoffs" / f"{dispatch_id}.result.json"
        if returned.is_file():
            collector = load_module(
                Path(__file__).with_name("artifact_collector.py"),
                "pes_chatgpt_artifact_collector",
            )
            value = collector.collect_returned_artifact(
                returned,
                record["host_envelope"],
            )
            mapper = load_module(
                Path(__file__).with_name("receipt_mapper.py"),
                "pes_chatgpt_receipt_mapper",
            )
            record["result"] = mapper.map_artifact(record["contract"], value)
            record["status"] = "PASS"
            self.runtime.save(dispatch_id, record)
        return super().status(dispatch_id)

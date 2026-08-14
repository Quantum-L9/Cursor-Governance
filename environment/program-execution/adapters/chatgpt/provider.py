from __future__ import annotations

import json
import os
from pathlib import Path

from peer_execution.imports import load_module
from peer_execution.provider import (
    CanonicalProviderResult,
    ProviderInvocation,
    ProviderProbe,
)


class ChatGPTManualHandoffProvider:
    provider_id = "chatgpt-manual-handoff"

    def __init__(self, runtime_root: str | Path, repository_root: str | Path) -> None:
        self.runtime_root = Path(runtime_root).resolve()

    def probe(self, context) -> ProviderProbe:
        enabled = os.environ.get("L9_CHATGPT_MANUAL_HANDOFF") == "1"
        identity = context.metadata.get("producer_identity")
        passed = enabled and isinstance(identity, str) and bool(identity)
        return ProviderProbe(
            status="PASS" if passed else "BLOCKED",
            blocked_reason=(
                None
                if passed
                else "Manual handoff requires transport enablement and producer identity"
            ),
            evidence=(
                {
                    "type": "manual_handoff",
                    "enabled": enabled,
                    "identity_bound": bool(identity),
                },
            ),
            observed_capabilities=("inspect", "artifact_production"),
        )

    def invoke(self, request) -> ProviderInvocation:
        contract = dict(request.rendered_contract)
        renderer = load_module(
            Path(__file__).with_name("envelope_renderer.py"),
            "pes_chatgpt_envelope_renderer",
        )
        identity = contract.get("external_producer_identity")
        if not isinstance(identity, str) or not identity:
            return ProviderInvocation(
                status="BLOCKED",
                evidence=({"type": "external_producer_identity_missing"},),
            )
        envelope = renderer.render_envelope(
            contract,
            artifacts=list(contract.get("source_artifacts") or []),
            producer_identity=identity,
        )
        root = self.runtime_root / "chatgpt-handoffs"
        root.mkdir(parents=True, exist_ok=True)
        path = root / f"{request.execution_id}.envelope.json"
        path.write_text(
            json.dumps(envelope, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return ProviderInvocation(
            status="RUNNING",
            state={"envelope": envelope, "handoff_path": str(path)},
            evidence=({"type": "manual_handoff_envelope", "path": str(path)},),
        )

    def poll(self, request, state) -> ProviderInvocation:
        returned = self.runtime_root / "chatgpt-handoffs" / (f"{request.execution_id}.result.json")
        if not returned.is_file():
            return ProviderInvocation(status="RUNNING", state=state)
        collector = load_module(
            Path(__file__).with_name("artifact_collector.py"),
            "pes_chatgpt_artifact_collector",
        )
        value = collector.collect_returned_artifact(returned, state["envelope"])
        result = CanonicalProviderResult(
            execution_id=request.execution_id,
            status="PASS",
            structured_payload=dict(value),
            provider_metadata={"provider_surface": "chatgpt-manual-handoff"},
            session_or_run_id=request.execution_id,
            observed_capabilities=("inspect", "artifact_production"),
        )
        return ProviderInvocation(status="PASS", state=state, result=result)

    def cancel(self, request, state) -> ProviderInvocation:
        return ProviderInvocation(status="UNSUPPORTED", state=state)


PROVIDER_CLASS = ChatGPTManualHandoffProvider

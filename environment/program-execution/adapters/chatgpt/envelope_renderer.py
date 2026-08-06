from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from adapters.common.digests import digest_object


def render_envelope(
    contract: Mapping[str, Any],
    *,
    artifacts: list[dict[str, Any]],
    producer_identity: str,
) -> dict[str, Any]:
    body = {
        "schema": "program-execution-adapter.host-envelope.v1",
        "adapter_id": "chatgpt-manual-handoff",
        "program_lock_digest": contract.get("program_lock_digest")
        or contract.get("program_digest"),
        "contract_digest": contract.get("contract_digest")
        or contract.get("rendered_contract_digest"),
        "task_id": contract.get("task_id") or contract.get("id"),
        "producer_identity": producer_identity,
        "artifacts": artifacts,
    }
    body["envelope_digest"] = digest_object(body)
    return body

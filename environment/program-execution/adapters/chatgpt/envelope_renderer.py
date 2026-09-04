from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from adapters.common.digests import digest_object


def _required(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"handoff envelope requires {name}")
    return value


def render_envelope(
    contract: Mapping[str, Any],
    *,
    artifacts: list[dict[str, Any]],
    producer_identity: str,
    task_id: str | None = None,
    program_lock_digest: str | None = None,
    contract_digest: str | None = None,
) -> dict[str, Any]:
    # Every identity field is required: the returned artifact is matched on
    # them, and an envelope rendered with None fields matched an artifact that
    # also had none.
    body = {
        "schema": "program-execution-adapter.host-envelope.v1",
        "adapter_id": "chatgpt-manual-handoff",
        "program_lock_digest": _required(
            "program_lock_digest",
            program_lock_digest
            or contract.get("program_lock_digest")
            or contract.get("program_digest"),
        ),
        "contract_digest": _required(
            "contract_digest",
            contract_digest
            or contract.get("contract_digest")
            or contract.get("rendered_contract_digest"),
        ),
        "task_id": _required("task_id", task_id or contract.get("task_id") or contract.get("id")),
        "producer_identity": _required("producer_identity", producer_identity),
        "artifacts": artifacts,
    }
    body["envelope_digest"] = digest_object(body)
    return body

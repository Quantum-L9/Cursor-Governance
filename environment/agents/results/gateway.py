from __future__ import annotations

import hashlib
import json
from typing import Any

from environment.agents.results import receipts as result_receipts
from environment.agents.results.adapters import cursor_subagent


def accept(
    *,
    return_receipt: dict[str, Any] | None,
    surface_result: dict[str, Any],
    adapter: str = "cursor_subagent",
) -> dict[str, Any]:
    if not return_receipt or return_receipt.get("status") not in {"RETURNED", None}:
        # allow explicit return receipt status RETURNED or presence
        if not return_receipt:
            return result_receipts.write_acceptance(
                {
                    "assignment_id": surface_result.get("assignment_id") or "unknown",
                    "agent_id": surface_result.get("agent_id") or "cursor",
                    "parent_agent_id": surface_result.get("parent_agent_id") or "cursor",
                    "surface": "cursor-ide",
                    "result_adapter": adapter,
                    "result_id": "reject-no-return",
                    "result_digest": "",
                    "status": "REJECTED",
                    "reason": "missing SubagentReturnReceipt",
                    "campaign_id": None,
                    "action_id": None,
                    "lease_id": None,
                    "base_sha": None,
                }
            )
    try:
        if adapter == "cursor_subagent":
            normalized = cursor_subagent.normalize(surface_result)
        else:
            raise ValueError(f"unknown adapter {adapter}")
    except Exception as exc:  # noqa: BLE001
        rid = hashlib.sha256(
            json.dumps(surface_result, sort_keys=True, default=str).encode()
        ).hexdigest()[:16]
        return result_receipts.write_acceptance(
            {
                "assignment_id": (return_receipt or {}).get("assignment_id") or "unknown",
                "agent_id": "cursor",
                "parent_agent_id": (return_receipt or {}).get("parent_agent_id") or "cursor",
                "surface": (return_receipt or {}).get("surface") or "cursor-ide",
                "result_adapter": adapter,
                "result_id": f"reject-{rid}",
                "result_digest": "",
                "status": "REJECTED",
                "reason": f"adapter validation failed: {exc}",
                "campaign_id": (return_receipt or {}).get("campaign_id"),
                "action_id": (return_receipt or {}).get("action_id"),
                "lease_id": (return_receipt or {}).get("lease_id"),
                "base_sha": (return_receipt or {}).get("base_sha"),
            }
        )

    assignment_id = (return_receipt or {}).get("assignment_id") or normalized.get("assignment_id")
    lease_id = (return_receipt or {}).get("lease_id")
    if lease_id and normalized.get("lease_id") and normalized.get("lease_id") != lease_id:
        status, reason = "REJECTED", "wrong lease"
    elif (
        (return_receipt or {}).get("base_sha")
        and normalized.get("base_sha")
        and normalized.get("base_sha") != (return_receipt or {}).get("base_sha")
    ):
        status, reason = "REJECTED", "wrong base_sha"
    else:
        status, reason = "ACCEPTED", "ok"

    result_digest = hashlib.sha256(
        json.dumps(normalized, sort_keys=True, default=str).encode()
    ).hexdigest()
    result_id = normalized.get("result_id") or result_digest[:16]
    existing = result_receipts.load_acceptance(result_id)
    if existing:
        return existing
    return result_receipts.write_acceptance(
        {
            "assignment_id": assignment_id,
            "campaign_id": (return_receipt or {}).get("campaign_id"),
            "action_id": (return_receipt or {}).get("action_id"),
            "agent_id": normalized.get("agent_id") or "cursor",
            "parent_agent_id": (return_receipt or {}).get("parent_agent_id") or "cursor",
            "lease_id": lease_id,
            "base_sha": (return_receipt or {}).get("base_sha"),
            "surface": (return_receipt or {}).get("surface") or "cursor-ide",
            "result_adapter": adapter,
            "result_id": result_id,
            "result_digest": result_digest,
            "status": status,
            "reason": reason,
        }
    )

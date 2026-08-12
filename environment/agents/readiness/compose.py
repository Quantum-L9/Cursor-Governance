from __future__ import annotations

from typing import Any


def execution_ready(dimensions: dict[str, bool]) -> dict[str, Any]:
    """Cursor EXECUTION_READY = all required dimensions true."""
    required = [
        "IDENTITY_READY",
        "PROGRAM_EXECUTION_READY",
        "AUTONOMY_READY",
        "DEPLOYMENT_READY",
        "RESULT_INGRESS_READY",
        "DATA_CAPTURE_READY",
    ]
    missing = [k for k in required if not dimensions.get(k)]
    status = "EXECUTION_READY" if not missing else "NOT_READY"
    delivery = dimensions.get("DATA_DELIVERY_READY")
    delivery_status = "DATA_DELIVERY_READY"
    if dimensions.get("DATA_DELIVERY_BLOCKED"):
        delivery_status = "DATA_DELIVERY_BLOCKED"
    elif dimensions.get("DATA_DELIVERY_DEGRADED_DURABLE_OUTBOX"):
        delivery_status = "DATA_DELIVERY_DEGRADED_DURABLE_OUTBOX"
    elif delivery is False:
        delivery_status = "DATA_DELIVERY_NOT_READY"
    return {
        "status": status,
        "missing": missing,
        "delivery": delivery_status,
        "dimensions": dimensions,
    }


def completion_evidence_ok(
    *,
    return_receipt: dict | None,
    acceptance_receipt: dict | None,
    ingress_receipt: dict | None,
) -> dict[str, Any]:
    """Controller completion evidence join (no new PE states)."""
    if not return_receipt:
        return {"allowed": False, "reason": "missing SubagentReturnReceipt"}
    if not acceptance_receipt or acceptance_receipt.get("status") != "ACCEPTED":
        return {"allowed": False, "reason": "missing ResultAcceptanceReceipt"}
    if not ingress_receipt or ingress_receipt.get("outcome") not in {
        "CAPTURED",
        "NO_REUSABLE_DATA",
        "QUARANTINED",
        "REJECTED",
    }:
        return {"allowed": False, "reason": "missing GeneratedDataIngressReceipt"}
    # NO_REUSABLE_DATA still allows execution completion
    return {"allowed": True, "reason": "evidence chain complete"}

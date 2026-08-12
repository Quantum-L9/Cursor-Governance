from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import receipts as ingress_receipts  # noqa: E402
import security_gate  # noqa: E402

# runtime_paths via repo root
_REPO = _HERE.parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def ingest_accepted_result(
    *,
    accepted_result: dict[str, Any],
    generated_data_packet: dict[str, Any] | None,
    acceptance_receipt: dict[str, Any],
) -> dict[str, Any]:
    if acceptance_receipt.get("status") != "ACCEPTED":
        return ingress_receipts.write_ingress(
            {
                "acceptance_receipt_digest": acceptance_receipt.get("receipt_digest") or "none",
                "outcome": "REJECTED",
                "reason": "result not accepted",
                "processor_job_id": None,
            }
        )
    acc_digest = acceptance_receipt["receipt_digest"]
    existing = ingress_receipts.load_ingress(acc_digest)
    if existing:
        return existing
    if not generated_data_packet:
        return ingress_receipts.write_ingress(
            {
                "acceptance_receipt_digest": acc_digest,
                "outcome": "NO_REUSABLE_DATA",
                "reason": "no generated-data packet",
                "processor_job_id": None,
            }
        )
    decision = security_gate.preflight(generated_data_packet)
    packet_digest = hashlib.sha256(
        json.dumps(generated_data_packet, sort_keys=True, default=str).encode()
    ).hexdigest()
    if not decision["safe"]:
        ingress_receipts.quarantine_meta(
            {
                "packet_digest": packet_digest,
                "classification": decision["classification"],
                "finding_types": decision["finding_types"],
                "acceptance_receipt_digest": acc_digest,
            }
        )
        return ingress_receipts.write_ingress(
            {
                "acceptance_receipt_digest": acc_digest,
                "outcome": "QUARANTINED",
                "reason": decision["classification"],
                "processor_job_id": None,
                "packet_digest": packet_digest,
            }
        )
    job_id = hashlib.sha256(f"{acc_digest}:{packet_digest}".encode()).hexdigest()[:24]
    return ingress_receipts.write_ingress(
        {
            "acceptance_receipt_digest": acc_digest,
            "outcome": "CAPTURED",
            "reason": "security preflight passed",
            "processor_job_id": job_id,
            "packet_digest": packet_digest,
        }
    )


def ingest(*args, **kwargs):
    return ingest_accepted_result(*args, **kwargs)

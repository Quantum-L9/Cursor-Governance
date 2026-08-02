from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ORCHESTRATION = ROOT / "subagent-generated-data" / "orchestration"
sys.path.insert(0, str(ORCHESTRATION))
from receipts import ProcessingReceiptChain
from state_store import PipelineStateStore


def status_payload(
    store: PipelineStateStore,
    *,
    campaign_id: str | None = None,
    job_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "pipeline": store.pipeline_status(),
    }
    with store.connect() as connection:
        payload["delivery"] = {
            row["status"]: int(row["count"])
            for row in connection.execute(
                """
                SELECT status, COUNT(*) AS count
                FROM delivery_attempts
                GROUP BY status
                """
            )
        }
        payload["retrieval"] = {
            "selections": int(
                connection.execute("SELECT COUNT(*) AS n FROM context_selections").fetchone()["n"]
            ),
            "reuse_events": int(
                connection.execute("SELECT COUNT(*) AS n FROM reuse_events").fetchone()["n"]
            ),
        }
        payload["invalidation"] = {
            "events": int(
                connection.execute("SELECT COUNT(*) AS n FROM invalidation_events").fetchone()["n"]
            ),
        }
    if campaign_id:
        payload["campaign"] = store.campaign_status(campaign_id).to_dict()
    if job_id:
        job = store.get_job(job_id)
        payload["job"] = job.to_dict()
        payload["events"] = [item.to_dict() for item in store.list_events(job_id)]
        chain_errors = ProcessingReceiptChain(store).verify_job_chain(job_id)
        payload["receipt_integrity"] = {
            "valid": not chain_errors,
            "errors": chain_errors,
        }
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Show generated-data pipeline status.")
    parser.add_argument("--database", required=True)
    parser.add_argument("--campaign-id")
    parser.add_argument("--job-id")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    payload = status_payload(
        PipelineStateStore(args.database),
        campaign_id=args.campaign_id,
        job_id=args.job_id,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

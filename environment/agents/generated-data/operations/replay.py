from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORCHESTRATION = ROOT / "generated-data" / "orchestration"
sys.path.insert(0, str(ORCHESTRATION))
from receipts import ProcessingReceiptChain
from state_store import (
    PipelineState,
    PipelineStateStore,
)

REPLAY_STATES = {
    "VALIDATED": PipelineState.VALIDATED,
    "HARVESTED": PipelineState.HARVESTED,
    "CLASSIFIED": PipelineState.CLASSIFIED,
    "ROUTED": PipelineState.ROUTED,
    "PROMOTION_DECIDED": PipelineState.PROMOTION_DECIDED,
    "DELIVERY_PENDING": PipelineState.DELIVERY_PENDING,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Perform controlled generated-data replay.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--database", required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument(
        "--from-stage",
        required=True,
        choices=sorted(REPLAY_STATES),
    )
    parser.add_argument("--actor", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument(
        "--force-stage",
        action="store_true",
    )
    args = parser.parse_args()
    store = PipelineStateStore(args.database)
    job = store.get_job(args.job_id)
    target = REPLAY_STATES[args.from_stage]
    if job.state is PipelineState.DEAD_LETTERED:
        raise SystemExit("Resolve the dead letter before replay")
    if not args.force_stage:
        raise SystemExit("Replay requires --force-stage and an explicit reason")
    replayed = store.transition(
        job_id=job.job_id,
        expected_state=job.state,
        target_state=target,
        actor=args.actor,
        payload={
            "reason": args.reason,
            "requested_stage": args.from_stage,
        },
        allow_replay=True,
    )
    ProcessingReceiptChain(store).append_receipt(
        job_id=job.job_id,
        stage=target.value,
        event_type="controlled_replay",
        actor=args.actor,
        payload={
            "reason": args.reason,
            "from_state": job.state.value,
            "to_state": target.value,
        },
        event_identity=(f"replay:{replayed.replay_generation}"),
    )
    print(
        json.dumps(
            replayed.to_dict(),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

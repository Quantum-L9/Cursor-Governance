#!/usr/bin/env python3
"""Operator CLI for campaign initialization, planning, status, and merge gates."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from autonomy.merge_coordinator import (  # type: ignore[import-not-found]
        MergeEvidence,
        evaluate_merge,
    )
    from autonomy.models import CampaignState, ConcurrencyBudget  # type: ignore[import-not-found]
    from autonomy.scheduler import plan_ready_set  # type: ignore[import-not-found]
    from autonomy.state_store import StateStore  # type: ignore[import-not-found]
else:
    from .merge_coordinator import MergeEvidence, evaluate_merge
    from .models import CampaignState, ConcurrencyBudget
    from .scheduler import plan_ready_set
    from .state_store import StateStore


def _root(value: str | None) -> Path:
    return Path(value or os.environ.get("L9_AUTONOMY_STATE_DIR", ".l9/autonomy")).expanduser()


def _plan_payload(state: CampaignState, total_lanes: int, mutation_lanes: int) -> dict[str, object]:
    plan = plan_ready_set(
        state,
        ConcurrencyBudget(total_lanes=total_lanes, mutation_lanes=mutation_lanes),
    )
    return {
        "campaign_id": state.campaign_id,
        "state_digest": state.state_digest,
        "ready": list(plan.ready),
        "selected": list(plan.selected),
        "deferred": plan.deferred,
        "available_total_lanes": plan.available_total_lanes,
        "available_mutation_lanes": plan.available_mutation_lanes,
    }


def command_init(args: argparse.Namespace) -> int:
    raw = json.loads(Path(args.campaign).read_text(encoding="utf-8"))
    state = CampaignState.from_dict(raw)
    path = StateStore(_root(args.state_root)).save(state)
    print(
        json.dumps(
            {
                "campaign_id": state.campaign_id,
                "path": str(path),
                "state_digest": state.state_digest,
            },
            sort_keys=True,
        )
    )
    return 0


def command_plan(args: argparse.Namespace) -> int:
    state = StateStore(_root(args.state_root)).load(args.campaign_id)
    print(
        json.dumps(
            _plan_payload(state, args.total_lanes, args.mutation_lanes), indent=2, sort_keys=True
        )
    )
    return 0


def command_status(args: argparse.Namespace) -> int:
    state = StateStore(_root(args.state_root)).load(args.campaign_id)
    status_counts: dict[str, int] = {}
    for runtime in state.action_runtime.values():
        status_counts[runtime.status.value] = status_counts.get(runtime.status.value, 0) + 1
    print(
        json.dumps(
            {
                "campaign_id": state.campaign_id,
                "objective": state.objective,
                "authority_profile": state.authority_profile,
                "state_digest": state.state_digest,
                "status_counts": status_counts,
                "completed_operations": sorted(state.completed_operations),
                "checkpoint_count": len(state.checkpoints),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def command_merge_gate(args: argparse.Namespace) -> int:
    raw = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    evidence = MergeEvidence(**raw)
    decision = evaluate_merge(evidence)
    print(
        json.dumps(
            {"eligible": decision.eligible, "reasons": list(decision.reasons)},
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if decision.eligible else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="l9-claude-autonomy")
    sub = parser.add_subparsers(dest="command", required=True)

    init_parser = sub.add_parser("init", help="Validate and persist a campaign definition")
    init_parser.add_argument("campaign")
    init_parser.add_argument("--state-root")
    init_parser.set_defaults(func=command_init)

    plan_parser = sub.add_parser("plan", help="Compute the next dependency-ready concurrent set")
    plan_parser.add_argument("campaign_id")
    plan_parser.add_argument("--state-root")
    plan_parser.add_argument(
        "--total-lanes", type=int, default=int(os.environ.get("L9_AUTONOMY_MAX_PARALLEL", "4"))
    )
    plan_parser.add_argument(
        "--mutation-lanes",
        type=int,
        default=int(os.environ.get("L9_AUTONOMY_MAX_MUTATION_LANES", "2")),
    )
    plan_parser.set_defaults(func=command_plan)

    status_parser = sub.add_parser("status", help="Show durable campaign state")
    status_parser.add_argument("campaign_id")
    status_parser.add_argument("--state-root")
    status_parser.set_defaults(func=command_status)

    merge_parser = sub.add_parser("merge-gate", help="Evaluate exact-SHA PR merge evidence")
    merge_parser.add_argument("evidence")
    merge_parser.set_defaults(func=command_merge_gate)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

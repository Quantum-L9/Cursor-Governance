#!/usr/bin/env python3
"""Compile compact resumable autonomy context for Claude Code SessionStart."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from autonomy.scheduler import plan_ready_set  # type: ignore[import-not-found]
    from autonomy.state_dir import expand_state_dir  # type: ignore[import-not-found]
    from autonomy.state_store import StateStore  # type: ignore[import-not-found]

    from autonomy.models import ConcurrencyBudget  # type: ignore[import-not-found]
else:
    from .models import ConcurrencyBudget
    from .scheduler import plan_ready_set
    from .state_dir import expand_state_dir
    from .state_store import StateStore


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _state_root(workspace: Path) -> Path:
    path = expand_state_dir(os.environ.get("L9_AUTONOMY_STATE_DIR"))
    return path if path.is_absolute() else workspace / path


def compile_context(workspace: Path) -> dict[str, Any]:
    enabled = _truthy(os.environ.get("L9_AUTONOMY_ENABLED", "true"))
    result: dict[str, Any] = {
        "enabled": enabled,
        "authority": os.environ.get("L9_AUTONOMY_AUTHORITY", "A4_CAMPAIGN_BOUNDED_EXTERNAL_WRITE"),
        "maturity": os.environ.get("L9_AUTONOMY_MATURITY", "M4_ASSURANCE_GOVERNED"),
        "profile": os.environ.get("L9_AUTONOMY_PROFILE", "pr-convergence"),
        "discover_before_ask": _truthy(os.environ.get("L9_DISCOVER_BEFORE_ASK", "true")),
        "exact_sha_gate": _truthy(os.environ.get("L9_REQUIRE_EXACT_SHA_GREEN", "true")),
        "workspace": str(workspace),
        "program_plane": {
            "authoritative": True,
            "note": (
                "Program Controller is authoritative; this autonomy context "
                "does not write campaign packets or Program Locks"
            ),
        },
    }
    if not enabled:
        result["status"] = "disabled"
        return result

    state_root = _state_root(workspace)
    result["state_root"] = str(state_root)
    store = StateStore(state_root)
    campaign_ids = store.list_campaigns()
    result["campaign_count"] = len(campaign_ids)
    if not campaign_ids:
        result["status"] = "no_active_campaign"
        return result

    campaign_id = max(
        campaign_ids,
        key=lambda item: store.path_for(item).stat().st_mtime,
    )
    state = store.load(campaign_id)
    total_lanes = int(os.environ.get("L9_AUTONOMY_MAX_PARALLEL", "4"))
    mutation_lanes = int(os.environ.get("L9_AUTONOMY_MAX_MUTATION_LANES", "2"))
    plan = plan_ready_set(
        state,
        ConcurrencyBudget(total_lanes=total_lanes, mutation_lanes=mutation_lanes),
    )
    statuses: dict[str, int] = {}
    for runtime in state.action_runtime.values():
        statuses[runtime.status.value] = statuses.get(runtime.status.value, 0) + 1
    result.update(
        {
            "status": "campaign_loaded",
            "campaign_id": state.campaign_id,
            "objective": state.objective,
            "state_digest": state.state_digest,
            "action_status_counts": statuses,
            "ready_actions": list(plan.ready),
            "next_action_set": list(plan.selected),
            "deferred_count": len(plan.deferred),
            "available_total_lanes": plan.available_total_lanes,
            "available_mutation_lanes": plan.available_mutation_lanes,
        }
    )
    return result


def render_text(context: dict[str, Any]) -> str:
    lines = [
        "L9 autonomy runtime:",
        f"  enabled: {str(context['enabled']).lower()}",
        f"  authority: {context['authority']}",
        f"  maturity: {context['maturity']}",
        f"  profile: {context['profile']}",
        f"  discover-before-ask: {str(context['discover_before_ask']).lower()}",
        f"  exact-SHA merge gate: {str(context['exact_sha_gate']).lower()}",
        f"  status: {context.get('status', 'unknown')}",
        "  program-plane: authoritative (read-only from autonomy)",
    ]
    if context.get("campaign_id"):
        lines.extend(
            [
                f"  campaign: {context['campaign_id']}",
                f"  objective: {context['objective']}",
                f"  state digest: {context['state_digest'][:16]}",
                f"  action states: {json.dumps(context['action_status_counts'], sort_keys=True)}",
                f"  dependency-ready: {', '.join(context['ready_actions']) or 'none'}",
                f"  next concurrent set: {', '.join(context['next_action_set']) or 'none'}",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        context = compile_context(Path(args.workspace).resolve())
        print(json.dumps(context, sort_keys=True) if args.json else render_text(context))
        return 0
    except Exception as exc:  # fail-open for SessionStart
        payload = {"enabled": True, "status": "degraded", "error": str(exc)}
        print(
            json.dumps(payload, sort_keys=True)
            if args.json
            else f"L9 autonomy runtime: degraded ({exc})"
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

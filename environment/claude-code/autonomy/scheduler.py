"""Conflict-aware ready-set scheduler for bounded concurrent execution."""

from __future__ import annotations

from .models import (
    LOCK_HOLDING,
    CampaignState,
    ConcurrencyBudget,
    ResourceLock,
    SchedulePlan,
)
from .readiness import action_readiness, validate_action_graph
from .resource_locks import first_conflict


def _held_locks(state: CampaignState) -> tuple[ResourceLock, ...]:
    locks: list[ResourceLock] = []
    for action_id, runtime in state.action_runtime.items():
        if runtime.status in LOCK_HOLDING:
            locks.extend(state.action_specs[action_id].resources)
    return tuple(locks)


def plan_ready_set(
    state: CampaignState,
    budget: ConcurrencyBudget,
) -> SchedulePlan:
    """Select the highest-value non-conflicting ready actions.

    The function is deterministic: equal scores are resolved by action_id.
    Running and externally-waiting actions consume their declared locks. Only
    active compute lanes consume the lane budget; waiting_external preserves
    locks but frees a compute lane.
    """

    validate_action_graph(state.action_specs)
    active_total = sum(
        runtime.status.value in {"claimed", "running", "validating"}
        for runtime in state.action_runtime.values()
    )
    active_mutations = sum(
        state.action_specs[action_id].mutation
        and runtime.status.value in {"claimed", "running", "validating"}
        for action_id, runtime in state.action_runtime.items()
    )
    available_total = max(0, budget.total_lanes - active_total)
    available_mutation = max(0, budget.mutation_lanes - active_mutations)

    candidates: list[str] = []
    deferred: dict[str, str] = {}
    for action_id in sorted(state.action_specs):
        decision = action_readiness(state, action_id)
        if decision.ready:
            candidates.append(action_id)
        elif state.action_runtime[action_id].status.value in {"pending", "ready", "retryable"}:
            deferred[action_id] = decision.reason

    candidates.sort(key=lambda action_id: (-state.action_specs[action_id].score(), action_id))
    selected: list[str] = []
    held = list(_held_locks(state))
    remaining_total = available_total
    remaining_mutation = available_mutation

    for action_id in candidates:
        spec = state.action_specs[action_id]
        if remaining_total <= 0:
            deferred[action_id] = "total_lane_budget_exhausted"
            continue
        if spec.mutation and remaining_mutation <= 0:
            deferred[action_id] = "mutation_lane_budget_exhausted"
            continue
        conflict = first_conflict(spec.resources, held)
        if conflict:
            deferred[action_id] = f"resource_conflict:{conflict.left_key}"
            continue
        selected.append(action_id)
        held.extend(spec.resources)
        remaining_total -= 1
        if spec.mutation:
            remaining_mutation -= 1

    return SchedulePlan(
        selected=tuple(selected),
        deferred=deferred,
        ready=tuple(candidates),
        available_total_lanes=available_total,
        available_mutation_lanes=available_mutation,
    )

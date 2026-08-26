"""Readiness and graph-integrity checks for action scheduling."""

from __future__ import annotations

from dataclasses import dataclass

from .models import TERMINAL_SUCCESS, ActionSpec, ActionStatus, CampaignState


@dataclass(frozen=True, slots=True)
class ReadinessDecision:
    ready: bool
    reason: str


def validate_action_graph(specs: dict[str, ActionSpec]) -> None:
    """Reject unknown dependencies and cycles before execution begins."""

    for action in specs.values():
        unknown = set(action.depends_on) - set(specs)
        if unknown:
            raise ValueError(
                f"action {action.action_id!r} has unknown dependencies: {sorted(unknown)}"
            )
        if action.action_id in action.depends_on:
            raise ValueError(f"action {action.action_id!r} depends on itself")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(action_id: str) -> None:
        if action_id in visited:
            return
        if action_id in visiting:
            raise ValueError(f"dependency cycle detected at {action_id!r}")
        visiting.add(action_id)
        for dependency in specs[action_id].depends_on:
            visit(dependency)
        visiting.remove(action_id)
        visited.add(action_id)

    for action_id in sorted(specs):
        visit(action_id)


def action_readiness(state: CampaignState, action_id: str) -> ReadinessDecision:
    spec = state.action_specs[action_id]
    runtime = state.action_runtime[action_id]

    if runtime.status not in {
        ActionStatus.PENDING,
        ActionStatus.READY,
        ActionStatus.RETRYABLE,
    }:
        return ReadinessDecision(False, f"status={runtime.status.value}")
    if not spec.preconditions_satisfied:
        return ReadinessDecision(False, "preconditions_not_satisfied")
    if spec.operation_id and spec.operation_id in state.completed_operations:
        return ReadinessDecision(False, "operation_already_completed")

    incomplete = [
        dependency
        for dependency in spec.depends_on
        if state.action_runtime[dependency].status not in TERMINAL_SUCCESS
    ]
    if incomplete:
        return ReadinessDecision(False, f"dependencies_incomplete={','.join(sorted(incomplete))}")
    return ReadinessDecision(True, "dependency_ready")


def ready_actions(state: CampaignState) -> tuple[str, ...]:
    validate_action_graph(state.action_specs)
    return tuple(
        action_id
        for action_id in sorted(state.action_specs)
        if action_readiness(state, action_id).ready
    )

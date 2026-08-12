"""Fan-in assurance barriers for concurrent action groups."""

from __future__ import annotations

from dataclasses import dataclass

from .models import TERMINAL_SUCCESS, CampaignState, JoinBarrier


@dataclass(frozen=True, slots=True)
class JoinDecision:
    satisfied: bool
    reason: str
    successful_members: tuple[str, ...]
    incomplete_members: tuple[str, ...]


def evaluate_join(
    state: CampaignState,
    barrier: JoinBarrier,
    *,
    conflict_check_passed: bool,
    integration_validation_passed: bool,
) -> JoinDecision:
    unknown = set(barrier.member_actions) - set(state.action_specs)
    if unknown:
        return JoinDecision(False, f"unknown_members={','.join(sorted(unknown))}", (), ())

    successful: list[str] = []
    incomplete: list[str] = []
    for action_id in barrier.member_actions:
        runtime = state.action_runtime[action_id]
        proof_ok = all(key in runtime.proof_bundle for key in barrier.required_proof_keys)
        if runtime.status in TERMINAL_SUCCESS and proof_ok:
            successful.append(action_id)
        else:
            incomplete.append(action_id)

    if barrier.policy == "all":
        policy_satisfied = len(successful) == len(barrier.member_actions)
    elif barrier.policy == "any":
        policy_satisfied = bool(successful)
    else:
        assert barrier.threshold is not None
        policy_satisfied = len(successful) >= barrier.threshold

    if not policy_satisfied:
        return JoinDecision(
            False,
            "member_policy_not_satisfied",
            tuple(successful),
            tuple(incomplete),
        )
    if not conflict_check_passed:
        return JoinDecision(
            False, "integration_conflict_check_failed", tuple(successful), tuple(incomplete)
        )
    if not integration_validation_passed:
        return JoinDecision(
            False, "integration_validation_failed", tuple(successful), tuple(incomplete)
        )
    return JoinDecision(True, "join_satisfied", tuple(successful), tuple(incomplete))

from __future__ import annotations

import unittest

from autonomy.scheduler import plan_ready_set

from autonomy.models import (
    ActionRuntime,
    ActionSpec,
    ActionStatus,
    CampaignState,
    ConcurrencyBudget,
    ResourceLock,
)


class SchedulerTests(unittest.TestCase):
    def make_state(self) -> CampaignState:
        specs = {
            "inspect-a": ActionSpec(
                action_id="inspect-a",
                objective="Inspect PR A",
                resources=(ResourceLock("service:github", "read"),),
                priority=2,
            ),
            "inspect-b": ActionSpec(
                action_id="inspect-b",
                objective="Inspect PR B",
                resources=(ResourceLock("service:github", "read"),),
                priority=1,
            ),
            "fix-a": ActionSpec(
                action_id="fix-a",
                objective="Fix PR A",
                depends_on=("inspect-a",),
                resources=(ResourceLock("repo:quantum/a", "write", "worktree:a"),),
                mutation=True,
                priority=10,
            ),
            "fix-b": ActionSpec(
                action_id="fix-b",
                objective="Fix PR B",
                depends_on=("inspect-b",),
                resources=(ResourceLock("repo:quantum/b", "write", "worktree:b"),),
                mutation=True,
                priority=9,
            ),
        }
        runtime = {action_id: ActionRuntime() for action_id in specs}
        return CampaignState("campaign", "Converge PRs", specs, runtime)

    def test_selects_independent_read_actions_concurrently(self) -> None:
        state = self.make_state()
        plan = plan_ready_set(state, ConcurrencyBudget(total_lanes=4, mutation_lanes=2))
        self.assertEqual(plan.selected, ("inspect-a", "inspect-b"))

    def test_dependencies_gate_mutation_actions(self) -> None:
        state = self.make_state()
        state.action_runtime["inspect-a"].status = ActionStatus.VALIDATED
        state.action_runtime["inspect-b"].status = ActionStatus.VALIDATED
        plan = plan_ready_set(state, ConcurrencyBudget(total_lanes=4, mutation_lanes=2))
        self.assertEqual(plan.selected, ("fix-a", "fix-b"))

    def test_mutation_budget_serializes_excess(self) -> None:
        state = self.make_state()
        state.action_runtime["inspect-a"].status = ActionStatus.VALIDATED
        state.action_runtime["inspect-b"].status = ActionStatus.VALIDATED
        plan = plan_ready_set(state, ConcurrencyBudget(total_lanes=4, mutation_lanes=1))
        self.assertEqual(plan.selected, ("fix-a",))
        self.assertEqual(plan.deferred["fix-b"], "mutation_lane_budget_exhausted")

    def test_waiting_external_preserves_lock_but_frees_compute_lane(self) -> None:
        state = self.make_state()
        state.action_runtime["inspect-a"].status = ActionStatus.VALIDATED
        state.action_runtime["inspect-b"].status = ActionStatus.VALIDATED
        state.action_runtime["fix-a"].status = ActionStatus.WAITING_EXTERNAL
        conflicting = ActionSpec(
            action_id="review-a",
            objective="Review same PR branch",
            resources=(ResourceLock("repo:quantum/a", "write", "worktree:a"),),
            mutation=True,
            priority=20,
        )
        state.action_specs["review-a"] = conflicting
        state.action_runtime["review-a"] = ActionRuntime()
        plan = plan_ready_set(state, ConcurrencyBudget(total_lanes=2, mutation_lanes=2))
        self.assertIn("fix-b", plan.selected)
        self.assertEqual(plan.deferred["review-a"], "resource_conflict:repo:quantum/a")


if __name__ == "__main__":
    unittest.main()

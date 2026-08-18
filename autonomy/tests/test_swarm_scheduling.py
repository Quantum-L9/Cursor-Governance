"""Saturation, claim-aware mutation, and bottleneck-attribution tests.

Contract under test: no independent READY action may remain idle while
compatible execution capacity exists; mutation concurrency is bounded by actual
claim conflict; and every non-admitted READY action is attributed to exactly one
blocking reason.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from autonomy.compiler.graph_compiler import compile_graph
from autonomy.models import CampaignAuthorization, DeploymentManifest
from autonomy.policy_loader import load_policy
from autonomy.runtime.engine import AutonomyRuntime
from autonomy.tests.swarm_fixtures import (
    CAMPAIGN_ID,
    actions_payload,
    campaign_payload,
    deployment_payload,
)

ROOT = Path(__file__).resolve().parents[2]
READY_STATUSES = ("LEASED",)


class SwarmSchedulingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.database = Path(self.tempdir.name) / "runtime.sqlite3"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def bootstrap(
        self,
        *,
        campaign: dict[str, Any] | None = None,
        deployment: dict[str, Any] | None = None,
        actions: dict[str, Any] | None = None,
    ) -> AutonomyRuntime:
        campaign_data = campaign if campaign is not None else campaign_payload()
        deployment_data = deployment if deployment is not None else deployment_payload()
        actions_data = actions if actions is not None else actions_payload(recon=1)
        compiled = compile_graph(
            CampaignAuthorization.from_dict(campaign_data),
            DeploymentManifest.from_dict(deployment_data),
            actions_data,
        )
        runtime = AutonomyRuntime.from_repository(
            repository_root=ROOT,
            database_path=self.database,
            signing_key="test-signing-key",
        )
        runtime.bootstrap(
            campaign_payload=campaign_data,
            deployment_payload=deployment_data,
            graph_payload=compiled.to_dict(),
        )
        return runtime

    @staticmethod
    def complete(runtime: AutonomyRuntime, action_id: str) -> None:
        runtime.store.set_action_status(
            campaign_id=CAMPAIGN_ID,
            action_id=action_id,
            status="COMPLETED",
        )

    # ------------------------------------------------------------------
    # read-only saturation
    # ------------------------------------------------------------------

    def test_wide_read_fanout_is_admitted_in_one_cycle(self) -> None:
        runtime = self.bootstrap(actions=actions_payload(recon=64))
        self.complete(runtime, "coordinate")
        cycle = runtime.scheduler.next_cycle(CAMPAIGN_ID)
        self.assertEqual(cycle.ready, 64)
        self.assertEqual(cycle.selected_count, 64)
        self.assertFalse(cycle.underutilized())
        self.assertEqual(cycle.blocked_resource_capacity, 0)
        self.assertEqual(cycle.blocked_claim, 0)

    def test_caller_batch_limit_cannot_serialize_saturation(self) -> None:
        runtime = self.bootstrap(actions=actions_payload(recon=32))
        self.complete(runtime, "coordinate")
        selected = runtime.scheduler.next_actions(CAMPAIGN_ID, limit=4)
        self.assertEqual(len(selected), 32)
        cycle = runtime.scheduler.next_cycle(CAMPAIGN_ID, limit=4)
        self.assertEqual(cycle.caller_limit, 4)
        self.assertFalse(cycle.caller_limit_applied)

    def test_hard_limit_is_an_explicit_safety_ceiling(self) -> None:
        runtime = self.bootstrap(actions=actions_payload(recon=32))
        self.complete(runtime, "coordinate")
        cycle = runtime.scheduler.next_cycle(CAMPAIGN_ID, hard_limit=5)
        self.assertEqual(cycle.selected_count, 5)
        self.assertTrue(cycle.caller_limit_applied)

    def test_non_saturating_policy_still_honors_caller_limit(self) -> None:
        runtime = self.bootstrap(actions=actions_payload(recon=32))
        self.complete(runtime, "coordinate")
        policy = dict(load_policy("resource-classes"))
        policy["global"] = {**policy["global"], "fill_policy": "batch"}
        runtime.scheduler.resource_policy = policy
        cycle = runtime.scheduler.next_cycle(CAMPAIGN_ID, limit=4)
        self.assertEqual(cycle.selected_count, 4)
        self.assertTrue(cycle.caller_limit_applied)

    # ------------------------------------------------------------------
    # mutation parallelism is claim-limited, not count-limited
    # ------------------------------------------------------------------

    def test_disjoint_mutations_run_concurrently(self) -> None:
        runtime = self.bootstrap(actions=actions_payload(mutations=12))
        self.complete(runtime, "coordinate")
        self.complete(runtime, "synthesize")
        cycle = runtime.scheduler.next_cycle(CAMPAIGN_ID)
        mutations = [item for item in cycle.selected if item.mutation]
        self.assertEqual(len(mutations), 12)
        self.assertEqual(cycle.blocked_claim, 0)

    def test_overlapping_mutation_claims_serialize(self) -> None:
        runtime = self.bootstrap(
            actions=actions_payload(mutations=12, shared_mutation_key=True),
        )
        self.complete(runtime, "coordinate")
        self.complete(runtime, "synthesize")
        cycle = runtime.scheduler.next_cycle(CAMPAIGN_ID)
        mutations = [item for item in cycle.selected if item.mutation]
        self.assertEqual(len(mutations), 1)
        self.assertEqual(cycle.blocked_claim, 11)

    def test_active_lease_claims_block_conflicting_admission(self) -> None:
        runtime = self.bootstrap(
            actions=actions_payload(mutations=2, shared_mutation_key=True),
        )
        self.complete(runtime, "coordinate")
        self.complete(runtime, "synthesize")
        runtime.scheduler.refresh_readiness(CAMPAIGN_ID)
        runtime.leases.issue(
            campaign_id=CAMPAIGN_ID,
            action_id="mutate-000",
            agent_id="executor-1",
        )
        cycle = runtime.scheduler.next_cycle(CAMPAIGN_ID)
        self.assertNotIn(
            "mutate-001",
            {item.action_id for item in cycle.selected},
        )
        self.assertEqual(cycle.blocked_claim, 1)
        self.assertEqual(cycle.running, 1)

    # ------------------------------------------------------------------
    # ceilings and their attribution
    # ------------------------------------------------------------------

    def test_resource_class_capacity_is_attributed(self) -> None:
        runtime = self.bootstrap(actions=actions_payload(recon=8))
        self.complete(runtime, "coordinate")
        policy = dict(load_policy("resource-classes"))
        classes = dict(policy["classes"])
        classes["repository_recon"] = {**classes["repository_recon"], "capacity": 3}
        policy["classes"] = classes
        runtime.scheduler.resource_policy = policy
        cycle = runtime.scheduler.next_cycle(CAMPAIGN_ID)
        self.assertEqual(cycle.selected_count, 3)
        self.assertEqual(cycle.blocked_resource_capacity, 5)

    def test_campaign_budget_is_attributed(self) -> None:
        runtime = self.bootstrap(
            campaign=campaign_payload(max_read_agents=2),
            actions=actions_payload(recon=8),
        )
        self.complete(runtime, "coordinate")
        cycle = runtime.scheduler.next_cycle(CAMPAIGN_ID)
        self.assertEqual(cycle.selected_count, 2)
        self.assertEqual(cycle.blocked_campaign_budget, 6)

    def test_role_cardinality_is_attributed(self) -> None:
        # The graph linter caps how many recon actions a deployment may declare;
        # this covers the runtime ceiling on how many may run at the same time.
        runtime = self.bootstrap(actions=actions_payload(recon=8))
        runtime.scheduler.set_role_ceilings(CAMPAIGN_ID, {"recon": 2})
        self.complete(runtime, "coordinate")
        cycle = runtime.scheduler.next_cycle(CAMPAIGN_ID)
        self.assertEqual(cycle.selected_count, 2)
        self.assertEqual(cycle.blocked_role_cardinality, 6)

    def test_global_provider_capacity_is_attributed(self) -> None:
        runtime = self.bootstrap(actions=actions_payload(recon=8))
        self.complete(runtime, "coordinate")
        policy = dict(load_policy("resource-classes"))
        policy["global"] = {
            **policy["global"],
            "provider_concurrency_ceiling": 6,
            "reserved_control_slots": 2,
        }
        runtime.scheduler.resource_policy = policy
        runtime.scheduler._provider_ceiling = 6
        runtime.scheduler._effective_ceiling = 6
        cycle = runtime.scheduler.next_cycle(CAMPAIGN_ID)
        self.assertEqual(cycle.available_global_slots, 4)
        self.assertEqual(cycle.selected_count, 4)
        self.assertEqual(cycle.blocked_global_capacity, 4)

    def test_worker_ceiling_reserves_control_slots(self) -> None:
        runtime = self.bootstrap()
        self.assertEqual(runtime.scheduler.provider_concurrency_ceiling, 500)
        self.assertEqual(runtime.scheduler.reserved_control_slots, 20)
        self.assertEqual(runtime.scheduler.worker_concurrency_ceiling, 480)

    def test_undeclared_resource_class_is_reported_not_dropped(self) -> None:
        # Bootstrap fails closed on an undeclared class, so reach this state the
        # only way it can happen at runtime: the policy drops a class that the
        # compiled graph still references.
        runtime = self.bootstrap(actions=actions_payload(recon=2))
        self.complete(runtime, "coordinate")
        policy = dict(load_policy("resource-classes"))
        policy["classes"] = {
            name: config for name, config in policy["classes"].items() if name != "repository_recon"
        }
        runtime.scheduler.resource_policy = policy
        cycle = runtime.scheduler.next_cycle(CAMPAIGN_ID)
        self.assertEqual(cycle.blocked_unknown_resource_class, 2)
        self.assertEqual(cycle.selected_count, 0)
        self.assertTrue(cycle.underutilized())

    def test_human_gate_is_never_auto_admitted(self) -> None:
        actions = actions_payload(recon=1)
        actions["actions"].append(
            {
                "id": "human-approval",
                "role": "coordinator",
                "kind": "human_gate",
                "depends_on": ["coordinate"],
                "mutation": False,
                "resource_class": "human_gate",
                "claims": [],
                "completion": {
                    "artifact_kind": "HumanDecision",
                    "required_fields": ["base_sha"],
                    "require_base_sha_match": True,
                },
                "priority_weight": 1,
            }
        )
        runtime = self.bootstrap(actions=actions)
        self.complete(runtime, "coordinate")
        cycle = runtime.scheduler.next_cycle(CAMPAIGN_ID)
        self.assertEqual(cycle.blocked_human_gate, 1)
        self.assertNotIn(
            "human-approval",
            {item.action_id for item in cycle.selected},
        )

    # ------------------------------------------------------------------
    # telemetry
    # ------------------------------------------------------------------

    def test_cycle_telemetry_exposes_every_required_counter(self) -> None:
        runtime = self.bootstrap(actions=actions_payload(recon=4))
        cycle = runtime.scheduler.next_cycle(CAMPAIGN_ID)
        rendered = cycle.render()
        for name in (
            "ready",
            "running",
            "selected",
            "available_global_slots",
            "blocked_dependency",
            "blocked_claim",
            "blocked_resource_capacity",
            "blocked_campaign_budget",
            "blocked_role_cardinality",
        ):
            self.assertIn(f"{name}=", rendered)
        self.assertEqual(cycle.blocked_dependency, 4)

    def test_status_reports_scheduling_telemetry(self) -> None:
        runtime = self.bootstrap(actions=actions_payload(recon=4))
        status = runtime.status(CAMPAIGN_ID)
        self.assertIn("scheduling", status)
        self.assertEqual(status["scheduling"]["selected"], len(status["ready"]))

    def test_backpressure_decreases_then_recovers(self) -> None:
        runtime = self.bootstrap()
        scheduler = runtime.scheduler
        self.assertTrue(scheduler.backpressure_enabled)
        throttled = scheduler.record_provider_throttle()
        self.assertEqual(throttled, 375)
        self.assertEqual(scheduler.worker_concurrency_ceiling, 355)
        recovered = scheduler.record_provider_recovery()
        self.assertEqual(recovered, 385)
        for _ in range(200):
            scheduler.record_provider_recovery()
        self.assertEqual(
            scheduler.record_provider_recovery(),
            scheduler.provider_concurrency_ceiling,
        )


if __name__ == "__main__":
    unittest.main()

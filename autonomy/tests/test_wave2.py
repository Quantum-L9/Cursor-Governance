from __future__ import annotations

import copy
import tempfile
import unittest
import uuid
from pathlib import Path

from autonomy.compiler.graph_compiler import compile_graph
from autonomy.errors import ContractError, PolicyViolation
from autonomy.io import load_json
from autonomy.models import (
    CampaignAuthorization,
    DeploymentManifest,
)
from autonomy.runtime.engine import AutonomyRuntime

ROOT = Path(__file__).resolve().parents[2]


class Wave2RuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.database = Path(self.tempdir.name) / "runtime.sqlite3"
        self.campaign_payload = load_json(ROOT / "autonomy/examples/w7-campaign.json")
        self.campaign_payload["base_state"]["commit_sha"] = "abc1234"
        self.deployment_payload = load_json(ROOT / "autonomy/examples/w7-deployment.json")
        self.actions_payload = load_json(ROOT / "autonomy/examples/w7-actions.json")
        campaign = CampaignAuthorization.from_dict(self.campaign_payload)
        deployment = DeploymentManifest.from_dict(self.deployment_payload)
        compiled = compile_graph(
            campaign,
            deployment,
            self.actions_payload,
        )
        self.graph_payload = compiled.to_dict()
        self.runtime = AutonomyRuntime.from_repository(
            repository_root=ROOT,
            database_path=self.database,
            signing_key="test-signing-key",
        )
        self.runtime.bootstrap(
            campaign_payload=self.campaign_payload,
            deployment_payload=self.deployment_payload,
            graph_payload=self.graph_payload,
        )
        self.campaign_id = self.campaign_payload["campaign_id"]

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_initial_actions_become_ready(self) -> None:
        ready = self.runtime.scheduler.next_actions(self.campaign_id)
        ids = {item.action_id for item in ready}
        self.assertIn("campaign-coordinator", ids)
        self.assertNotIn("execute-m0", ids)

    def test_lease_requires_ready_action(self) -> None:
        with self.assertRaises(PolicyViolation):
            self.runtime.leases.issue(
                campaign_id=self.campaign_id,
                action_id="execute-m0",
                agent_id="executor-1",
            )

    def test_role_capability_is_enforced(self) -> None:
        self.runtime.scheduler.refresh_readiness(self.campaign_id)
        lease = self.runtime.leases.issue(
            campaign_id=self.campaign_id,
            action_id="campaign-coordinator",
            agent_id="coordinator-1",
        )
        self.runtime.leases.acknowledge(
            lease_id=lease.lease_id,
            agent_id="coordinator-1",
            accepted_capabilities=[
                "campaign.inspect",
                "repository.write_scoped",
            ],
        )
        denied = self.runtime.gateway.authorize(
            lease_id=lease.lease_id,
            agent_id="coordinator-1",
            capability="repository.write_scoped",
            resource="autonomy/README.md",
        )
        self.assertFalse(denied.allowed)
        self.assertEqual(denied.code, "ROLE_CAPABILITY_DENIED")
        allowed = self.runtime.gateway.authorize(
            lease_id=lease.lease_id,
            agent_id="coordinator-1",
            capability="campaign.inspect",
        )
        self.assertTrue(allowed.allowed)

    def test_unacknowledged_lease_cannot_use_tools(self) -> None:
        lease = self.runtime.leases.issue(
            campaign_id=self.campaign_id,
            action_id="campaign-coordinator",
            agent_id="coordinator-1",
        )
        decision = self.runtime.gateway.authorize(
            lease_id=lease.lease_id,
            agent_id="coordinator-1",
            capability="campaign.inspect",
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.code, "LEASE_NOT_ACKNOWLEDGED")

    def test_base_sha_drift_revokes_lease(self) -> None:
        lease = self.runtime.leases.issue(
            campaign_id=self.campaign_id,
            action_id="campaign-coordinator",
            agent_id="coordinator-1",
        )
        self.runtime.leases.acknowledge(
            lease_id=lease.lease_id,
            agent_id="coordinator-1",
            accepted_capabilities=["campaign.inspect"],
        )
        with self.assertRaises(PolicyViolation):
            self.runtime.leases.heartbeat(
                lease_id=lease.lease_id,
                agent_id="coordinator-1",
                observed_base_sha="different-sha",
                status="running",
            )
        revoked = self.runtime.leases.get(lease.lease_id)
        self.assertEqual(revoked.status.value, "REVOKED")

    def test_claim_conflict_blocks_second_writer(self) -> None:
        # Force two independent writer actions ready for this isolated
        # arbitration test.
        with self.runtime.store.transaction() as connection:
            execute = self.runtime.store.decode_action(
                self.campaign_id,
                "execute-m0",
            )
            duplicate = copy.deepcopy(execute)
            duplicate["id"] = "execute-m0-duplicate"
            connection.execute(
                """
                INSERT INTO actions (
                    campaign_id,
                    action_id,
                    role,
                    kind,
                    status,
                    mutation,
                    resource_class,
                    priority_weight,
                    critical_depth,
                    action_json,
                    created_at,
                    updated_at
                )
                SELECT
                    campaign_id,
                    ?,
                    role,
                    kind,
                    'READY',
                    mutation,
                    resource_class,
                    priority_weight,
                    critical_depth,
                    ?,
                    created_at,
                    updated_at
                FROM actions
                WHERE campaign_id = ? AND action_id = 'execute-m0'
                """,
                (
                    duplicate["id"],
                    __import__("json").dumps(
                        duplicate,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    self.campaign_id,
                ),
            )
            connection.execute(
                """
                UPDATE actions
                SET status = 'READY'
                WHERE
                    campaign_id = ?
                    AND action_id = 'execute-m0'
                """,
                (self.campaign_id,),
            )
        first = self.runtime.leases.issue(
            campaign_id=self.campaign_id,
            action_id="execute-m0",
            agent_id="executor-1",
        )
        with self.assertRaises(PolicyViolation):
            self.runtime.leases.issue(
                campaign_id=self.campaign_id,
                action_id="execute-m0-duplicate",
                agent_id="executor-2",
            )
        self.runtime.leases.revoke(
            lease_id=first.lease_id,
            reason="test cleanup",
            actor="test",
        )

    def test_valid_artifact_completes_action(self) -> None:
        lease = self.runtime.leases.issue(
            campaign_id=self.campaign_id,
            action_id="campaign-coordinator",
            agent_id="coordinator-1",
        )
        accepted = [
            "campaign.inspect",
            "graph.inspect",
            "scheduler.request",
            "status.inspect",
        ]
        self.runtime.leases.acknowledge(
            lease_id=lease.lease_id,
            agent_id="coordinator-1",
            accepted_capabilities=accepted,
        )
        artifact_id = f"artifact-{uuid.uuid4().hex}"
        submitted = self.runtime.artifacts.submit(
            lease_id=lease.lease_id,
            agent_id="coordinator-1",
            artifact={
                "artifact_id": artifact_id,
                "kind": "CampaignStatus",
                "campaign_id": self.campaign_id,
                "graph_id": self.graph_payload["graph_id"],
                "action_id": "campaign-coordinator",
                "lease_id": lease.lease_id,
                "producer_agent_id": "coordinator-1",
                "base_sha": "abc1234",
                "input_artifacts": [],
                "payload": {
                    "campaign_id": self.campaign_id,
                    "state": "EXECUTING",
                },
            },
        )
        self.assertEqual(submitted, artifact_id)
        action = self.runtime.store.get_action(
            self.campaign_id,
            "campaign-coordinator",
        )
        self.assertEqual(action["status"], "COMPLETED")

    def test_missing_artifact_field_is_rejected(self) -> None:
        lease = self.runtime.leases.issue(
            campaign_id=self.campaign_id,
            action_id="campaign-coordinator",
            agent_id="coordinator-1",
        )
        self.runtime.leases.acknowledge(
            lease_id=lease.lease_id,
            agent_id="coordinator-1",
            accepted_capabilities=["campaign.inspect"],
        )
        with self.assertRaises(ContractError):
            self.runtime.artifacts.submit(
                lease_id=lease.lease_id,
                agent_id="coordinator-1",
                artifact={
                    "artifact_id": f"artifact-{uuid.uuid4().hex}",
                    "kind": "CampaignStatus",
                    "campaign_id": self.campaign_id,
                    "graph_id": self.graph_payload["graph_id"],
                    "action_id": "campaign-coordinator",
                    "lease_id": lease.lease_id,
                    "producer_agent_id": "coordinator-1",
                    "base_sha": "abc1234",
                    "input_artifacts": [],
                    "payload": {"campaign_id": self.campaign_id},
                },
            )

    def test_receipt_chain_verifies(self) -> None:
        errors = self.runtime.verify_receipts(self.campaign_id)
        self.assertEqual(errors, [])

    def test_forbidden_global_capability_is_denied(self) -> None:
        lease = self.runtime.leases.issue(
            campaign_id=self.campaign_id,
            action_id="campaign-coordinator",
            agent_id="coordinator-1",
        )
        self.runtime.leases.acknowledge(
            lease_id=lease.lease_id,
            agent_id="coordinator-1",
            accepted_capabilities=["pr.merge"],
        )
        decision = self.runtime.gateway.authorize(
            lease_id=lease.lease_id,
            agent_id="coordinator-1",
            capability="pr.merge",
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.code, "GLOBALLY_FORBIDDEN_CAPABILITY")


if __name__ == "__main__":
    unittest.main()

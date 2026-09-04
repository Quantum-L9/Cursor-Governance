"""Root-plane bindings a Cursor admission must carry (SA-F02/F03/F04/F06).

- verifier/reviewer leases are refused for any agent that produced the work
  under judgement (``VERIFIER_NOT_INDEPENDENT``), at ``LeaseManager.issue``;
- a verifier/reviewer admission persists the subject it must judge;
- an admission persists the campaign AND action writable scope the capability
  gateway enforces, with forbidden paths unioned;
- a Task naming a different managed ``subagent_type`` than the admitted one is
  denied at preToolUse;
- ``lease_status`` exposes the root lease state the result gateway re-checks.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any

from autonomy.adapters.cursor.host_bridge import (
    CursorHostBridge,
    host_bind_pre_tool_use,
    lease_status,
)
from autonomy.adapters.orchestrator import AdapterOrchestrator
from autonomy.compiler.graph_compiler import compile_graph
from autonomy.errors import PolicyViolation
from autonomy.models import CampaignAuthorization, DeploymentManifest
from autonomy.policy_loader import load_example, load_policy
from autonomy.runtime.engine import AutonomyRuntime
from autonomy.tests.swarm_fixtures import (
    CAMPAIGN_ID,
    actions_payload,
    campaign_payload,
    deployment_payload,
)
from environment.agents.deployment import receipts as receipt_lib

ROOT = Path(__file__).resolve().parents[2]
ACTION_ALLOWED = ["autonomy/adapters/**"]
ACTION_FORBIDDEN = ["autonomy/adapters/secrets/**"]


def _actions() -> dict[str, Any]:
    payload = actions_payload(recon=2, mutations=1)
    payload["actions"].append(
        {
            "id": "remediate-000",
            "role": "remediator",
            "kind": "work",
            "depends_on": ["synthesize"],
            "mutation": True,
            "resource_class": "repository_mutation",
            "claims": [{"key": "repo:lane-remediate", "mode": "write", "exclusive": True}],
            "completion": {
                "artifact_kind": "RemediationResult",
                "required_fields": ["base_sha"],
                "require_base_sha_match": True,
            },
            "priority_weight": 7,
            "metadata": {"allowed_paths": ACTION_ALLOWED, "forbidden_paths": ACTION_FORBIDDEN},
        }
    )
    return payload


class AdmissionBindingTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self._prev_runtime = os.environ.get("L9_RUNTIME_ROOT")
        os.environ["L9_RUNTIME_ROOT"] = str(Path(self.tempdir.name) / "l9runtime")
        self.addCleanup(self._restore_runtime)
        roles = ROOT / "environment/agents/cursor-subagents/CURSOR_SUBAGENT_ROLES.yaml"
        receipt_lib.write_deployment_receipt(
            {
                "schema": receipt_lib.RECEIPT_SCHEMA,
                "status": receipt_lib.STATUS_READY,
                "source_manifest_digest": hashlib.sha256(roles.read_bytes()).hexdigest(),
                "surface": "cursor",
            },
            surface="cursor",
            workspace_id=receipt_lib.workspace_id_for(ROOT),
        )
        self.database = Path(self.tempdir.name) / "runtime.sqlite3"
        campaign_data = campaign_payload()
        deployment_data = deployment_payload()
        compiled = compile_graph(
            CampaignAuthorization.from_dict(campaign_data),
            DeploymentManifest.from_dict(deployment_data),
            _actions(),
        )
        self.runtime = AutonomyRuntime.from_repository(
            repository_root=ROOT, database_path=self.database, signing_key="admission-binding"
        )
        self.runtime.bootstrap(
            campaign_payload=campaign_data,
            deployment_payload=deployment_data,
            graph_payload=compiled.to_dict(),
        )
        for action_id in ("coordinate", "synthesize"):
            self.runtime.store.set_action_status(
                campaign_id=CAMPAIGN_ID, action_id=action_id, status="COMPLETED"
            )
        self.runtime.scheduler.refresh_readiness(CAMPAIGN_ID)
        requirements = load_policy("adapter-requirements")
        requirements["allow_missing_executable_in_test"] = True
        self.orchestrator = AdapterOrchestrator(
            self.runtime, repository_root=ROOT, requirements=requirements
        )
        self.bridge = CursorHostBridge(self.runtime, self.orchestrator)
        self.campaign_scope = self.runtime.store.decode_campaign(CAMPAIGN_ID)["scope"]

    def _restore_runtime(self) -> None:
        if self._prev_runtime is None:
            os.environ.pop("L9_RUNTIME_ROOT", None)
        else:
            os.environ["L9_RUNTIME_ROOT"] = self._prev_runtime

    def _admit(self, agent_id: str, action_id: str) -> dict[str, Any]:
        return self.bridge.create_admission(
            campaign_id=CAMPAIGN_ID,
            agent_id=agent_id,
            adapter_config=load_example("adapters/cursor.json"),
            action_id=action_id,
        )

    def _complete(self, action_id: str) -> None:
        self.runtime.store.set_action_status(
            campaign_id=CAMPAIGN_ID, action_id=action_id, status="COMPLETED"
        )
        self.runtime.scheduler.refresh_readiness(CAMPAIGN_ID)

    def _bound(self, admission: dict[str, Any], tool_use_id: str, **kwargs: Any) -> dict[str, Any]:
        return host_bind_pre_tool_use(
            self.database, admission["admission_token"], tool_use_id, **kwargs
        )


class VerifierIndependenceTests(AdmissionBindingTestCase):
    def test_producer_cannot_lease_verification_of_its_own_mutation(self) -> None:
        self._admit("cursor-child-1", "mutate-000")
        self._complete("mutate-000")
        with self.assertRaises(PolicyViolation) as caught:
            self._admit("cursor-child-1", "verify-000")
        self.assertIn("VERIFIER_NOT_INDEPENDENT", str(caught.exception))
        # No lease leaked for the refused request.
        with self.runtime.store.connect() as connection:
            rows = connection.execute(
                "SELECT lease_id FROM leases WHERE action_id = 'verify-000'"
            ).fetchall()
        self.assertEqual(rows, [])

    def test_lease_manager_refuses_at_the_root_plane(self) -> None:
        self._admit("cursor-child-1", "mutate-000")
        self._complete("mutate-000")
        with self.assertRaises(PolicyViolation) as caught:
            self.runtime.leases.issue(
                campaign_id=CAMPAIGN_ID, action_id="verify-000", agent_id="cursor-child-1"
            )
        self.assertIn("VERIFIER_NOT_INDEPENDENT", str(caught.exception))

    def test_independent_agent_is_admitted_with_the_subject_persisted(self) -> None:
        self._admit("cursor-child-1", "mutate-000")
        self._complete("mutate-000")
        verifier = self._admit("cursor-child-2", "verify-000")
        self.assertEqual(verifier["agent_contract"]["role"], "verifier")
        bound = self._bound(verifier, "tu-verify")
        self.assertTrue(bound["allowed"], bound)
        self.assertEqual(bound["admission"]["subject_agent_id"], "cursor-child-1")
        self.assertEqual(bound["admission"]["expected_subagent_type"], "l9-verifier-reviewer")

    def test_reviewer_is_independent_from_every_producer_in_the_chain(self) -> None:
        self._admit("cursor-child-1", "mutate-000")
        self._complete("mutate-000")
        self._admit("cursor-child-2", "verify-000")
        self._complete("verify-000")
        for producer in ("cursor-child-1", "cursor-child-2"):
            with self.assertRaises(PolicyViolation, msg=producer) as caught:
                self._admit(producer, "review")
            self.assertIn("VERIFIER_NOT_INDEPENDENT", str(caught.exception))
        reviewer = self._admit("cursor-child-3", "review")
        bound = self._bound(reviewer, "tu-review")
        # independent_from names the subject under review: the executor.
        self.assertEqual(bound["admission"]["subject_agent_id"], "cursor-child-1")

    def test_non_judging_role_admission_carries_no_subject(self) -> None:
        recon = self._admit("cursor-child-1", "recon-000")
        bound = self._bound(recon, "tu-recon")
        self.assertIsNone(bound["admission"]["subject_agent_id"])


class WritableScopeBindingTests(AdmissionBindingTestCase):
    def test_admission_persists_campaign_and_action_scope(self) -> None:
        admission = self._admit("cursor-child-1", "remediate-000")
        bound = self._bound(admission, "tu-remediate")["admission"]
        self.assertEqual(bound["allowed_paths"], list(self.campaign_scope["allowed_paths"]))
        self.assertEqual(bound["action_allowed_paths"], ACTION_ALLOWED)
        for pattern in list(self.campaign_scope["forbidden_paths"]) + ACTION_FORBIDDEN:
            self.assertIn(pattern, bound["forbidden_paths"])

    def test_action_without_narrowing_persists_empty_action_scope(self) -> None:
        admission = self._admit("cursor-child-1", "mutate-000")
        bound = self._bound(admission, "tu-mutate")["admission"]
        self.assertEqual(bound["action_allowed_paths"], [])
        self.assertEqual(bound["allowed_paths"], list(self.campaign_scope["allowed_paths"]))


class SubagentTypeBindingTests(AdmissionBindingTestCase):
    def test_mismatched_subagent_type_is_denied(self) -> None:
        admission = self._admit("cursor-child-1", "recon-000")
        decision = self._bound(admission, "tu-1", subagent_type="generalPurpose")
        self.assertFalse(decision["allowed"])
        self.assertIn("subagent_type", decision["reason"])
        # The denied Task did not consume the single-use token.
        retry = self._bound(admission, "tu-1", subagent_type="l9-recon")
        self.assertTrue(retry["allowed"], retry)

    def test_matching_or_absent_subagent_type_is_allowed(self) -> None:
        first = self._admit("cursor-child-1", "recon-000")
        self.assertTrue(self._bound(first, "tu-1", subagent_type="l9-recon")["allowed"])
        second = self._admit("cursor-child-2", "recon-001")
        self.assertTrue(self._bound(second, "tu-2")["allowed"])
        self.assertEqual(
            self._bound(second, "tu-2")["admission"]["expected_subagent_type"], "l9-recon"
        )


class LeaseStatusLookupTests(AdmissionBindingTestCase):
    def test_lease_status_reflects_root_lease_state(self) -> None:
        admission = self._admit("cursor-child-1", "recon-000")
        lease_id = admission["lease"]["lease_id"]
        self.assertEqual(lease_status(self.database, lease_id), "ACTIVE")
        self.runtime.leases.revoke(lease_id=lease_id, reason="operator cancel", actor="test")
        self.assertEqual(lease_status(self.database, lease_id), "REVOKED")
        self.assertIsNone(lease_status(self.database, "lease-does-not-exist"))


if __name__ == "__main__":
    unittest.main()

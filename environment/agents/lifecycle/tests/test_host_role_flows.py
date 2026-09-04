"""Host-admitted role flows through the real root-Autonomy authority.

Covers the defects the audit reproduced on the native Cursor host path:

- SA-F01: an admission persists the autonomy role (``executor``) while the
  document carries the Cursor role (``test``); every mutating and reviewing
  role must round-trip to an ACCEPTED result, not only ``recon``;
- SA-F02: a cancelled host stop, or a revoked root lease, rejects a
  structurally valid document — the document never out-votes the host;
- SA-F05: a correlation rejection still leaves a durable REJECTED receipt;
- SA-F06: the Task's ``subagent_type`` must match the admitted managed agent;
- SA-F08: a partial document is accepted as incomplete, never as success;
- SA-F10: two agents may reuse one result_id on different assignments.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

_GOV_ROOT = Path(__file__).resolve().parents[4]
if str(_GOV_ROOT) not in sys.path:
    sys.path.insert(0, str(_GOV_ROOT))

from autonomy.adapters.cursor.host_bridge import CursorHostBridge  # noqa: E402
from autonomy.adapters.orchestrator import AdapterOrchestrator  # noqa: E402
from autonomy.compiler.graph_compiler import compile_graph  # noqa: E402
from autonomy.models import CampaignAuthorization, DeploymentManifest  # noqa: E402
from autonomy.policy_loader import load_example, load_policy  # noqa: E402
from autonomy.runtime.engine import AutonomyRuntime  # noqa: E402
from autonomy.tests.swarm_fixtures import (  # noqa: E402
    CAMPAIGN_ID,
    actions_payload,
    campaign_payload,
    deployment_payload,
)
from environment.agents.deployment import receipts as deploy_receipts  # noqa: E402
from environment.agents.lifecycle import compose_start, compose_stop, receipts  # noqa: E402
from environment.agents.results import receipts as result_receipts  # noqa: E402

RESULT_KIND = {
    "recon": "ReconReport",
    "pr_remediation": "PRRemediationReport",
    "test": "TestReport",
    "documentation": "DocumentationReport",
    "verifier_reviewer": "VerificationReviewReport",
}


def _completion(kind: str) -> dict[str, Any]:
    return {"artifact_kind": kind, "required_fields": ["base_sha"], "require_base_sha_match": True}


def _actions() -> dict[str, Any]:
    payload = actions_payload(recon=2, mutations=1)
    payload["actions"].extend(
        [
            {
                "id": "remediate-000",
                "role": "remediator",
                "kind": "work",
                "depends_on": ["synthesize"],
                "mutation": True,
                "resource_class": "repository_mutation",
                "claims": [{"key": "repo:lane-remediate", "mode": "write", "exclusive": True}],
                "completion": _completion("RemediationResult"),
                "priority_weight": 7,
            },
            {
                "id": "document-000",
                "role": "evidence_writer",
                "kind": "work",
                "depends_on": ["synthesize"],
                "mutation": False,
                "resource_class": "repository_read",
                "claims": [],
                "completion": _completion("EvidenceReceipt"),
                "priority_weight": 5,
            },
        ]
    )
    return payload


class HostRoleFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        os.environ["L9_RUNTIME_ROOT"] = self.tmp.name
        self.addCleanup(os.environ.pop, "L9_RUNTIME_ROOT", None)
        deploy_receipts.write_deployment_receipt(
            {
                "schema": deploy_receipts.RECEIPT_SCHEMA,
                "status": deploy_receipts.STATUS_READY,
                "source_manifest_digest": deploy_receipts.source_manifest_digest(_GOV_ROOT),
                "surface": "cursor",
            },
            surface="cursor",
            workspace_id=deploy_receipts.workspace_id_for(_GOV_ROOT),
        )
        self.database = Path(self.tmp.name) / "runtime.sqlite3"
        os.environ["L9_AUTONOMY_RUNTIME_DB"] = str(self.database)
        self.addCleanup(os.environ.pop, "L9_AUTONOMY_RUNTIME_DB", None)
        campaign_data = campaign_payload()
        campaign_data["base_state"]["commit_sha"] = "a" * 40
        deployment_data = deployment_payload()
        compiled = compile_graph(
            CampaignAuthorization.from_dict(campaign_data),
            DeploymentManifest.from_dict(deployment_data),
            _actions(),
        )
        self.runtime = AutonomyRuntime.from_repository(
            repository_root=_GOV_ROOT, database_path=self.database, signing_key="host-role-flows"
        )
        self.runtime.bootstrap(
            campaign_payload=campaign_data,
            deployment_payload=deployment_data,
            graph_payload=compiled.to_dict(),
        )
        for action_id in ("coordinate", "synthesize"):
            self._complete(action_id)
        requirements = load_policy("adapter-requirements")
        requirements["allow_missing_executable_in_test"] = True
        self.bridge = CursorHostBridge(
            self.runtime,
            AdapterOrchestrator(self.runtime, repository_root=_GOV_ROOT, requirements=requirements),
        )
        self.counter = 0

    def _complete(self, action_id: str) -> None:
        self.runtime.store.set_action_status(
            campaign_id=CAMPAIGN_ID, action_id=action_id, status="COMPLETED"
        )
        self.runtime.scheduler.refresh_readiness(CAMPAIGN_ID)

    def _flow(self, agent_id: str, action_id: str) -> tuple[dict[str, Any], dict[str, Any], str]:
        """Admit, launch, and start one host child; return (admission, assignment, subagent_id)."""
        self.counter += 1
        tool_use_id = f"tu-{self.counter}"
        subagent_id = f"sub-{self.counter}"
        admission = self.bridge.create_admission(
            campaign_id=CAMPAIGN_ID,
            agent_id=agent_id,
            adapter_config=load_example("adapters/cursor.json"),
            action_id=action_id,
        )
        pre = compose_start.compose_host_pre_tool_use(
            {
                "tool_name": "Task",
                "tool_use_id": tool_use_id,
                "tool_input": {"prompt": f"Execute. {admission['prompt_marker']}"},
            }
        )
        self.assertEqual(pre["permission"], "allow", pre)
        start = compose_start.compose_host_subagent_start(
            {"subagent_id": subagent_id, "tool_call_id": tool_use_id}
        )
        self.assertEqual(start["permission"], "allow", start)
        assignment = receipts.load_assignment(admission["admission_token"])
        self.assertIsNotNone(assignment)
        return admission, assignment, subagent_id

    @staticmethod
    def _document(
        assignment: dict[str, Any],
        role: str,
        *,
        result_id: str,
        files_changed: list[str] | None = None,
        status: str = "completed",
        findings: list[dict[str, Any]] | None = None,
        subject_agent_id: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "role": role,
            "objective": "Bounded host flow.",
            "input_artifact_ids": [],
            "allowed_paths": list(assignment.get("allowed_paths") or []),
            "forbidden_paths": list(assignment.get("forbidden_paths") or []),
        }
        if subject_agent_id is not None:
            body["subject_agent_id"] = subject_agent_id
        return {
            "schema": "l9.cursor-subagent.result.v1",
            "schema_version": "1.0.0",
            "result_id": result_id,
            "result_kind": RESULT_KIND[role],
            "status": status,
            "identity": {
                key: assignment[key]
                for key in (
                    "campaign_id",
                    "graph_id",
                    "action_id",
                    "agent_id",
                    "lease_id",
                    "base_sha",
                )
            },
            "assignment": body,
            "deliverable": {
                "summary": "One durable result was produced.",
                "findings": findings or [],
                "files_read": ["autonomy/adapters/cursor/host_bridge.py"],
                "files_changed": files_changed or [],
                "evidence": [],
                "commands_executed": [],
                "validations": [],
                "unresolved_items": [],
                "recommended_next_actions": [],
                "reuse_assessment": {"reusable_data_found": False, "confidence": 1.0},
                "visibility": "campaign_local",
            },
            "provenance": {"produced_at": "2026-09-02T00:00:00Z"},
        }

    def _stop(self, subagent_id: str, document: dict[str, Any], status: str = "COMPLETED"):
        out = compose_stop.compose_subagent_stop(
            {"subagent_id": subagent_id, "status": status, "output": document}
        )
        self.assertEqual(out["status"], "RETURNED", out)
        return out["generated_data"]

    # ------------------------------------------------------------------ F01

    def test_mutating_and_reviewing_roles_round_trip_to_accepted(self) -> None:
        _, executor, sub_exec = self._flow("cursor-exec", "mutate-000")
        self.assertEqual(executor["subagent_role"], "executor")
        self.assertEqual(executor["result_role"], "test")
        generated = self._stop(
            sub_exec,
            self._document(executor, "test", result_id="r-exec", files_changed=["autonomy/x.py"]),
        )
        self.assertEqual(generated["status"], "ACCEPTED", generated)

        _, remediator, sub_rem = self._flow("cursor-rem", "remediate-000")
        self.assertEqual(remediator["result_role"], "pr_remediation")
        generated = self._stop(
            sub_rem,
            self._document(
                remediator, "pr_remediation", result_id="r-rem", files_changed=["autonomy/y.py"]
            ),
        )
        self.assertEqual(generated["status"], "ACCEPTED", generated)

        _, writer, sub_doc = self._flow("cursor-doc", "document-000")
        self.assertEqual(writer["result_role"], "documentation")
        generated = self._stop(sub_doc, self._document(writer, "documentation", result_id="r-doc"))
        self.assertEqual(generated["status"], "ACCEPTED", generated)

        self._complete("mutate-000")
        _, verifier, sub_ver = self._flow("cursor-ver", "verify-000")
        self.assertEqual(verifier["subagent_role"], "verifier")
        self.assertEqual(verifier["result_role"], "verifier_reviewer")
        self.assertEqual(verifier["subject_agent_id"], "cursor-exec")
        generated = self._stop(
            sub_ver,
            self._document(
                verifier, "verifier_reviewer", result_id="r-ver", subject_agent_id="cursor-exec"
            ),
        )
        self.assertEqual(generated["status"], "ACCEPTED", generated)

        self._complete("verify-000")
        _, reviewer, sub_rev = self._flow("cursor-rev", "review")
        self.assertEqual(reviewer["subagent_role"], "reviewer")
        self.assertEqual(reviewer["subject_agent_id"], "cursor-exec")
        generated = self._stop(
            sub_rev,
            self._document(
                reviewer, "verifier_reviewer", result_id="r-rev", subject_agent_id="cursor-exec"
            ),
        )
        self.assertEqual(generated["status"], "ACCEPTED", generated)

    # ------------------------------------------------------------------ F03

    def test_reviewer_document_naming_another_subject_is_rejected(self) -> None:
        self._flow("cursor-exec", "mutate-000")
        self._complete("mutate-000")
        _, verifier, sub_ver = self._flow("cursor-ver", "verify-000")
        generated = self._stop(
            sub_ver,
            self._document(
                verifier, "verifier_reviewer", result_id="r-ver", subject_agent_id="someone-else"
            ),
        )
        self.assertEqual(generated["status"], "REJECTED", generated)
        self.assertIn("subject", generated["acceptance_receipt"]["reason"])

    # ------------------------------------------------------------------ F02

    def test_cancelled_host_stop_rejects_a_valid_document(self) -> None:
        _, assignment, subagent_id = self._flow("cursor-child-1", "recon-000")
        generated = self._stop(
            subagent_id, self._document(assignment, "recon", result_id="r-1"), status="CANCELLED"
        )
        self.assertEqual(generated["status"], "REJECTED", generated)
        receipt = generated["acceptance_receipt"]
        self.assertEqual(receipt["status"], "REJECTED")
        self.assertIn("CANCELLED", receipt["reason"])
        self.assertIsNone(generated["ingress_receipt"])
        self.assertTrue(
            result_receipts.acceptance_path(
                receipt["result_id"], receipt["assignment_id"]
            ).is_file()
        )

    def test_revoked_root_lease_rejects_a_valid_document(self) -> None:
        admission, assignment, subagent_id = self._flow("cursor-child-1", "recon-000")
        self.runtime.leases.revoke(
            lease_id=admission["lease"]["lease_id"], reason="operator cancel", actor="test"
        )
        generated = self._stop(subagent_id, self._document(assignment, "recon", result_id="r-1"))
        self.assertEqual(generated["status"], "REJECTED", generated)
        self.assertIn("REVOKED", generated["acceptance_receipt"]["reason"])
        self.assertIsNone(generated["ingress_receipt"])

    def test_released_lease_still_accepts_a_completed_document(self) -> None:
        admission, assignment, subagent_id = self._flow("cursor-child-1", "recon-000")
        self.runtime.leases.release(lease_id=admission["lease"]["lease_id"], actor="test")
        generated = self._stop(subagent_id, self._document(assignment, "recon", result_id="r-1"))
        self.assertEqual(generated["status"], "ACCEPTED", generated)

    # ------------------------------------------------------------------ F05

    def test_wrong_role_document_leaves_a_durable_rejected_receipt(self) -> None:
        _, assignment, subagent_id = self._flow("cursor-child-1", "recon-000")
        document = self._document(assignment, "test", result_id="r-wrong")
        generated = self._stop(subagent_id, document)
        self.assertEqual(generated["status"], "REJECTED", generated)
        receipt = generated["acceptance_receipt"]
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt["status"], "REJECTED")
        self.assertIn("role", receipt["reason"])
        path = result_receipts.acceptance_path(receipt["result_id"], receipt["assignment_id"])
        self.assertTrue(path.is_file(), path)

    # ------------------------------------------------------------------ F06

    def test_task_subagent_type_must_match_the_admitted_managed_agent(self) -> None:
        admission = self.bridge.create_admission(
            campaign_id=CAMPAIGN_ID,
            agent_id="cursor-child-1",
            adapter_config=load_example("adapters/cursor.json"),
            action_id="recon-000",
        )

        def payload(subagent_type: str | None) -> dict[str, Any]:
            tool_input: dict[str, Any] = {"prompt": admission["prompt_marker"]}
            if subagent_type is not None:
                tool_input["subagent_type"] = subagent_type
            return {"tool_name": "Task", "tool_use_id": "tu-type", "tool_input": tool_input}

        denied = compose_start.compose_host_pre_tool_use(payload("generalPurpose"))
        self.assertEqual(denied["permission"], "deny", denied)
        self.assertIn("subagent_type", denied["reason"])
        allowed = compose_start.compose_host_pre_tool_use(payload("l9-recon"))
        self.assertEqual(allowed["permission"], "allow", allowed)
        replay = compose_start.compose_host_pre_tool_use(payload(None))
        self.assertEqual(replay["permission"], "allow", replay)

    # ------------------------------------------------------------------ F08

    def test_partial_document_is_accepted_incomplete_not_success(self) -> None:
        _, assignment, subagent_id = self._flow("cursor-child-1", "recon-000")
        finding = {
            "finding_id": "f-1",
            "primary_class": "repository_fact",
            "epistemic_status": "observed",
            "statement": "Half of the surface was inspected before the budget ran out.",
            "scope": {"module": "autonomy/adapters/cursor"},
            "confidence": 0.5,
            "proposed_routes": ["memory", "contracts"],
        }
        document = self._document(
            assignment, "recon", result_id="r-partial", status="partial", findings=[finding]
        )
        generated = self._stop(subagent_id, document)
        self.assertEqual(generated["status"], "ACCEPTED_INCOMPLETE", generated)
        self.assertEqual(generated["document_status"], "partial")
        self.assertEqual(generated["result_acceptance_status"], "ACCEPTED")
        self.assertEqual(generated["acceptance_receipt"]["document_status"], "partial")

    # ------------------------------------------------------------------ F10

    def test_same_result_id_on_different_assignments_is_not_a_collision(self) -> None:
        _, first, sub_first = self._flow("cursor-child-1", "recon-000")
        _, second, sub_second = self._flow("cursor-child-2", "recon-001")
        one = self._stop(sub_first, self._document(first, "recon", result_id="shared-id"))
        two = self._stop(sub_second, self._document(second, "recon", result_id="shared-id"))
        self.assertEqual(one["status"], "ACCEPTED", one)
        self.assertEqual(two["status"], "ACCEPTED", two)
        self.assertNotEqual(
            one["acceptance_receipt"]["receipt_digest"], two["acceptance_receipt"]["receipt_digest"]
        )


if __name__ == "__main__":
    unittest.main()

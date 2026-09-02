"""Native Cursor host lifecycle against real root-Autonomy authority (PHASE-2).

Drives the actual host hook composition functions with realistic Cursor hook
JSON fixtures: preToolUse(Task) carrying only an opaque admission token,
subagentStart correlated by ``tool_call_id == tool_use_id``, and subagentStop
resolved through the persisted host correlation. Everything uncorrelated stays
denied, exactly as PR #287's fail-closed floor.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

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


class HostLifecycleTests(unittest.TestCase):
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
            actions_payload(recon=1),
        )
        self.runtime = AutonomyRuntime.from_repository(
            repository_root=_GOV_ROOT,
            database_path=self.database,
            signing_key="host-lifecycle-test",
        )
        self.runtime.bootstrap(
            campaign_payload=campaign_data,
            deployment_payload=deployment_data,
            graph_payload=compiled.to_dict(),
        )
        self.runtime.store.set_action_status(
            campaign_id=CAMPAIGN_ID, action_id="coordinate", status="COMPLETED"
        )
        self.runtime.scheduler.refresh_readiness(CAMPAIGN_ID)
        requirements = load_policy("adapter-requirements")
        requirements["allow_missing_executable_in_test"] = True
        self.bridge = CursorHostBridge(
            self.runtime,
            AdapterOrchestrator(self.runtime, repository_root=_GOV_ROOT, requirements=requirements),
        )

    def _admission(self) -> dict:
        return self.bridge.create_admission(
            campaign_id=CAMPAIGN_ID,
            agent_id="cursor-child-1",
            adapter_config=load_example("adapters/cursor.json"),
        )

    @staticmethod
    def _pre_tool_use_payload(marker: str) -> dict:
        # Real preToolUse hook shape: tool identity plus the Task input; only
        # the opaque token is ever read out of the prompt.
        return {
            "hook_event_name": "preToolUse",
            "conversation_id": "conv-1",
            "tool_name": "Task",
            "tool_use_id": "tu-100",
            "tool_input": {
                "description": "governed child",
                "prompt": f"Execute the assignment. {marker}",
            },
        }

    @staticmethod
    def _subagent_start_payload() -> dict:
        return {
            "hook_event_name": "subagentStart",
            "subagent_id": "sub-100",
            "tool_call_id": "tu-100",
            "parent_conversation_id": "conv-1",
            "model": "cursor-default",
            "is_parallel_worker": True,
            "git_branch": "agent/native-child",
        }

    def test_full_host_flow_admits_and_correlates(self) -> None:
        admission = self._admission()
        pre = compose_start.compose_host_pre_tool_use(
            self._pre_tool_use_payload(admission["prompt_marker"])
        )
        self.assertEqual(pre["permission"], "allow", pre)
        self.assertEqual(pre["lease_id"], admission["lease"]["lease_id"])
        start = compose_start.compose_host_subagent_start(self._subagent_start_payload())
        self.assertEqual(start["permission"], "allow", start)
        # Host identity is persisted through the lifecycle correlation receipt.
        correlation = receipts.load_host_correlation("sub-100")
        self.assertIsNotNone(correlation)
        self.assertEqual(correlation["assignment_id"], admission["admission_token"])
        self.assertEqual(correlation["tool_call_id"], "tu-100")
        self.assertEqual(correlation["lease_id"], admission["lease"]["lease_id"])
        self.assertEqual(correlation["model"], "cursor-default")
        self.assertTrue(correlation["is_parallel_worker"])
        # And the assignment receipt exists for the result pipeline.
        self.assertTrue(receipts.assignment_path(admission["admission_token"]).is_file())

    def test_task_without_token_stays_denied(self) -> None:
        self._admission()
        payload = self._pre_tool_use_payload("no token in this prompt")
        out = compose_start.compose_host_pre_tool_use(payload)
        self.assertEqual(out["permission"], "deny")
        self.assertIn("admission token", out["reason"])

    def test_task_with_unknown_token_stays_denied(self) -> None:
        payload = self._pre_tool_use_payload("L9_ADMISSION_TOKEN=admission-doesnotexist")
        out = compose_start.compose_host_pre_tool_use(payload)
        self.assertEqual(out["permission"], "deny")

    def test_missing_runtime_database_stays_denied(self) -> None:
        admission = self._admission()
        os.environ["L9_AUTONOMY_RUNTIME_DB"] = str(Path(self.tmp.name) / "absent.sqlite3")
        out = compose_start.compose_host_pre_tool_use(
            self._pre_tool_use_payload(admission["prompt_marker"])
        )
        self.assertEqual(out["permission"], "deny")
        self.assertIn("runtime database", out["reason"])

    def test_uncorrelated_subagent_start_stays_denied(self) -> None:
        self._admission()
        out = compose_start.compose_host_subagent_start(self._subagent_start_payload())
        self.assertEqual(out["permission"], "deny")

    def test_host_stop_routes_through_correlated_assignment(self) -> None:
        admission = self._admission()
        compose_start.compose_host_pre_tool_use(
            self._pre_tool_use_payload(admission["prompt_marker"])
        )
        compose_start.compose_host_subagent_start(self._subagent_start_payload())
        out = compose_stop.compose_subagent_stop(
            {"subagent_id": "sub-100", "status": "COMPLETED", "output": "done"}
        )
        # The correlated stop resolves to the admission's assignment and enters
        # the existing result pipeline (never quarantined as an orphan).
        self.assertNotEqual(out.get("status"), "QUARANTINED")
        self.assertTrue(receipts.host_stop_path("sub-100").is_file())

    def test_host_stop_structured_result_writes_accepted_subagent_ingress(self) -> None:
        admission = self._admission()
        compose_start.compose_host_pre_tool_use(
            self._pre_tool_use_payload(admission["prompt_marker"])
        )
        compose_start.compose_host_subagent_start(self._subagent_start_payload())
        assignment = receipts.load_assignment(admission["admission_token"])
        self.assertIsNotNone(assignment)
        document = {
            "schema": "l9.cursor-subagent.result.v1",
            "schema_version": "1.0.0",
            "result_id": "result-host-ingest-001",
            "result_kind": "ReconReport",
            "status": "completed",
            "identity": {
                "campaign_id": assignment["campaign_id"],
                "graph_id": assignment["graph_id"],
                "action_id": assignment["action_id"],
                "agent_id": assignment["agent_id"],
                "lease_id": assignment["lease_id"],
                "base_sha": assignment["base_sha"],
            },
            "assignment": {
                "role": "recon",
                "objective": "Inspect the generated-data seam.",
                "input_artifact_ids": [],
                "allowed_paths": list(assignment.get("allowed_paths") or []),
                "forbidden_paths": list(assignment.get("forbidden_paths") or []),
            },
            "deliverable": {
                "summary": "One durable result was produced.",
                "findings": [],
                "files_read": ["environment/agents/results/gateway.py"],
                "files_changed": [],
                "evidence": [],
                "commands_executed": [],
                "validations": [],
                "unresolved_items": [],
                "recommended_next_actions": [],
                "reuse_assessment": {
                    "reusable_data_found": False,
                    "confidence": 1.0,
                    "reason": "No reusable finding in this host-lifecycle fixture.",
                },
                "visibility": "repository_local",
            },
            "provenance": {"produced_at": "2026-08-30T23:54:00Z"},
        }
        out = compose_stop.compose_subagent_stop(
            {"subagent_id": "sub-100", "status": "COMPLETED", "output": document}
        )
        self.assertEqual(out.get("status"), "RETURNED", out)
        generated = out.get("generated_data") or {}
        ingress = generated.get("ingress_receipt") or {}
        self.assertEqual(ingress.get("source_kind"), "accepted_subagent_result", generated)


if __name__ == "__main__":
    unittest.main()

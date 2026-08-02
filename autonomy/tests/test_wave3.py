from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from autonomy.adapters.claude_code.adapter import build_claude_task
from autonomy.adapters.cursor.adapter import build_cursor_task
from autonomy.adapters.orchestrator import AdapterOrchestrator
from autonomy.compiler.graph_compiler import compile_graph
from autonomy.errors import PolicyViolation
from autonomy.io import load_json
from autonomy.models import CampaignAuthorization, DeploymentManifest
from autonomy.runtime.engine import AutonomyRuntime
from autonomy.validation.golden_trace import GoldenTraceValidator
from autonomy.validation.simulator import PipelineSimulator

ROOT = Path(__file__).resolve().parents[2]


class Wave3Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.database = Path(self.tempdir.name) / "runtime.sqlite3"
        self.campaign_payload = load_json(ROOT / "autonomy/examples/w7-campaign.json")
        self.campaign_payload["base_state"]["commit_sha"] = "abc1234"
        self.deployment_payload = load_json(ROOT / "autonomy/examples/w7-deployment.json")
        self.actions_payload = load_json(ROOT / "autonomy/examples/w7-actions.json")
        campaign = CampaignAuthorization.from_dict(self.campaign_payload)
        deployment = DeploymentManifest.from_dict(self.deployment_payload)
        self.graph_payload = compile_graph(
            campaign,
            deployment,
            self.actions_payload,
        ).to_dict()
        self.runtime = AutonomyRuntime.from_repository(
            repository_root=ROOT,
            database_path=self.database,
            signing_key="wave3-test-key",
        )
        self.runtime.bootstrap(
            campaign_payload=self.campaign_payload,
            deployment_payload=self.deployment_payload,
            graph_payload=self.graph_payload,
        )
        # Override in-memory only — do not mutate tracked policy files (pytest-xdist safe).
        requirements = load_json(ROOT / "autonomy/policies/adapter-requirements.json")
        requirements["allow_missing_executable_in_test"] = True
        self.orchestrator = AdapterOrchestrator(
            self.runtime,
            repository_root=ROOT,
            requirements=requirements,
        )
        self.campaign_id = self.campaign_payload["campaign_id"]

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def register_cursor(self) -> str:
        result = self.orchestrator.register(
            load_json(ROOT / "autonomy/examples/adapters/cursor.json")
        )
        self.assertEqual(result["conformance"]["status"], "PASS")
        return result["session_id"]

    def test_nonconformant_adapter_cannot_deploy(self) -> None:
        config = load_json(ROOT / "autonomy/examples/adapters/cursor.json")
        config["direct_tool_access"] = True
        result = self.orchestrator.register(config)
        self.assertEqual(result["conformance"]["status"], "FAIL")
        with self.assertRaises(PolicyViolation):
            self.orchestrator.request_agent(
                session_id=result["session_id"],
                campaign_id=self.campaign_id,
                agent_id="cursor-agent-1",
            )

    def test_conformant_adapter_receives_contract(self) -> None:
        session_id = self.register_cursor()
        deployment = self.orchestrator.request_agent(
            session_id=session_id,
            campaign_id=self.campaign_id,
            agent_id="cursor-agent-1",
            action_id="campaign-coordinator",
        )
        contract = deployment["agent_contract"]
        self.assertEqual(contract["action_id"], "campaign-coordinator")
        self.assertTrue(contract["runtime_protocol"]["mediate_every_tool_call"])
        self.assertFalse(contract["mutation"])

    def test_ack_requires_exact_capability_set(self) -> None:
        session_id = self.register_cursor()
        deployment = self.orchestrator.request_agent(
            session_id=session_id,
            campaign_id=self.campaign_id,
            agent_id="cursor-agent-1",
            action_id="campaign-coordinator",
        )
        with self.assertRaises(PolicyViolation):
            self.orchestrator.acknowledge_agent(
                session_id=session_id,
                lease_id=deployment["lease"]["lease_id"],
                agent_id="cursor-agent-1",
                accepted_capabilities=["campaign.inspect"],
            )

    def test_tool_use_requires_matching_adapter_session(self) -> None:
        first_session = self.register_cursor()
        second_session = self.register_cursor()
        deployment = self.orchestrator.request_agent(
            session_id=first_session,
            campaign_id=self.campaign_id,
            agent_id="cursor-agent-1",
            action_id="campaign-coordinator",
        )
        capabilities = deployment["required_acknowledgment"]["capabilities"]
        self.orchestrator.acknowledge_agent(
            session_id=first_session,
            lease_id=deployment["lease"]["lease_id"],
            agent_id="cursor-agent-1",
            accepted_capabilities=capabilities,
        )
        with self.assertRaises(PolicyViolation):
            self.orchestrator.authorize_tool(
                session_id=second_session,
                lease_id=deployment["lease"]["lease_id"],
                agent_id="cursor-agent-1",
                capability="campaign.inspect",
            )

    def test_cursor_task_carries_enforcement_context(self) -> None:
        session_id = self.register_cursor()
        deployment = self.orchestrator.request_agent(
            session_id=session_id,
            campaign_id=self.campaign_id,
            agent_id="cursor-agent-1",
            action_id="campaign-coordinator",
        )
        task = build_cursor_task(deployment)
        self.assertEqual(task["environment"]["L9_DIRECT_TOOL_ACCESS"], "0")
        self.assertEqual(task["environment"]["L9_AUTONOMOUS_MERGE"], "0")
        self.assertIn(deployment["lease"]["lease_id"], task["prompt"])

    def test_claude_task_requires_fail_closed_hooks(self) -> None:
        session_id = self.register_cursor()
        deployment = self.orchestrator.request_agent(
            session_id=session_id,
            campaign_id=self.campaign_id,
            agent_id="claude-agent-1",
            action_id="campaign-coordinator",
        )
        task = build_claude_task(deployment)
        self.assertTrue(task["hooks"]["pre_tool_use"]["required"])
        self.assertTrue(task["hooks"]["pre_tool_use"]["fail_closed"])

    def test_simulator_produces_deterministic_waves(self) -> None:
        result = PipelineSimulator(
            self.graph_payload,
            load_json(ROOT / "autonomy/policies/resource-classes.json"),
        ).simulate()
        self.assertGreater(result["steps"], 0)
        self.assertEqual(result["unreachable_actions"], [])
        first_wave_ids = {action["action_id"] for action in result["waves"][0]["actions"]}
        self.assertIn("campaign-coordinator", first_wave_ids)

    def test_golden_trace_rejects_autonomous_merge(self) -> None:
        specification = load_json(ROOT / "autonomy/tests/golden/task046-happy-path.spec.json")
        events = [
            {"event_type": "campaign_bootstrapped"},
            {"event_type": "lease_issued"},
            {"event_type": "agent_deployed"},
            {"event_type": "lease_acknowledged"},
            {"event_type": "autonomous_merge"},
            {"event_type": "lease_released"},
            {"event_type": "artifact_accepted"},
        ]
        errors = GoldenTraceValidator().validate(
            events=events,
            specification=specification,
        )
        self.assertTrue(any("Forbidden event" in error for error in errors))

    def test_global_merge_capability_still_denied(self) -> None:
        session_id = self.register_cursor()
        deployment = self.orchestrator.request_agent(
            session_id=session_id,
            campaign_id=self.campaign_id,
            agent_id="cursor-agent-1",
            action_id="campaign-coordinator",
        )
        capabilities = deployment["required_acknowledgment"]["capabilities"]
        self.orchestrator.acknowledge_agent(
            session_id=session_id,
            lease_id=deployment["lease"]["lease_id"],
            agent_id="cursor-agent-1",
            accepted_capabilities=capabilities,
        )
        decision = self.orchestrator.authorize_tool(
            session_id=session_id,
            lease_id=deployment["lease"]["lease_id"],
            agent_id="cursor-agent-1",
            capability="pr.merge",
        )
        self.assertFalse(decision["allowed"])

    def test_status_reports_adapter_and_receipts(self) -> None:
        session_id = self.register_cursor()
        status = self.orchestrator.status(
            session_id=session_id,
            campaign_id=self.campaign_id,
        )
        self.assertEqual(status["adapter"]["conformance"], "PASS")
        self.assertTrue(status["receipt_chain"]["valid"])


if __name__ == "__main__":
    unittest.main()

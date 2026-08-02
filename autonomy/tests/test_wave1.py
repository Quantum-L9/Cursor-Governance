from __future__ import annotations

import json
import unittest
from pathlib import Path

from autonomy.compiler.graph_compiler import compile_graph
from autonomy.errors import (
    ContractError,
    GraphCompilationError,
    GraphValidationError,
)
from autonomy.io import load_json
from autonomy.models import CampaignAuthorization, DeploymentManifest
from autonomy.validation.graph_linter import GraphLinter

ROOT = Path(__file__).resolve().parents[2]


class Wave1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.campaign_payload = load_json(ROOT / "autonomy/examples/w7-campaign.json")
        self.campaign_payload["base_state"]["commit_sha"] = "abc1234"
        self.deployment_payload = load_json(ROOT / "autonomy/examples/w7-deployment.json")
        self.action_payload = load_json(ROOT / "autonomy/examples/w7-actions.json")
        self.role_policy = load_json(ROOT / "autonomy/policies/role-capabilities.json")
        self.pipeline_policy = load_json(ROOT / "autonomy/policies/pipeline-invariants.json")

    def compile(self):
        campaign = CampaignAuthorization.from_dict(self.campaign_payload)
        deployment = DeploymentManifest.from_dict(self.deployment_payload)
        return (
            compile_graph(
                campaign,
                deployment,
                self.action_payload,
            ),
            deployment,
        )

    def test_compiles_valid_w7_graph(self) -> None:
        compiled, _ = self.compile()
        self.assertTrue(compiled.graph_id.startswith("graph-"))
        self.assertEqual(
            len(compiled.topological_order),
            len(compiled.actions),
        )
        self.assertLess(
            compiled.topological_order.index("synthesize-m0"),
            compiled.topological_order.index("execute-m0"),
        )
        self.assertLess(
            compiled.topological_order.index("execute-m0"),
            compiled.topological_order.index("verify-m0-scope"),
        )

    def test_linter_accepts_valid_graph(self) -> None:
        compiled, deployment = self.compile()
        linter = GraphLinter(
            deployment=deployment,
            role_policy=self.role_policy,
            pipeline_policy=self.pipeline_policy,
        )
        linter.assert_valid(compiled.to_dict())

    def test_cycle_is_rejected(self) -> None:
        payload = json.loads(json.dumps(self.action_payload))
        first = payload["actions"][0]
        first["depends_on"] = ["evidence-writer"]
        campaign = CampaignAuthorization.from_dict(self.campaign_payload)
        deployment = DeploymentManifest.from_dict(self.deployment_payload)
        with self.assertRaises(GraphCompilationError):
            compile_graph(campaign, deployment, payload)

    def test_executor_without_synthesis_is_rejected(self) -> None:
        payload = json.loads(json.dumps(self.action_payload))
        for action in payload["actions"]:
            if action["id"] == "execute-m0":
                action["depends_on"] = ["ro-m0-gap"]
        campaign = CampaignAuthorization.from_dict(self.campaign_payload)
        deployment = DeploymentManifest.from_dict(self.deployment_payload)
        compiled = compile_graph(campaign, deployment, payload)
        linter = GraphLinter(
            deployment=deployment,
            role_policy=self.role_policy,
            pipeline_policy=self.pipeline_policy,
        )
        with self.assertRaises(GraphValidationError):
            linter.assert_valid(compiled.to_dict())

    def test_autonomous_merge_is_rejected(self) -> None:
        payload = json.loads(json.dumps(self.action_payload))
        for action in payload["actions"]:
            if action["id"] == "execute-m0":
                action["metadata"]["operations"].append("merge_pull_request")
        campaign = CampaignAuthorization.from_dict(self.campaign_payload)
        deployment = DeploymentManifest.from_dict(self.deployment_payload)
        compiled = compile_graph(campaign, deployment, payload)
        linter = GraphLinter(
            deployment=deployment,
            role_policy=self.role_policy,
            pipeline_policy=self.pipeline_policy,
        )
        findings = linter.lint(compiled.to_dict())
        self.assertTrue(any(item.code == "PIPE-008" for item in findings))

    def test_campaign_requires_resolved_base_sha(self) -> None:
        payload = json.loads(json.dumps(self.campaign_payload))
        payload["base_state"]["commit_sha"] = ""
        with self.assertRaises(ContractError):
            CampaignAuthorization.from_dict(payload)

    def test_campaign_cannot_allow_force_push(self) -> None:
        payload = json.loads(json.dumps(self.campaign_payload))
        payload["scope"]["allowed_operations"].append("force_push")
        with self.assertRaises(ContractError):
            CampaignAuthorization.from_dict(payload)


if __name__ == "__main__":
    unittest.main()

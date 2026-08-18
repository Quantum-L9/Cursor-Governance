"""Compile-time and adapter-level guards for wide (swarm) execution.

The scheduler can only saturate what the compiler emits, so these tests pin the
graph-width metrics, the fail-closed lints that keep independent work from being
compiled into a chain or into the wrong resource pool, and the adapter's
background-execution surface.
"""

from __future__ import annotations

import unittest

from autonomy.adapters.claude_code.adapter import BACKGROUND_ROLES, build_claude_task
from autonomy.compiler.graph_compiler import compile_graph
from autonomy.errors import GraphValidationError
from autonomy.models import CampaignAuthorization, DeploymentManifest
from autonomy.policy_loader import load_example, load_policy
from autonomy.tests.swarm_fixtures import (
    actions_payload,
    campaign_payload,
    deployment_payload,
)
from autonomy.validation.graph_linter import GraphLinter


class CompilerWidthTests(unittest.TestCase):
    def compile(self, actions):
        return compile_graph(
            CampaignAuthorization.from_dict(campaign_payload()),
            DeploymentManifest.from_dict(deployment_payload()),
            actions,
        )

    def test_independent_work_compiles_into_one_wide_layer(self) -> None:
        compiled = self.compile(actions_payload(recon=32))
        self.assertEqual(compiled.max_parallel_width, 32)
        self.assertEqual(compiled.serial_depth, 2)
        self.assertEqual(len(compiled.parallel_layers[1]), 32)

    def test_width_metrics_are_published_on_the_compiled_graph(self) -> None:
        payload = self.compile(actions_payload(recon=4)).to_dict()
        self.assertEqual(payload["max_parallel_width"], 4)
        self.assertEqual(payload["serial_depth"], 2)
        self.assertEqual(len(payload["parallel_layers"]), 2)

    def test_mutation_fanout_stays_wide(self) -> None:
        compiled = self.compile(actions_payload(mutations=8))
        # coordinate -> synthesize -> 8 mutations -> 8 verifications -> review
        self.assertEqual(compiled.max_parallel_width, 8)
        self.assertEqual(compiled.serial_depth, 5)


class SerializationLintTests(unittest.TestCase):
    def lint(self, actions):
        deployment = DeploymentManifest.from_dict(deployment_payload())
        compiled = compile_graph(
            CampaignAuthorization.from_dict(campaign_payload()),
            deployment,
            actions,
        )
        linter = GraphLinter(
            deployment=deployment,
            role_policy=load_policy("role-capabilities"),
            pipeline_policy=load_policy("pipeline-invariants"),
            resource_policy=load_policy("resource-classes"),
        )
        return linter, compiled.to_dict()

    @staticmethod
    def chain_recon(actions):
        """Rewrite a recon fan-out into a recon -> recon -> recon chain."""

        recon_ids = [item["id"] for item in actions["actions"] if item["role"] == "recon"]
        for previous, current in zip(recon_ids, recon_ids[1:], strict=False):
            for item in actions["actions"]:
                if item["id"] == current:
                    item["depends_on"] = [previous]
        return actions

    def test_serialized_siblings_are_rejected(self) -> None:
        linter, graph = self.lint(self.chain_recon(actions_payload(recon=4)))
        with self.assertRaises(GraphValidationError):
            linter.assert_valid(graph)
        codes = {finding.code for finding in linter.lint(graph)}
        self.assertIn("PIPE-SERIAL-SIBLING", codes)

    def test_declared_justification_permits_a_serial_edge(self) -> None:
        actions = self.chain_recon(actions_payload(recon=4))
        for item in actions["actions"]:
            if item["role"] == "recon":
                item.setdefault("metadata", {})["serialization_justification"] = (
                    "each pass refines the previous recon's findings"
                )
        linter, graph = self.lint(actions)
        linter.assert_valid(graph)

    def test_conflicting_claims_justify_a_serial_edge(self) -> None:
        actions = self.chain_recon(actions_payload(recon=2))
        for item in actions["actions"]:
            if item["role"] == "recon":
                item["claims"] = [
                    {
                        "key": "repo:contended",
                        "mode": "read",
                        "exclusive": True,
                    }
                ]
        linter, graph = self.lint(actions)
        linter.assert_valid(graph)

    def test_human_gate_may_sequence_behind_its_own_role(self) -> None:
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
        linter, graph = self.lint(actions)
        linter.assert_valid(graph)


class ResourceClassLintTests(unittest.TestCase):
    def lint(self, actions):
        deployment = DeploymentManifest.from_dict(deployment_payload())
        compiled = compile_graph(
            CampaignAuthorization.from_dict(campaign_payload()),
            deployment,
            actions,
        )
        linter = GraphLinter(
            deployment=deployment,
            role_policy=load_policy("role-capabilities"),
            pipeline_policy=load_policy("pipeline-invariants"),
            resource_policy=load_policy("resource-classes"),
        )
        return linter.lint(compiled.to_dict())

    def test_undeclared_resource_class_fails_closed(self) -> None:
        actions = actions_payload(recon=1)
        for item in actions["actions"]:
            if item["role"] == "recon":
                item["resource_class"] = "not_a_class"
        findings = self.lint(actions)
        self.assertIn(
            "PIPE-RESOURCE-CLASS-UNKNOWN",
            {finding.code for finding in findings if finding.severity == "ERROR"},
        )

    def test_mutation_in_read_class_fails_closed(self) -> None:
        actions = actions_payload(mutations=1)
        for item in actions["actions"]:
            if item["mutation"]:
                item["resource_class"] = "repository_read"
        findings = self.lint(actions)
        self.assertIn(
            "PIPE-RESOURCE-CLASS-MUTATION",
            {finding.code for finding in findings if finding.severity == "ERROR"},
        )

    def test_read_action_in_mutation_class_warns_only(self) -> None:
        actions = actions_payload(recon=1)
        for item in actions["actions"]:
            if item["role"] == "recon":
                item["resource_class"] = "repository_mutation"
        findings = self.lint(actions)
        warnings = {finding.code for finding in findings if finding.severity == "WARNING"}
        errors = {finding.code for finding in findings if finding.severity == "ERROR"}
        self.assertIn("PIPE-RESOURCE-CLASS-WIDTH", warnings)
        self.assertNotIn("PIPE-RESOURCE-CLASS-WIDTH", errors)

    def test_example_graph_spreads_across_split_pools(self) -> None:
        # Recon, context compilation, synthesis, verification and review each
        # own a pool, so one family saturating cannot starve another.
        declared = load_policy("resource-classes")["classes"]
        used = {item["resource_class"] for item in load_example("w7-actions.json")["actions"]}
        self.assertTrue(used <= set(declared), msg=f"undeclared classes: {used - set(declared)}")
        self.assertTrue(
            {
                "repository_recon",
                "context_compile",
                "synthesis",
                "verification",
                "review",
            }
            <= used
        )


class BackgroundRoleTests(unittest.TestCase):
    def deployment(self, role: str) -> dict:
        return {
            "agent_contract": {
                "campaign_id": "campaign",
                "graph_id": "graph",
                "action_id": "action",
                "agent_id": "agent",
                "lease_id": "lease",
                "capability_id": "capability",
                "base_sha": "abc1234",
                "role": role,
                "objective": "objective",
                "completion": {
                    "artifact_kind": "ReconReport",
                    "required_fields": ["base_sha"],
                },
            },
            "lease": {"lease_id": "lease"},
        }

    def test_every_parallel_safe_analytical_role_runs_in_background(self) -> None:
        expected = {
            "context_compiler",
            "recon",
            "synthesis",
            "verifier",
            "reviewer",
            "failure_classifier",
            "poller",
            "sentinel",
            "evidence_writer",
        }
        self.assertEqual(set(BACKGROUND_ROLES), expected)
        for role in expected:
            self.assertTrue(
                build_claude_task(self.deployment(role))["run_in_background"],
                msg=f"{role} must not be serialized in the foreground",
            )

    def test_mutation_roles_stay_in_the_foreground(self) -> None:
        for role in ("executor", "remediator"):
            self.assertFalse(build_claude_task(self.deployment(role))["run_in_background"])

    def test_background_execution_never_relaxes_enforcement(self) -> None:
        task = build_claude_task(self.deployment("recon"))
        self.assertEqual(task["environment"]["L9_DIRECT_TOOL_ACCESS"], "0")
        self.assertEqual(task["environment"]["L9_AUTONOMOUS_MERGE"], "0")
        self.assertTrue(task["hooks"]["pre_tool_use"]["fail_closed"])
        self.assertTrue(task["hooks"]["post_tool_use"]["required"])


if __name__ == "__main__":
    unittest.main()

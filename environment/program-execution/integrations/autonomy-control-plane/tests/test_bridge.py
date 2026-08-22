from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from adapters.common.imports import load_module

_HERE = Path(__file__).resolve().parents[1]
_PE_ROOT = _HERE.parents[1]
_GOV_ROOT = _PE_ROOT.parents[1]
if str(_GOV_ROOT) not in sys.path:
    sys.path.insert(0, str(_GOV_ROOT))
if str(_PE_ROOT) not in sys.path:
    sys.path.insert(0, str(_PE_ROOT))

from autonomy.compiler.graph_compiler import compile_graph
from autonomy.models import CampaignAuthorization, DeploymentManifest
from autonomy.validation.graph_linter import GraphLinter
from autonomy.policy_loader import load_policy


def _mapper():
    return load_module(_HERE / "contract_mapper.py", "pes_test_autonomy_contract_mapper")


def _grant():
    return load_module(_HERE / "grant.py", "pes_test_autonomy_grant")


def _mutating_contract() -> dict[str, object]:
    return {
        "program_id": "Program A",
        "task_id": "TASK-1",
        "objective": "Edit the declared path",
        "base_sha": "a" * 40,
        "requested_actions": ["inspect", "local_write"],
        "writable_paths": ["docs/result.txt"],
        "contract_digest": "digest-1",
        "program_digest": "program-digest-1",
        "repository_id": "repo-a",
        "branch": "campaign/demo",
        "lease_id": "lease-program-1",
    }


class AutonomyControlPlaneBridgeTests(unittest.TestCase):
    def test_identifiers_are_deterministic(self) -> None:
        module = _mapper()
        first = module.deterministic_ids("Program A", "TASK-1", 2, "cursor-foreground")
        second = module.deterministic_ids("Program A", "TASK-1", 2, "cursor-foreground")
        self.assertEqual(first, second)
        self.assertEqual(first["action_id"], "task-1")

    def test_mapped_campaign_uses_campaign_terminology(self) -> None:
        mapped = _mapper().map_program_contract(
            {"program_id": "Program A", "task_id": "TASK-1", "base_sha": "a" * 40},
            adapter_id="cursor-foreground",
            attempt_number=1,
        )
        campaign = mapped["campaign"]
        self.assertEqual(campaign["campaign_task_id"], "TASK-1")
        self.assertNotIn("program_task_id", campaign)

    def test_mapped_mutation_campaign_is_schema_valid_and_compileable(self) -> None:
        mapped = _mapper().map_program_contract(
            _mutating_contract(),
            adapter_id="cursor-foreground",
            attempt_number=1,
        )
        campaign = CampaignAuthorization.from_dict(mapped["campaign"])
        deployment = DeploymentManifest.from_dict(mapped["deployment"])
        compiled = compile_graph(campaign, deployment, mapped["graph"])
        GraphLinter(
            deployment=deployment,
            role_policy=load_policy("role-capabilities"),
            pipeline_policy=load_policy("pipeline-invariants"),
            resource_policy=load_policy("resource-classes"),
        ).assert_valid(compiled.to_dict())
        self.assertTrue(mapped["mutation"])
        self.assertIn("edit_scoped", campaign.scope["allowed_operations"])
        self.assertIn("commit_local", campaign.scope["allowed_operations"])
        self.assertIn("merge", campaign.scope["forbidden_operations"])
        self.assertNotIn("push_non_force_declared_branch", campaign.scope["allowed_operations"])

    def test_inspect_only_grant_does_not_authorize_write(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            grant = _grant().grant_task_mutation(
                _GOV_ROOT,
                workspace,
                {
                    "program_id": "Program A",
                    "task_id": "TASK-1",
                    "objective": "Inspect only",
                    "base_sha": "a" * 40,
                    "requested_actions": ["inspect"],
                    "writable_paths": [],
                    "contract_digest": "digest-ro",
                    "repository_id": "repo-a",
                },
                attempt_number=1,
            )
            self.assertFalse(grant["mutation"])
            self.assertEqual(grant["authorized"], ["repository.read"])
            self.assertNotIn("repository.write_scoped", grant["authorized"])
            self.assertNotIn("git.commit_local", grant["authorized"])

    def test_grant_issues_local_write_and_commit_not_merge(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            grant = _grant().grant_task_mutation(
                _GOV_ROOT,
                workspace,
                _mutating_contract(),
                attempt_number=1,
            )
            self.assertTrue(grant["mutation"])
            self.assertEqual(grant["authorized"], ["repository.write_scoped", "git.commit_local"])
            self.assertIn("merge", grant["forbidden"])
            self.assertFalse(grant["owns_program_state"])
            packet = (workspace / "runtime" / "autonomy-packet.json").read_text(encoding="utf-8")
            self.assertIn("pes-program-a-task-1-attempt-1", packet)
            self.assertTrue((workspace / "runtime" / "autonomy-grant.json").is_file())

    def test_bridge_only_reuses_existing_files(self) -> None:
        source = (_HERE / "bridge.py").read_text(encoding="utf-8")
        self.assertIn("autonomy/adapters/orchestrator.py", source)
        self.assertNotIn("class LeaseManager", source)


if __name__ == "__main__":
    unittest.main()

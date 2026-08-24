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

from autonomy.compiler.graph_compiler import compile_graph  # noqa: E402
from autonomy.models import CampaignAuthorization, DeploymentManifest  # noqa: E402
from autonomy.policy_loader import load_policy  # noqa: E402
from autonomy.validation.graph_linter import GraphLinter  # noqa: E402


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
            packet_path = _grant().grant_receipt_path(workspace, "TASK-1", 1, kind="packet")
            packet = packet_path.read_text(encoding="utf-8")
            self.assertIn("pes-program-a-task-1-attempt-1", packet)
            grant_path = _grant().grant_receipt_path(workspace, "TASK-1", 1, kind="grant")
            self.assertTrue(grant_path.is_file())
            self.assertEqual(grant["task_id"], "TASK-1")
            self.assertEqual(grant["attempt_number"], 1)
            # Concurrent PE tasks must not overwrite each other's authority
            # evidence through a mutable workspace-global receipt pair.
            self.assertFalse((workspace / "runtime" / "autonomy-grant.json").exists())
            self.assertFalse((workspace / "runtime" / "autonomy-packet.json").exists())

    def test_two_parallel_grants_do_not_overwrite_each_other(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            contract_a = _mutating_contract()
            contract_b = dict(_mutating_contract())
            contract_b["task_id"] = "TASK-2"
            contract_b["writable_paths"] = ["docs/other.md"]
            grant_a = _grant().grant_task_mutation(
                _GOV_ROOT, workspace, contract_a, attempt_number=1
            )
            grant_b = _grant().grant_task_mutation(
                _GOV_ROOT, workspace, contract_b, attempt_number=1
            )
            path_a = _grant().grant_receipt_path(workspace, "TASK-1", 1, kind="grant")
            path_b = _grant().grant_receipt_path(workspace, "TASK-2", 1, kind="grant")
            self.assertNotEqual(path_a, path_b)
            self.assertTrue(path_a.is_file())
            self.assertTrue(path_b.is_file())
            self.assertNotEqual(grant_a["lease_id"], grant_b["lease_id"])
            self.assertNotEqual(grant_a["campaign_id"], grant_b["campaign_id"])

    def test_revoked_grant_lease_cannot_stay_active(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            grant = _grant().grant_task_mutation(
                _GOV_ROOT, workspace, _mutating_contract(), attempt_number=1
            )
            result = _grant().revoke_task_grant(grant, reason="child failed before completion")
            self.assertTrue(result["revoked"])
            from autonomy.runtime.engine import AutonomyRuntime

            runtime = AutonomyRuntime.from_repository(
                repository_root=_GOV_ROOT,
                database_path=Path(grant["runtime_database"]),
            )
            lease = runtime.leases.get(grant["lease_id"])
            self.assertEqual(lease.status.value, "REVOKED")
            # Idempotent: revoking again is a no-op, not an error.
            _grant().revoke_task_grant(grant, reason="replay")

    def test_bridge_only_reuses_existing_files(self) -> None:
        source = (_HERE / "bridge.py").read_text(encoding="utf-8")
        self.assertIn("autonomy/adapters/orchestrator.py", source)
        self.assertNotIn("class LeaseManager", source)


if __name__ == "__main__":
    unittest.main()

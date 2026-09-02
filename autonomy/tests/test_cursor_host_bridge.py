"""Native Cursor host admission bridge (PHASE-2).

Root Autonomy authority must exist before a native Task launches; the host
``tool_use_id`` and ``subagent_id`` are then bound deterministically to that
persisted authority through an opaque single-use admission token. Nothing is
ever inferred from Task prose, and every uncorrelated or conflicting host
event is denied.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from autonomy.adapters.cursor.host_bridge import (
    CursorHostBridge,
    host_bind_pre_tool_use,
    host_bind_subagent_start,
)
from autonomy.adapters.cursor.mint_admission import mint_admission
from autonomy.adapters.orchestrator import AdapterOrchestrator
from autonomy.compiler.graph_compiler import compile_graph
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
from environment.agents.deployment.receipts import DeploymentNotReady

ROOT = Path(__file__).resolve().parents[2]


def _roles_digest(repo_root: Path) -> str:
    path = repo_root / "environment/agents/cursor-subagents/CURSOR_SUBAGENT_ROLES.yaml"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_cursor_receipt(
    workspace: Path,
    *,
    status: str = receipt_lib.STATUS_READY,
    digest: str | None = None,
    corrupt: bool = False,
) -> Path:
    workspace_id = receipt_lib.workspace_id_for(workspace)
    body = {
        "schema": receipt_lib.RECEIPT_SCHEMA,
        "status": status,
        "source_manifest_digest": digest if digest is not None else _roles_digest(ROOT),
        "surface": "cursor",
    }
    path = receipt_lib.write_deployment_receipt(body, surface="cursor", workspace_id=workspace_id)
    if corrupt:
        data = json.loads(path.read_text(encoding="utf-8"))
        data["receipt_digest"] = "0" * 64
        path.write_text(json.dumps(data) + "\n", encoding="utf-8")
    return path


class HostBridgeTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self._prev_runtime = os.environ.get("L9_RUNTIME_ROOT")
        self.l9_runtime = Path(self.tempdir.name) / "l9runtime"
        os.environ["L9_RUNTIME_ROOT"] = str(self.l9_runtime)
        self.addCleanup(self._restore_runtime)
        _write_cursor_receipt(ROOT)
        self.database = Path(self.tempdir.name) / "runtime.sqlite3"
        campaign_data = campaign_payload()
        deployment_data = deployment_payload()
        actions_data = actions_payload(recon=2)
        compiled = compile_graph(
            CampaignAuthorization.from_dict(campaign_data),
            DeploymentManifest.from_dict(deployment_data),
            actions_data,
        )
        self.runtime = AutonomyRuntime.from_repository(
            repository_root=ROOT,
            database_path=self.database,
            signing_key="host-bridge-test",
        )
        self.runtime.bootstrap(
            campaign_payload=campaign_data,
            deployment_payload=deployment_data,
            graph_payload=compiled.to_dict(),
        )
        # Coordinator completes so recon actions become READY for admission.
        self.runtime.store.set_action_status(
            campaign_id=CAMPAIGN_ID, action_id="coordinate", status="COMPLETED"
        )
        self.runtime.scheduler.refresh_readiness(CAMPAIGN_ID)
        requirements = load_policy("adapter-requirements")
        self.orchestrator = AdapterOrchestrator(
            self.runtime, repository_root=ROOT, requirements=requirements
        )
        self.bridge = CursorHostBridge(self.runtime, self.orchestrator)

    def _restore_runtime(self) -> None:
        if self._prev_runtime is None:
            os.environ.pop("L9_RUNTIME_ROOT", None)
        else:
            os.environ["L9_RUNTIME_ROOT"] = self._prev_runtime

    def _admission(self, agent_id: str = "cursor-child-1") -> dict:
        return self.bridge.create_admission(
            campaign_id=CAMPAIGN_ID,
            agent_id=agent_id,
            adapter_config=load_example("adapters/cursor.json"),
        )

    def _expire(self, token: str) -> None:
        with self.runtime.store.transaction() as connection:
            connection.execute(
                "UPDATE cursor_host_admissions SET expires_at='2000-01-01T00:00:00Z' "
                "WHERE admission_token=?",
                (token,),
            )


class AdmissionCreationTests(HostBridgeTestCase):
    def test_admission_requires_preexisting_root_authority(self) -> None:
        admission = self._admission()
        self.assertTrue(admission["admission_token"].startswith("admission-"))
        self.assertIn("L9_ADMISSION_TOKEN=", admission["prompt_marker"])
        lease = self.runtime.leases.get(admission["lease"]["lease_id"])
        self.assertEqual(lease.status.value, "ACTIVE")
        self.assertIn("agent_contract", admission)
        # The adapter session is durable in the root runtime database.
        session = self.orchestrator.require_conformant_session(admission["session_id"])
        self.assertEqual(session["status"], "PASS")


class MintAdmissionHelperTests(HostBridgeTestCase):
    def test_mint_helper_calls_create_admission(self) -> None:
        admission = mint_admission(
            campaign_id=CAMPAIGN_ID,
            agent_id="cursor-child-1",
            repository_root=ROOT,
            database_path=self.database,
            adapter_config=load_example("adapters/cursor.json"),
        )
        self.assertTrue(admission["admission_token"].startswith("admission-"))
        self.assertTrue(admission["prompt_marker"].startswith("L9_ADMISSION_TOKEN="))

    def test_mint_helper_is_not_a_second_store(self) -> None:
        text = (
            Path(__file__).resolve().parents[1] / "adapters" / "cursor" / "mint_admission.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("CREATE TABLE", text)
        self.assertIn("create_admission", text)


class PreToolUseBindTests(HostBridgeTestCase):
    def test_unknown_admission_token_denied(self) -> None:
        decision = host_bind_pre_tool_use(self.database, "admission-nope", "tu-1")
        self.assertFalse(decision["allowed"])
        self.assertIn("unknown admission token", decision["reason"])

    def test_expired_admission_token_denied(self) -> None:
        admission = self._admission()
        self._expire(admission["admission_token"])
        decision = host_bind_pre_tool_use(self.database, admission["admission_token"], "tu-1")
        self.assertFalse(decision["allowed"])
        self.assertIn("expired", decision["reason"])

    def test_valid_root_admission_allowed_and_single_use(self) -> None:
        admission = self._admission()
        token = admission["admission_token"]
        decision = host_bind_pre_tool_use(self.database, token, "tu-1")
        self.assertTrue(decision["allowed"])
        self.assertEqual(decision["admission"]["tool_use_id"], "tu-1")
        # Idempotent redelivery of the same binding is allowed…
        replay = host_bind_pre_tool_use(self.database, token, "tu-1")
        self.assertTrue(replay["allowed"])
        self.assertTrue(replay.get("idempotent"))
        # …but conflicting reuse for a different tool use is denied.
        conflict = host_bind_pre_tool_use(self.database, token, "tu-2")
        self.assertFalse(conflict["allowed"])

    def test_missing_root_lease_denied(self) -> None:
        admission = self._admission()
        self.runtime.leases.revoke(
            lease_id=admission["lease"]["lease_id"],
            reason="test revocation",
            actor="test",
        )
        decision = host_bind_pre_tool_use(self.database, admission["admission_token"], "tu-1")
        self.assertFalse(decision["allowed"])
        self.assertIn("not ACTIVE", decision["reason"])


class SubagentStartBindTests(HostBridgeTestCase):
    def test_start_requires_exact_tool_call_id_match(self) -> None:
        admission = self._admission()
        host_bind_pre_tool_use(self.database, admission["admission_token"], "tu-1")
        wrong = host_bind_subagent_start(
            self.database, tool_call_id="tu-other", subagent_id="sub-1"
        )
        self.assertFalse(wrong["allowed"])
        right = host_bind_subagent_start(
            self.database,
            tool_call_id="tu-1",
            subagent_id="sub-1",
            parent_conversation_id="conv-9",
            model="cursor-fast",
            is_parallel_worker=True,
            git_branch="agent/task",
        )
        self.assertTrue(right["allowed"])
        persisted = right["admission"]
        self.assertEqual(persisted["subagent_id"], "sub-1")
        self.assertEqual(persisted["parent_conversation_id"], "conv-9")
        self.assertEqual(persisted["model"], "cursor-fast")
        self.assertTrue(persisted["is_parallel_worker"])
        self.assertEqual(persisted["git_branch"], "agent/task")

    def test_conflicting_subagent_reuse_denied(self) -> None:
        admission = self._admission()
        host_bind_pre_tool_use(self.database, admission["admission_token"], "tu-1")
        host_bind_subagent_start(self.database, tool_call_id="tu-1", subagent_id="sub-1")
        conflict = host_bind_subagent_start(self.database, tool_call_id="tu-1", subagent_id="sub-2")
        self.assertFalse(conflict["allowed"])
        replay = host_bind_subagent_start(self.database, tool_call_id="tu-1", subagent_id="sub-1")
        self.assertTrue(replay["allowed"])
        self.assertTrue(replay.get("idempotent"))

    def test_start_without_pre_tool_use_binding_denied(self) -> None:
        self._admission()
        decision = host_bind_subagent_start(
            self.database, tool_call_id="tu-unbound", subagent_id="sub-1"
        )
        self.assertFalse(decision["allowed"])

    def test_revoked_lease_cannot_start(self) -> None:
        admission = self._admission()
        host_bind_pre_tool_use(self.database, admission["admission_token"], "tu-1")
        self.runtime.leases.revoke(
            lease_id=admission["lease"]["lease_id"],
            reason="test revocation",
            actor="test",
        )
        decision = host_bind_subagent_start(self.database, tool_call_id="tu-1", subagent_id="sub-1")
        self.assertFalse(decision["allowed"])


class DeploymentReadinessAdmissionTests(HostBridgeTestCase):
    def test_ready_receipt_admits(self) -> None:
        admission = self._admission()
        self.assertTrue(admission["admission_token"].startswith("admission-"))
        self.assertNotIn("allowed", admission)

    def test_missing_receipt_denies(self) -> None:
        path = receipt_lib.receipt_path(
            surface="cursor", workspace_id=receipt_lib.workspace_id_for(ROOT)
        )
        path.unlink()
        with self.assertRaises(DeploymentNotReady) as caught:
            self._admission()
        self.assertIn("missing", str(caught.exception))

    def test_blocked_receipt_denies(self) -> None:
        _write_cursor_receipt(ROOT, status="BLOCKED")
        with self.assertRaises(DeploymentNotReady) as caught:
            self._admission()
        self.assertIn("BLOCKED", str(caught.exception))

    def test_stale_digest_denies(self) -> None:
        _write_cursor_receipt(ROOT, digest="0" * 64)
        with self.assertRaises(DeploymentNotReady) as caught:
            self._admission()
        self.assertIn("stale", str(caught.exception))

    def test_invalid_digest_denies(self) -> None:
        _write_cursor_receipt(ROOT, corrupt=True)
        with self.assertRaises(DeploymentNotReady) as caught:
            self._admission()
        self.assertIn("digest invalid", str(caught.exception))


if __name__ == "__main__":
    unittest.main()

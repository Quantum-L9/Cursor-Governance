from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from adapters.common.imports import load_module

_HERE = Path(__file__).resolve().parents[1]
_PE_ROOT = _HERE.parents[1]
_GOV_ROOT = _PE_ROOT.parents[1]
# APPEND, never insert(0): see peer_execution.imports.pe_script.
if str(_GOV_ROOT) not in sys.path:
    sys.path.append(str(_GOV_ROOT))
# APPEND, never insert(0): Program Execution needs its own PE-exclusive
# packages here, but `scripts` is a top-level name it SHARES with the
# repository root. Prepending would hand PE's `scripts/` that name for the
# whole process. See peer_execution.imports.pe_script.
if str(_PE_ROOT) not in sys.path:
    sys.path.append(str(_PE_ROOT))

from autonomy.compiler.graph_compiler import compile_graph  # noqa: E402
from autonomy.models import CampaignAuthorization, DeploymentManifest  # noqa: E402
from autonomy.policy_loader import load_policy  # noqa: E402
from autonomy.validation.graph_linter import GraphLinter  # noqa: E402


def _mapper():
    return load_module(_HERE / "contract_mapper.py", "pes_test_autonomy_contract_mapper")


def _grant():
    return load_module(_HERE / "grant.py", "pes_test_autonomy_grant")


def _program_authority():
    return load_module(_HERE / "program_authority.py", "pes_test_program_authority")


def _state_db(workspace: Path):
    """A canonical PEC state database, built by the Controller's own StateDB.

    Hand-rolling the schema here would let this fixture drift from the state
    the verifier actually reads in production.
    """
    scripts = _PE_ROOT / "core/program-execution-controller-template/scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from pec.state import StateDB  # noqa: PLC0415

    return StateDB(workspace / "runtime" / "state.sqlite")


def _bind_program_parent(
    workspace: Path,
    contract: dict[str, object],
    *,
    runtime_state: str = "CONTRACTED",
    expires_in_seconds: int = 900,
    active: bool = True,
) -> None:
    """Give a workspace the canonical Program parent the contract claims."""
    task_id = str(contract["task_id"])
    database = _state_db(workspace)
    try:
        database.upsert_task(
            {
                "id": task_id,
                "title": task_id,
                "wave_id": "WAVE-1",
                "workstream_id": "WS-1",
                "target_id": "TARGET-A",
                "repository_id": str(contract.get("repository_id") or "repo-a"),
                "execution_kind": "code_change",
                "objective": str(contract.get("objective") or "Execute"),
                "risk_tier": "low",
                "definition_status": "defined",
            }
        )
        now = datetime.now(tz=UTC)
        database.create_lease(
            {
                "lease_id": str(contract["lease_id"]),
                "task_id": task_id,
                "repository_id": str(contract.get("repository_id") or "repo-a"),
                "holder": "make-campaign",
                "base_sha": str(contract["base_sha"]),
                "branch": str(contract.get("branch") or "HEAD"),
                "worktree": str(workspace / "worktrees" / task_id),
                "contract_digest": str(contract["contract_digest"]),
                "issued_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "expires_at": (now + timedelta(seconds=expires_in_seconds)).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
            }
        )
        database.update_task(task_id, lease_id=str(contract["lease_id"]))
        database.transition_task(task_id, "ELIGIBLE")
        database.transition_task(task_id, "LEASED")
        database.transition_task(task_id, "PREPARED")
        if runtime_state != "PREPARED":
            database.transition_task(task_id, runtime_state)
        if not active:
            database.release_lease(str(contract["lease_id"]))
    finally:
        database.close()


def _commit_only_contract() -> dict[str, object]:
    """commit without local_write: incoherent, and must gain nothing.

    Nothing upstream should produce this -- the campaign compiler refuses it.
    That is exactly why the authority owner has to refuse it too: a lower
    authority owner that depends on its caller staying honest is not
    fail-closed, it has merely not been asked dishonestly yet.
    """
    contract = _mutating_contract()
    contract["requested_actions"] = ["inspect", "commit"]
    contract["task_id"] = "TASK-3"
    contract["contract_digest"] = "digest-commit-only"
    return contract


def _write_only_contract() -> dict[str, object]:
    """Mutation without commit: the shape that used to receive commit anyway."""
    contract = _mutating_contract()
    contract["requested_actions"] = ["inspect", "local_write"]
    contract["task_id"] = "TASK-2"
    contract["contract_digest"] = "digest-write-only"
    return contract


def _mutating_contract() -> dict[str, object]:
    return {
        "program_id": "Program A",
        "task_id": "TASK-1",
        "objective": "Edit the declared path",
        "base_sha": "a" * 40,
        "requested_actions": ["inspect", "local_write", "commit"],
        "writable_paths": ["docs/result.txt"],
        "contract_digest": "digest-1",
        "program_digest": "program-digest-1",
        "repository_id": "repo-a",
        "branch": "campaign/demo",
        "lease_id": "lease-program-1",
    }


def _execution_request_payload() -> dict[str, object]:
    """A minimal valid canonical execution request, sidecar-free."""
    from peer_execution.permissions import resolve_permission_profile  # noqa: PLC0415

    delegated = ("inspect", "local_write")
    return {
        "schema": "l9.peer-execution.request.v1",
        "execution_id": "claude-code-direct-0001",
        "task_id": "TASK-1",
        "program_lock_digest": "sha256:" + "c" * 64,
        "rendered_contract_digest": "sha256:" + "d" * 64,
        "worktree_ref": "/tmp/worktrees/TASK-1",
        "objective": "Edit the declared path",
        "context_manifest_ref": "/tmp/contexts/TASK-1.json",
        "context_manifest_digest": "sha256:" + "e" * 64,
        "rendered_contract": {"task_id": "TASK-1"},
        "worker_instruction": "Do the declared work",
        "permission_profile_ref": "repo-local-bounded",
        "permission_profile": resolve_permission_profile("repo-local-bounded", delegated),
        "inference_budget": {"max_turns": 12},
        "timeout_budget": {"dispatch_seconds": 1800, "poll_seconds": 30},
        "requested_capabilities": list(delegated),
        "telemetry_context": {"task_id": "TASK-1"},
        "agent_ref": "claude-code",
        "surface": "claude-cli",
        "provider_ref": "claude-code-direct",
        "execution_profile_ref": "worker-default",
    }


class AutonomyControlPlaneBridgeTests(unittest.TestCase):
    def test_missing_base_sha_is_refused_not_zero_filled(self) -> None:
        """A zero SHA passes the hex check and binds a lease to a commit no tree has."""
        mapper = _mapper()
        contract = _mutating_contract()
        contract.pop("base_sha")
        with self.assertRaises(mapper.ContractActionError) as ctx:
            mapper.map_program_contract(contract, adapter_id="claude-code", attempt_number=1)
        self.assertIn("base_sha", str(ctx.exception))

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

    def test_local_write_without_commit_does_not_allow_commit_local(self) -> None:
        """`mutation` is not one permission: commit is never inferred from write."""
        campaign = _mapper().map_program_contract(
            _write_only_contract(),
            adapter_id="cursor-foreground",
            attempt_number=1,
        )["campaign"]
        allowed = campaign["scope"]["allowed_operations"]
        self.assertIn("edit_scoped", allowed)
        self.assertNotIn("commit_local", allowed)

    def test_local_write_without_commit_grant_withholds_commit_capability(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            grant = _grant().grant_task_mutation(
                _GOV_ROOT,
                Path(raw),
                _write_only_contract(),
                attempt_number=1,
            )
            self.assertTrue(grant["mutation"])
            self.assertEqual(grant["authorized"], ["repository.write_scoped"])
            self.assertNotIn("git.commit_local", grant["authorized"])

    def test_commit_without_local_write_is_refused_by_the_mapper(self) -> None:
        """It must not fall through to the write set and pick up edit_scoped."""
        module = _mapper()
        with self.assertRaises(module.ContractActionError) as ctx:
            module.allowed_operations(_commit_only_contract())
        self.assertIn("local_write", str(ctx.exception))

        with self.assertRaises(module.ContractActionError):
            module.map_program_contract(
                _commit_only_contract(),
                adapter_id="cursor-foreground",
                attempt_number=1,
            )

    def test_commit_without_local_write_yields_no_usable_grant(self) -> None:
        """The authority owner refuses before any lease is issued."""
        # Bind the module once: `_grant()` loads a fresh copy per call, so a
        # second load would raise a different AutonomyGrantError class object.
        grant_mod = _grant()
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            with self.assertRaises(grant_mod.AutonomyGrantError) as ctx:
                grant_mod.grant_task_mutation(
                    _GOV_ROOT,
                    workspace,
                    _commit_only_contract(),
                    attempt_number=1,
                )
            self.assertIn("local_write", str(ctx.exception))
            # No receipt, so no record of authority it never held.
            self.assertFalse(
                grant_mod.grant_receipt_path(workspace, "TASK-3", 1, kind="grant").exists()
            )
            self.assertFalse((workspace / "runtime" / "autonomy-grants").exists())

    def test_write_capability_traces_only_to_local_write(self) -> None:
        """Each capability comes from the one action that justifies it."""
        executor_authority = _grant()._executor_authority

        caps, authorized = executor_authority(_write_only_contract())
        self.assertIn("repository.write_scoped", caps)
        self.assertNotIn("git.commit_local", caps)
        self.assertEqual(authorized, ("repository.write_scoped",))

        caps, authorized = executor_authority(_mutating_contract())
        self.assertIn("repository.write_scoped", caps)
        self.assertIn("git.commit_local", caps)
        self.assertEqual(authorized, ("repository.write_scoped", "git.commit_local"))

    def test_read_probe_targets_the_declared_scope_not_an_invented_file(self) -> None:
        """A read grant with no declared path probes the whole-worktree scope."""
        module = _grant()
        contract = {"writable_paths": [], "requested_actions": ["inspect"]}
        self.assertEqual(module._resource_for_capability(contract, "repository.read"), "**")
        declared = {"writable_paths": ["docs/result.txt"], "requested_actions": ["inspect"]}
        self.assertEqual(
            module._resource_for_capability(declared, "repository.read"), "docs/result.txt"
        )
        self.assertIsNone(module._resource_for_capability(contract, "shell.execute"))

    def test_write_probe_without_a_declared_path_is_refused(self) -> None:
        """`README.md` used to be invented as the resource of every write probe."""
        module = _grant()
        contract = {"writable_paths": [], "requested_actions": ["local_write"]}
        with self.assertRaises(module.AutonomyGrantError) as ctx:
            module._resource_for_capability(contract, "repository.write_scoped")
        self.assertIn("WRITABLE_PATHS_REQUIRED", str(ctx.exception))

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


class ProgramBoundRootAuthorityTests(unittest.TestCase):
    """PR-001: narrowed Program authority, carried by a conformant root session."""

    def test_grant_registers_a_conformant_canonical_adapter_session(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            contract = _mutating_contract()
            _bind_program_parent(workspace, contract)
            grant = _grant().grant_task_mutation(
                _GOV_ROOT,
                workspace,
                contract,
                attempt_number=1,
                agent_ref="claude-code",
                surface="claude-cli",
            )
            self.assertEqual(
                grant["peer_binding"],
                {
                    "agent_ref": "claude-code",
                    "surface": "claude-cli",
                    "provider_ref": "claude-code-direct",
                    "execution_profile_ref": "worker-default",
                    "autonomy_provider_ref": "root-autonomy-control-plane",
                },
            )
            session_id = grant["adapter_session_id"]
            self.assertTrue(session_id.startswith("adapter-session-"))
            connection = sqlite3.connect(grant["runtime_database"])
            try:
                connection.row_factory = sqlite3.Row
                session = connection.execute(
                    "SELECT * FROM adapter_sessions WHERE session_id = ?", (session_id,)
                ).fetchone()
                lease = connection.execute(
                    "SELECT * FROM leases WHERE lease_id = ?", (grant["lease_id"],)
                ).fetchone()
            finally:
                connection.close()
            self.assertIsNotNone(session)
            self.assertEqual(session["status"], "PASS")
            self.assertEqual(session["peer_ref"], "claude-code")
            self.assertEqual(session["surface"], "claude-cli")
            # The live orchestrator authorizes a tool only against the session
            # the lease itself was issued under.
            metadata = json.loads(lease["metadata_json"])
            self.assertEqual(metadata["adapter_session_id"], session_id)

    def test_subordinate_lease_binds_program_parent_and_cannot_outlive_it(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            contract = _mutating_contract()
            _bind_program_parent(workspace, contract, expires_in_seconds=120)
            grant = _grant().grant_task_mutation(_GOV_ROOT, workspace, contract, attempt_number=1)
            parent = grant["program_parent"]
            self.assertTrue(parent["bound"])
            self.assertEqual(parent["lease_id"], "lease-program-1")
            self.assertEqual(parent["runtime_state"], "CONTRACTED")
            connection = sqlite3.connect(grant["runtime_database"])
            try:
                connection.row_factory = sqlite3.Row
                lease = connection.execute(
                    "SELECT * FROM leases WHERE lease_id = ?", (grant["lease_id"],)
                ).fetchone()
            finally:
                connection.close()
            metadata = json.loads(lease["metadata_json"])
            self.assertEqual(metadata["program_lease_id"], "lease-program-1")
            self.assertEqual(metadata["program_task_id"], "TASK-1")
            self.assertEqual(metadata["program_contract_digest"], "digest-1")
            self.assertIs(metadata["owns_program_state"], False)
            # 120s of parent authority can never become 900s of child authority.
            issued = datetime.strptime(lease["issued_at"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(
                tzinfo=UTC
            )
            expires = datetime.strptime(lease["expires_at"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(
                tzinfo=UTC
            )
            self.assertLessEqual((expires - issued).total_seconds(), 120)
            parent_expiry = datetime.strptime(parent["expires_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=UTC
            )
            self.assertLessEqual(expires, parent_expiry)

    def test_expired_or_released_program_parent_refuses_the_grant(self) -> None:
        for label, kwargs in (
            ("expired", {"expires_in_seconds": -60}),
            ("released", {"active": False}),
            ("terminal", {"runtime_state": "FAILED"}),
        ):
            with self.subTest(parent=label), tempfile.TemporaryDirectory() as raw:
                workspace = Path(raw)
                contract = _mutating_contract()
                _bind_program_parent(workspace, contract, **kwargs)
                module = _grant()
                with self.assertRaises(module.AutonomyGrantError) as caught:
                    module.grant_task_mutation(_GOV_ROOT, workspace, contract, attempt_number=1)
                self.assertIn("PROGRAM_PARENT", str(caught.exception))

    def test_program_parent_lease_drift_refuses_the_grant(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            contract = _mutating_contract()
            _bind_program_parent(workspace, contract)
            drifted = dict(contract)
            drifted["lease_id"] = "lease-program-2"
            module = _grant()
            with self.assertRaises(module.AutonomyGrantError) as caught:
                module.grant_task_mutation(_GOV_ROOT, workspace, drifted, attempt_number=1)
            self.assertIn("PROGRAM_PARENT_LEASE_DRIFT", str(caught.exception))

    def test_verifier_never_mutates_program_state(self) -> None:
        """The parent read is evidence, not a transition."""
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            contract = _mutating_contract()
            _bind_program_parent(workspace, contract)
            state = workspace / "runtime" / "state.sqlite"
            before = state.read_bytes()
            verifier = _program_authority().ProgramAuthorityVerifier(workspace)
            parent = verifier.require_live_parent(contract)
            self.assertTrue(parent.bound)
            self.assertEqual(state.read_bytes(), before)

    def test_local_write_without_commit_never_acquires_commit_capability(self) -> None:
        """DG-001: the lease accepts the action-specific set, not the role set."""
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            contract = _write_only_contract()
            contract["lease_id"] = "lease-program-2"
            _bind_program_parent(workspace, contract)
            grant = _grant().grant_task_mutation(
                _GOV_ROOT,
                workspace,
                contract,
                attempt_number=1,
                agent_ref="claude-code",
                surface="claude-cli",
            )
            self.assertNotIn("git.commit_local", grant["authorized"])
            self.assertNotIn("git.commit_local", grant["autonomy_authority"]["capabilities"])
            connection = sqlite3.connect(grant["runtime_database"])
            try:
                connection.row_factory = sqlite3.Row
                lease = connection.execute(
                    "SELECT * FROM leases WHERE lease_id = ?", (grant["lease_id"],)
                ).fetchone()
            finally:
                connection.close()
            accepted = json.loads(lease["metadata_json"])["accepted_capabilities"]
            self.assertNotIn("git.commit_local", accepted)
            # The executor *role* does grant it; the acknowledgment is what
            # narrows the lease, so acknowledging the role set would re-inflate.
            from autonomy.policy_loader import load_policy  # noqa: PLC0415

            role = load_policy("role-capabilities")["roles"]["executor"]["capabilities"]
            self.assertIn("git.commit_local", role)

    def test_authority_round_trips_beside_an_unchanged_rendered_contract(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            contract = _mutating_contract()
            _bind_program_parent(workspace, contract)
            grant = _grant().grant_task_mutation(_GOV_ROOT, workspace, contract, attempt_number=1)
            authority = grant["autonomy_authority"]
            self.assertEqual(authority["schema"], "l9.program-execution.autonomy-authority.v1")
            self.assertIs(authority["owns_program_state"], False)
            self.assertNotIn("rendered_contract", authority)
            self.assertNotIn("rendered_contract_digest", authority)

            from peer_execution.provider import CanonicalExecutionRequest  # noqa: PLC0415

            base = _execution_request_payload()
            without = CanonicalExecutionRequest.from_dict(base)
            with_authority = CanonicalExecutionRequest.from_dict(
                {**base, "autonomy_authority": authority}
            )
            self.assertIsNone(without.autonomy_authority)
            self.assertEqual(with_authority.autonomy_authority, authority)
            # Carrying authority never changes contract identity.
            self.assertEqual(
                with_authority.rendered_contract_digest, without.rendered_contract_digest
            )
            self.assertEqual(with_authority.rendered_contract, without.rendered_contract)
            round_tripped = CanonicalExecutionRequest.from_dict(with_authority.to_dict())
            self.assertEqual(round_tripped.autonomy_authority, authority)

    def test_sidecar_for_another_task_is_refused(self) -> None:
        from peer_execution.provider import CanonicalExecutionRequest  # noqa: PLC0415

        base = _execution_request_payload()
        foreign = {
            "schema": "l9.program-execution.autonomy-authority.v1",
            "owns_program_state": False,
            "task_id": "TASK-OTHER",
            "adapter_session_id": "adapter-session-x",
            "lease_id": "lease-x",
            "agent_id": "agent-x",
            "runtime_database": "/tmp/runtime.sqlite3",
        }
        with self.assertRaises(ValueError):
            CanonicalExecutionRequest.from_dict({**base, "autonomy_authority": foreign})
        with self.assertRaises(ValueError):
            CanonicalExecutionRequest.from_dict(
                {
                    **base,
                    "autonomy_authority": {
                        **foreign,
                        "task_id": base["task_id"],
                        "rendered_contract_digest": "sha256:" + "b" * 64,
                    },
                }
            )


class SubordinateLifecycleTests(unittest.TestCase):
    """PR-002: the subordinate lease terminalizes; it never owns the verdict."""

    def _granted(self, workspace: Path, contract: dict[str, object] | None = None):
        contract = contract or _mutating_contract()
        _bind_program_parent(workspace, contract)
        module = _grant()
        grant = module.grant_task_mutation(_GOV_ROOT, workspace, contract, attempt_number=1)
        return module, grant

    def _lease_row(self, grant: dict[str, object]):
        connection = sqlite3.connect(str(grant["runtime_database"]))
        try:
            connection.row_factory = sqlite3.Row
            return connection.execute(
                "SELECT * FROM leases WHERE lease_id = ?", (grant["lease_id"],)
            ).fetchone()
        finally:
            connection.close()

    def test_success_submits_a_result_that_releases_lease_and_claims(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            module, grant = self._granted(workspace)
            result = module.submit_task_result(
                grant,
                changed_files=["docs/result.txt"],
                candidate_sha=None,
                contract_digest="digest-1",
            )
            self.assertTrue(result["submitted"])
            self.assertEqual(result["lease_status"], "RELEASED")
            connection = sqlite3.connect(str(grant["runtime_database"]))
            try:
                connection.row_factory = sqlite3.Row
                claims = connection.execute(
                    "SELECT status FROM claims WHERE lease_id = ?", (grant["lease_id"],)
                ).fetchall()
                artifact = connection.execute(
                    "SELECT kind, status FROM artifacts WHERE artifact_id = ?",
                    (result["artifact_id"],),
                ).fetchone()
            finally:
                connection.close()
            self.assertEqual(artifact["kind"], "ExecutionResult")
            self.assertEqual(artifact["status"], "VALID")
            self.assertTrue(claims, "the executor lease held no claims to release")
            for claim in claims:
                self.assertNotEqual(claim["status"], "HELD")

    def test_root_support_never_completes_program_truth(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            module, grant = self._granted(workspace)
            state_before = (workspace / "runtime" / "state.sqlite").read_bytes()
            module.submit_task_result(
                grant,
                changed_files=["docs/result.txt"],
                candidate_sha=None,
                contract_digest="digest-1",
            )
            self.assertIs(grant["owns_program_state"], False)
            self.assertEqual(
                (workspace / "runtime" / "state.sqlite").read_bytes(),
                state_before,
                msg="root autonomy wrote to canonical Program state",
            )

    def test_controller_rejection_invalidates_root_support(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            module, grant = self._granted(workspace)
            submitted = module.submit_task_result(
                grant,
                changed_files=["docs/result.txt"],
                candidate_sha=None,
                contract_digest="digest-1",
            )
            outcome = module.invalidate_task_support(
                grant,
                artifact_id=submitted["artifact_id"],
                reason="controller verdict 'FAILED_LOCAL'",
            )
            self.assertTrue(outcome["invalidated"])
            connection = sqlite3.connect(str(grant["runtime_database"]))
            try:
                connection.row_factory = sqlite3.Row
                artifact = connection.execute(
                    "SELECT status, invalidation_reason FROM artifacts WHERE artifact_id = ?",
                    (submitted["artifact_id"],),
                ).fetchone()
            finally:
                connection.close()
            self.assertEqual(artifact["status"], "INVALID")
            self.assertIn("FAILED_LOCAL", artifact["invalidation_reason"])

    def test_failure_revokes_the_subordinate_lease(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            module, grant = self._granted(workspace)
            module.revoke_task_grant(grant, reason="provider window failed")
            self.assertEqual(self._lease_row(grant)["status"], "REVOKED")

    def test_decision_coverage_names_every_unmediated_path(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            module, grant = self._granted(workspace)
            # The grant probed the declared writable path; nothing else.
            self.assertEqual(module.authorized_resources(grant), {"docs/result.txt"})
            self.assertEqual(
                module.unmediated_changed_paths(
                    grant, ["docs/result.txt", "ops/secrets/leak.env", "AGENTS.md"]
                ),
                ["AGENTS.md", "docs/result.txt", "ops/secrets/leak.env"],
            )

    def test_a_grant_probe_is_not_an_effect_authorization(self) -> None:
        """Holding the capability is not the same as having authorized a write.

        The probe this module takes while issuing the lease is a real allowed
        `repository.write_scoped` decision on the task's first writable path.
        Counting it as mediation is what let a provider write that exact path
        with no hook in the loop and still show full coverage, so coverage asks
        only for `effect`-phase decisions -- of which a freshly issued grant has
        none. The live effect path is proved end to end in
        `environment/program-execution/tests/hardening/test_autonomy_enforcement_e2e.py`.
        """
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            module, grant = self._granted(workspace)
            probes = module.lease_decisions(
                grant,
                capability="repository.write_scoped",
                phase=module.AUTHORIZATION_PHASE_GRANT_PROBE,
            )
            self.assertEqual([row["resource"] for row in probes], ["docs/result.txt"])
            self.assertEqual(
                module.authorized_resources(grant, phase=module.AUTHORIZATION_PHASE_EFFECT),
                set(),
            )
            self.assertEqual(
                module.unmediated_changed_paths(grant, ["docs/result.txt"]),
                ["docs/result.txt"],
            )

    def test_lease_decisions_are_scoped_to_this_lease(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            module, grant_a = self._granted(workspace)
            other = _mutating_contract()
            other["task_id"] = "TASK-2"
            other["lease_id"] = "lease-program-2"
            other["writable_paths"] = ["docs/other.md"]
            other["contract_digest"] = "digest-2"
            _bind_program_parent(workspace, other)
            grant_b = module.grant_task_mutation(_GOV_ROOT, workspace, other, attempt_number=1)
            self.assertEqual(module.authorized_resources(grant_b), {"docs/other.md"})
            self.assertNotIn("docs/other.md", module.authorized_resources(grant_a))

    def test_local_write_without_commit_stays_without_commit_through_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            contract = _write_only_contract()
            contract["lease_id"] = "lease-program-2"
            module, grant = self._granted(workspace, contract)
            self.assertNotIn("git.commit_local", grant["authorized"])
            module.submit_task_result(
                grant,
                changed_files=["docs/result.txt"],
                candidate_sha=None,
                contract_digest="digest-write-only",
            )
            decisions = module.lease_decisions(grant, allowed_only=False)
            self.assertTrue(decisions)
            self.assertNotIn("git.commit_local", {row["capability"] for row in decisions})


class EffectAuthorizationTests(unittest.TestCase):
    """PR-002: the resource and shell rules the live authorizer enforces."""

    def test_resource_normalization_refuses_every_escape(self) -> None:
        module = _program_authority()
        with tempfile.TemporaryDirectory() as raw:
            worktree = Path(raw) / "worktree"
            (worktree / "docs").mkdir(parents=True)
            (worktree / "docs" / "result.txt").write_text("x", encoding="utf-8")
            self.assertEqual(
                module.normalize_effect_resource(worktree, str(worktree / "docs/result.txt")),
                "docs/result.txt",
            )
            self.assertEqual(
                module.normalize_effect_resource(worktree, "docs/result.txt"),
                "docs/result.txt",
            )
            for resource in ("/etc/passwd", "../escape.txt", str(Path(raw) / "outside.txt"), ""):
                with self.subTest(resource=resource):
                    with self.assertRaises(module.ProgramAuthorityError):
                        module.normalize_effect_resource(worktree, resource)
            linked = Path(raw) / "elsewhere"
            linked.mkdir()
            (worktree / "linked").symlink_to(linked, target_is_directory=True)
            with self.assertRaises(module.ProgramAuthorityError):
                module.normalize_effect_resource(worktree, "linked/result.txt")

    def test_only_canonical_validation_commands_reach_test_run(self) -> None:
        module = _program_authority()
        self.assertEqual(module.canonical_shell_capability("pytest -q"), "test.run")
        for command in ("ls -1 'a' >/dev/null", "git push origin HEAD", "sh -c 'rm -rf /'"):
            with self.subTest(command=command):
                with self.assertRaises(module.ProgramAuthorityError):
                    module.canonical_shell_capability(command)

    def test_a_shell_tool_cannot_infer_test_run_without_validation(self) -> None:
        from autonomy.adapters import tool_hook
        from autonomy.errors import PolicyViolation

        with self.assertRaises(PolicyViolation):
            tool_hook.pre_tool_use(
                tool_name="Bash",
                arguments={"command": "rm -rf /"},
                session_id="adapter-session-x",
                lease_id="lease-x",
                agent_id="agent-x",
                orchestrator=object(),
            )


if __name__ == "__main__":
    unittest.main()

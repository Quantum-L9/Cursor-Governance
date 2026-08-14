from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from peer_execution.context import (
    build_context_manifest,
    load_context_manifest,
    load_execution_context,
    write_context_manifest,
)
from peer_execution.contracts import validate_contract
from peer_execution.core_receipts import verification_receipt
from peer_execution.digests import digest_object
from peer_execution.permissions import resolve_permission_profile
from peer_execution.profiles import load_profile
from peer_execution.provider import (
    CanonicalExecutionRequest,
    CanonicalProviderResult,
    ProviderInvocation,
)
from peer_execution.runner import run_to_terminal
from peer_execution.runtime_store import RuntimeStore
from peer_execution.subprocess_runner import run_argv


class PeerExecutionContractTests(unittest.TestCase):
    def _request(self, **overrides: object) -> CanonicalExecutionRequest:
        manifest = build_context_manifest(self._context_contract())
        permission = resolve_permission_profile("repo-local-bounded", ["inspect"])
        request = CanonicalExecutionRequest(
            execution_id="exec-1",
            task_id="task-1",
            program_lock_digest="a" * 64,
            rendered_contract_digest="b" * 64,
            worktree_ref="/tmp/w",
            objective="do it",
            context_manifest_ref="/tmp/context.json",
            context_manifest_digest=str(manifest["manifest_digest"]),
            rendered_contract=dict(manifest["rendered_contract"]),
            worker_instruction=str(manifest["worker_instruction"]),
            permission_profile_ref="repo-local-bounded",
            permission_profile=permission,
            inference_budget={"max_turns": 12},
            timeout_budget={"dispatch_seconds": 1800, "poll_seconds": 30},
            requested_capabilities=("inspect",),
            telemetry_context={"provider_ref": "synthetic-a"},
            provider_ref="synthetic-a",
            execution_profile_ref="worker-read-only",
        )
        merged = request.model_dump()
        merged.update(overrides)
        return CanonicalExecutionRequest.model_validate(merged)

    @staticmethod
    def _context_contract() -> dict[str, object]:
        return {
            "task_id": "task-1",
            "program_digest": "a" * 64,
            "contract_digest": "b" * 64,
            "base_sha": "c" * 40,
            "worktree": "/tmp/w",
            "objective": "Implement the exact task",
            "writable_paths": ["src/**"],
            "validation_commands": ["python -m pytest"],
            "required_evidence_ids": [],
            "requested_actions": ["inspect"],
        }

    def test_permission_profile_denies_remote_mutation(self) -> None:
        remote_actions = (
            "push",
            "pull_request",
            "merge",
            "publish_or_release",
            "deploy_or_migrate",
            "destructive_change",
            "external_message",
        )
        profile = resolve_permission_profile(
            "repo-local-bounded",
            ["inspect", "local_write", *remote_actions],
        )
        self.assertIn("local_write", profile["allowed_actions"])
        for action in remote_actions:
            self.assertNotIn(action, profile["allowed_actions"])
            self.assertIn(action, profile["denied_actions"])

    def test_context_manifest_is_digest_bound_and_canonicalized(self) -> None:
        manifest = build_context_manifest(self._context_contract())
        self.assertEqual(manifest["program_lock_digest"], "sha256:" + "a" * 64)
        self.assertEqual(manifest["rendered_contract_digest"], "sha256:" + "b" * 64)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "context.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            loaded = load_context_manifest(path)
        self.assertEqual(loaded["task_id"], "task-1")
        self.assertIn("worker_instruction", loaded)

    def test_context_manifest_is_bound_to_execution_request(self) -> None:
        manifest = build_context_manifest(self._context_contract())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "context.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            request = self._request(
                task_id="different-task",
                context_manifest_ref=str(path),
            )
            with self.assertRaisesRegex(ValueError, "task_id"):
                load_execution_context(request)

    def test_context_manifest_accepts_matching_normalized_request(self) -> None:
        manifest = build_context_manifest(self._context_contract())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "context.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            request = self._request(context_manifest_ref=str(path))
            loaded = load_execution_context(request)
        self.assertEqual(loaded["manifest_digest"], manifest["manifest_digest"])

    def test_context_filename_rejects_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "safe"):
                write_context_manifest(tmp, "../escape", self._context_contract())

    def test_context_directory_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp) / "runtime"
            target = Path(tmp) / "outside"
            runtime.mkdir()
            target.mkdir()
            (runtime / "contexts").symlink_to(target, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlinked context directory"):
                write_context_manifest(runtime, "exec-1", self._context_contract())

    def test_context_manifest_conflict_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            write_context_manifest(tmp, "exec-1", self._context_contract())
            changed = self._context_contract()
            changed["objective"] = "different objective"
            with self.assertRaisesRegex(ValueError, "does not match execution contract"):
                write_context_manifest(tmp, "exec-1", changed)

    def test_canonical_rendered_contract_does_not_require_duplicate_ceiling(self) -> None:
        contract: dict[str, object] = {
            "schema": "program-execution-controller.rendered-contract.v2",
            "task_id": "TASK-1",
            "program_digest": "a" * 64,
            "requested_actions": ["inspect"],
            "remote_mutation": "denied",
        }
        contract["contract_digest"] = digest_object(contract).split(":", 1)[1]
        binding = validate_contract(contract)
        self.assertEqual(binding.requested_actions, ("inspect",))
        self.assertEqual(binding.allowed_actions, ("inspect",))

    def test_canonical_rendered_contract_requires_remote_mutation_denied(self) -> None:
        contract: dict[str, object] = {
            "schema": "program-execution-controller.rendered-contract.v2",
            "task_id": "TASK-1",
            "program_digest": "a" * 64,
            "requested_actions": ["inspect"],
            "remote_mutation": "allowed",
        }
        contract["contract_digest"] = digest_object(contract).split(":", 1)[1]
        with self.assertRaisesRegex(Exception, "deny remote mutation"):
            validate_contract(contract)

    def test_empty_verification_gates_cannot_pass(self) -> None:
        contract = {
            "task_id": "TASK-1",
            "program_digest": "a" * 64,
            "contract_digest": "b" * 64,
            "base_sha": "c" * 40,
        }
        receipt = verification_receipt(
            contract,
            candidate_sha=None,
            declared_changed_files=[],
            observed_changed_files=[],
            validations=[],
            gates={},
        )
        self.assertEqual(receipt["verdict"], "FAILED")

    def test_stale_verification_gate_yields_stale_verdict(self) -> None:
        contract = {
            "task_id": "TASK-1",
            "program_digest": "a" * 64,
            "contract_digest": "b" * 64,
            "base_sha": "c" * 40,
        }
        receipt = verification_receipt(
            contract,
            candidate_sha=None,
            declared_changed_files=[],
            observed_changed_files=[],
            validations=[],
            gates={"base_state": "STALE"},
        )
        self.assertEqual(receipt["verdict"], "STALE")

    def test_profile_registry_rejects_retry_ownership_drift(self) -> None:
        subsystem = Path(__file__).resolve().parents[2]
        schema_source = subsystem / "conformance/schemas/execution-profile.schema.json"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = root / "registry"
            schemas = root / "conformance/schemas"
            registry.mkdir()
            schemas.mkdir(parents=True)
            (schemas / "execution-profile.schema.json").write_bytes(schema_source.read_bytes())
            (registry / "EXECUTION_PROFILE_REGISTRY.yaml").write_text(
                "schema: l9.peer-execution.profile-registry.v1\n"
                "schema_version: 1.0.0\n"
                "default_profile_ref: bad\n"
                "profiles:\n"
                "  bad:\n"
                "    permission_profile_ref: repo-local-bounded\n"
                "    context_policy_ref: contract-minimal-v1\n"
                "    inference_budget: {max_turns: 4}\n"
                "    timeout_budget: {dispatch_seconds: 60, poll_seconds: 1}\n"
                "    retry_policy: {max_attempts: 2, backoff_seconds: 0}\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "schema errors"):
                load_profile(root, "bad")

    def test_profile_registry_rejects_unknown_context_policy(self) -> None:
        subsystem = Path(__file__).resolve().parents[2]
        schema_source = subsystem / "conformance/schemas/execution-profile.schema.json"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = root / "registry"
            schemas = root / "conformance/schemas"
            registry.mkdir()
            schemas.mkdir(parents=True)
            (schemas / "execution-profile.schema.json").write_bytes(schema_source.read_bytes())
            (registry / "EXECUTION_PROFILE_REGISTRY.yaml").write_text(
                "schema: l9.peer-execution.profile-registry.v1\n"
                "schema_version: 1.0.0\n"
                "default_profile_ref: future\n"
                "profiles:\n"
                "  future:\n"
                "    permission_profile_ref: read-only\n"
                "    context_policy_ref: future-policy-v2\n"
                "    inference_budget: {max_turns: 4}\n"
                "    timeout_budget: {dispatch_seconds: 60, poll_seconds: 1}\n"
                "    retry_policy: {max_attempts: 1, backoff_seconds: 0}\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "schema errors"):
                load_profile(root, "future")

    def test_runtime_store_rejects_identifier_collisions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = RuntimeStore(tmp)
            store.save("safe-id", {"value": 1})
            with self.assertRaisesRegex(ValueError, "unsafe runtime identifier"):
                store.save("safe/id", {"value": 2})
            self.assertEqual(store.load("safe-id"), {"value": 1})

    def test_subprocess_runner_rejects_argv_type_coercion(self) -> None:
        with self.assertRaisesRegex(ValueError, r"argv\[1\]"):
            run_argv(
                ["python3", None],  # type: ignore[list-item]
                cwd="/tmp",
                timeout_seconds=1,
            )

    def test_subprocess_runner_rejects_nonpositive_timeout(self) -> None:
        with self.assertRaisesRegex(ValueError, "greater than zero"):
            run_argv(["python3", "-V"], cwd="/tmp", timeout_seconds=0)

    def test_terminal_runner_returns_without_polling(self) -> None:
        class Adapter:
            execution_profile = {"timeout_budget": {"dispatch_seconds": 60, "poll_seconds": 1}}

        outcome = run_to_terminal(Adapter(), "dispatch-1", "PASS")
        self.assertEqual(outcome.status, "PASS")
        self.assertFalse(outcome.timed_out)
        self.assertEqual(outcome.status_receipts, ())

    def test_canonical_request_round_trip(self) -> None:
        request = self._request()
        self.assertEqual(
            CanonicalExecutionRequest.from_dict(request.to_dict()),
            request,
        )

    def test_canonical_request_normalizes_digests(self) -> None:
        request = self._request()
        self.assertEqual(request.program_lock_digest, "sha256:" + "a" * 64)
        self.assertEqual(request.rendered_contract_digest, "sha256:" + "b" * 64)

    def test_canonical_request_rejects_invalid_budget(self) -> None:
        with self.assertRaisesRegex((ValueError, ValidationError), "dispatch_seconds"):
            self._request(timeout_budget={"dispatch_seconds": 0, "poll_seconds": 30})

    def test_canonical_request_does_not_coerce_identity_types(self) -> None:
        value = self._request().to_dict()
        value["task_id"] = 123
        with self.assertRaisesRegex(ValueError, "task_id"):
            CanonicalExecutionRequest.from_dict(value)

    def test_canonical_request_requires_provider_binding(self) -> None:
        value = self._request().to_dict()
        value["provider_ref"] = None
        with self.assertRaisesRegex(ValueError, "provider_ref"):
            CanonicalExecutionRequest.from_dict(value)

    def test_canonical_request_requires_at_least_one_capability(self) -> None:
        with self.assertRaisesRegex((ValueError, ValidationError), "requested_capabilities"):
            self._request(requested_capabilities=())

    def test_provider_invocation_status_must_match_result(self) -> None:
        result = CanonicalProviderResult(
            execution_id="exec-1",
            status="FAIL",
            structured_payload={},
        )
        with self.assertRaisesRegex(ValueError, "must equal"):
            ProviderInvocation(status="PASS", result=result)


if __name__ == "__main__":
    unittest.main()

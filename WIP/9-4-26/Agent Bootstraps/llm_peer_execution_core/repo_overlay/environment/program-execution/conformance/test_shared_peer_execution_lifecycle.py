from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from conformance.helpers import valid_contract
from peer_execution.digests import digest_object
from peer_execution.execution import PeerExecutionAdapter
from peer_execution.models import ProbeContext
from peer_execution.provider import (
    CanonicalProviderResult,
    ProviderInvocation,
    ProviderProbe,
)


class _SyntheticProvider:
    def __init__(self, provider_id: str) -> None:
        self.provider_id = provider_id

    def probe(self, context) -> ProviderProbe:
        return ProviderProbe(
            status="PASS",
            evidence=({"type": "synthetic_probe", "provider": self.provider_id},),
            observed_capabilities=("inspect",),
        )

    def invoke(self, request) -> ProviderInvocation:
        result = CanonicalProviderResult(
            execution_id=request.execution_id,
            status="PASS",
            structured_payload={
                "candidate_sha": None,
                "changed_files": [],
                "validation_results": [],
                "residual_unknowns": [],
            },
            provider_metadata={"provider": self.provider_id},
            observed_capabilities=("inspect",),
        )
        return ProviderInvocation(status="PASS", result=result)

    def poll(self, request, state) -> ProviderInvocation:
        return ProviderInvocation(status="PASS", state=state)

    def cancel(self, request, state) -> ProviderInvocation:
        return ProviderInvocation(status="UNSUPPORTED", state=state)


class _WriteCapableProvider(_SyntheticProvider):
    def probe(self, context) -> ProviderProbe:
        return ProviderProbe(
            status="PASS",
            evidence=({"type": "synthetic_probe", "provider": self.provider_id},),
            observed_capabilities=("inspect", "local_write"),
        )


class _IntentInspectingProvider(_SyntheticProvider):
    def __init__(self, provider_id: str) -> None:
        super().__init__(provider_id)
        self.adapter = None
        self.saw_dispatch_intent = False

    def invoke(self, request) -> ProviderInvocation:
        if self.adapter is None:
            raise AssertionError("test provider is not bound to adapter")
        record = self.adapter.runtime.load(request.execution_id)
        self.saw_dispatch_intent = (
            record.get("status") == "DISPATCHING"
            and record.get("canonical_execution_request", {}).get("execution_id")
            == request.execution_id
        )
        if not self.saw_dispatch_intent:
            raise AssertionError("dispatch intent was not persisted before provider invoke")
        return super().invoke(request)


class _OverclaimingProvider(_SyntheticProvider):
    def invoke(self, request) -> ProviderInvocation:
        result = CanonicalProviderResult(
            execution_id=request.execution_id,
            status="PASS",
            structured_payload={
                "candidate_sha": None,
                "changed_files": [],
                "validation_results": [],
                "residual_unknowns": [],
            },
            observed_capabilities=("inspect", "local_write"),
        )
        return ProviderInvocation(status="PASS", result=result)


class SharedPeerExecutionLifecycleTests(unittest.TestCase):
    def _exercise(self, provider_id: str, root: Path) -> dict[str, object]:
        descriptor = {
            "adapter_id": provider_id,
            "adapter_version": "1.0.0",
            "adapter_kind": "worker_host",
            "capabilities": {
                "actions": ["inspect"],
                "cancellation": "unsupported",
            },
            "receipts": {"terminal_core_receipt": "attempt"},
        }
        profile = {
            "profile_ref": "worker-read-only",
            "permission_profile_ref": "read-only",
            "inference_budget": {"max_turns": 4},
            "timeout_budget": {"dispatch_seconds": 60, "poll_seconds": 1},
            "retry_policy": {"max_attempts": 1, "backoff_seconds": 0},
            "context_policy_ref": "contract-minimal-v1",
        }
        runtime = root / "runtime" / "peer-execution"
        contract = valid_contract()
        contract["validation_commands"] = ["python3 -V"]
        contract["worktree"] = str(root)
        contract["attempt_receipt_path"] = str(root / "attempts" / f"{provider_id}.attempt.json")
        contract.pop("contract_digest", None)
        contract["contract_digest"] = digest_object(contract)
        adapter = PeerExecutionAdapter(
            runtime,
            descriptor=descriptor,
            provider=_SyntheticProvider(provider_id),
            execution_profile=profile,
            binding_context={
                "agent_ref": "synthetic-agent",
                "surface": "synthetic-surface",
            },
        )
        adapter.probe(
            ProbeContext(
                repository_root=str(root),
                runtime_root=str(runtime),
                program_lock_digest=contract["program_digest"],
            )
        )
        prepared = adapter.prepare(contract)
        dispatched = adapter.dispatch({"dispatch_id": prepared.dispatch_id})
        self.assertEqual(dispatched.status, "PASS")
        return dict(adapter.collect(str(prepared.dispatch_id)))

    def test_prepare_rejects_unproven_requested_capability(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            descriptor = {
                "adapter_id": "synthetic-a",
                "adapter_version": "1.0.0",
                "adapter_kind": "worker_host",
                "capabilities": {
                    "actions": ["inspect", "local_write"],
                    "cancellation": "unsupported",
                },
                "receipts": {"terminal_core_receipt": "attempt"},
            }
            profile = {
                "profile_ref": "worker-default",
                "permission_profile_ref": "repo-local-bounded",
                "inference_budget": {"max_turns": 4},
                "timeout_budget": {"dispatch_seconds": 60, "poll_seconds": 1},
                "retry_policy": {"max_attempts": 1, "backoff_seconds": 0},
                "context_policy_ref": "contract-minimal-v1",
            }
            contract = valid_contract(requested_actions=["inspect", "local_write"])
            contract["validation_commands"] = ["python3 -V"]
            contract["worktree"] = str(root)
            contract["attempt_receipt_path"] = str(root / "attempts" / "attempt.json")
            contract.pop("contract_digest", None)
            contract["contract_digest"] = digest_object(contract)
            adapter = PeerExecutionAdapter(
                root / "runtime" / "peer-execution",
                descriptor=descriptor,
                provider=_SyntheticProvider("synthetic-a"),
                execution_profile=profile,
            )
            adapter.probe(
                ProbeContext(
                    repository_root=str(root),
                    runtime_root=str(root / "runtime" / "peer-execution"),
                    program_lock_digest=contract["program_digest"],
                )
            )
            with self.assertRaisesRegex(Exception, "not proven"):
                adapter.prepare(contract)


    def test_shared_permission_profile_blocks_provider_independent_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            descriptor = {
                "adapter_id": "synthetic-readonly",
                "adapter_version": "1.0.0",
                "adapter_kind": "worker_host",
                "capabilities": {
                    "actions": ["inspect", "local_write"],
                    "cancellation": "unsupported",
                },
                "receipts": {"terminal_core_receipt": "attempt"},
            }
            profile = {
                "profile_ref": "worker-read-only",
                "permission_profile_ref": "read-only",
                "inference_budget": {"max_turns": 4},
                "timeout_budget": {"dispatch_seconds": 60, "poll_seconds": 1},
                "retry_policy": {"max_attempts": 1, "backoff_seconds": 0},
                "context_policy_ref": "contract-minimal-v1",
            }
            contract = valid_contract(requested_actions=["inspect", "local_write"])
            contract["validation_commands"] = ["python3 -V"]
            contract["worktree"] = str(root)
            contract["attempt_receipt_path"] = str(root / "attempts" / "attempt.json")
            contract.pop("contract_digest", None)
            contract["contract_digest"] = digest_object(contract)
            adapter = PeerExecutionAdapter(
                root / "runtime" / "peer-execution",
                descriptor=descriptor,
                provider=_WriteCapableProvider("synthetic-readonly"),
                execution_profile=profile,
            )
            adapter.probe(
                ProbeContext(
                    repository_root=str(root),
                    runtime_root=str(root / "runtime" / "peer-execution"),
                    program_lock_digest=contract["program_digest"],
                )
            )
            with self.assertRaisesRegex(Exception, "profile denies"):
                adapter.prepare(contract)

    def test_dispatch_intent_is_persisted_before_provider_invocation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            descriptor = {
                "adapter_id": "synthetic-intent",
                "adapter_version": "1.0.0",
                "adapter_kind": "worker_host",
                "capabilities": {"actions": ["inspect"], "cancellation": "unsupported"},
                "receipts": {"terminal_core_receipt": "attempt"},
            }
            profile = {
                "profile_ref": "worker-read-only",
                "permission_profile_ref": "read-only",
                "inference_budget": {"max_turns": 4},
                "timeout_budget": {"dispatch_seconds": 60, "poll_seconds": 1},
                "retry_policy": {"max_attempts": 1, "backoff_seconds": 0},
                "context_policy_ref": "contract-minimal-v1",
            }
            contract = valid_contract(requested_actions=["inspect"])
            contract["validation_commands"] = ["python3 -V"]
            contract["worktree"] = str(root)
            contract["attempt_receipt_path"] = str(root / "attempts" / "attempt.json")
            contract.pop("contract_digest", None)
            contract["contract_digest"] = digest_object(contract)
            provider = _IntentInspectingProvider("synthetic-intent")
            adapter = PeerExecutionAdapter(
                root / "runtime" / "peer-execution",
                descriptor=descriptor,
                provider=provider,
                execution_profile=profile,
            )
            provider.adapter = adapter
            adapter.probe(
                ProbeContext(
                    repository_root=str(root),
                    runtime_root=str(root / "runtime" / "peer-execution"),
                    program_lock_digest=contract["program_digest"],
                )
            )
            prepared = adapter.prepare(contract)
            adapter.dispatch({"dispatch_id": prepared.dispatch_id})
            self.assertTrue(provider.saw_dispatch_intent)

    def test_persisted_request_budget_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            descriptor = {
                "adapter_id": "synthetic-drift",
                "adapter_version": "1.0.0",
                "adapter_kind": "worker_host",
                "capabilities": {"actions": ["inspect"], "cancellation": "unsupported"},
                "receipts": {"terminal_core_receipt": "attempt"},
            }
            profile = {
                "profile_ref": "worker-read-only",
                "permission_profile_ref": "read-only",
                "inference_budget": {"max_turns": 4},
                "timeout_budget": {"dispatch_seconds": 60, "poll_seconds": 1},
                "retry_policy": {"max_attempts": 1, "backoff_seconds": 0},
                "context_policy_ref": "contract-minimal-v1",
            }
            contract = valid_contract(requested_actions=["inspect"])
            contract["validation_commands"] = ["python3 -V"]
            contract["worktree"] = str(root)
            contract["attempt_receipt_path"] = str(root / "attempts" / "attempt.json")
            contract.pop("contract_digest", None)
            contract["contract_digest"] = digest_object(contract)
            adapter = PeerExecutionAdapter(
                root / "runtime" / "peer-execution",
                descriptor=descriptor,
                provider=_SyntheticProvider("synthetic-drift"),
                execution_profile=profile,
            )
            adapter.probe(
                ProbeContext(
                    repository_root=str(root),
                    runtime_root=str(root / "runtime" / "peer-execution"),
                    program_lock_digest=contract["program_digest"],
                )
            )
            prepared = adapter.prepare(contract)
            adapter.dispatch({"dispatch_id": prepared.dispatch_id})
            record = adapter.runtime.load(str(prepared.dispatch_id))
            request = dict(record["canonical_execution_request"])
            timeout = dict(request["timeout_budget"])
            timeout["dispatch_seconds"] = 61
            request["timeout_budget"] = timeout
            record["canonical_execution_request"] = request
            adapter.runtime.save(str(prepared.dispatch_id), record)
            with self.assertRaisesRegex(ValueError, "timeout_budget drift"):
                adapter._request_from_record(record)

    def test_result_cannot_claim_capability_not_proven_by_probe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            descriptor = {
                "adapter_id": "synthetic-overclaim",
                "adapter_version": "1.0.0",
                "adapter_kind": "worker_host",
                "capabilities": {
                    "actions": ["inspect", "local_write"],
                    "cancellation": "unsupported",
                },
                "receipts": {"terminal_core_receipt": "attempt"},
            }
            profile = {
                "profile_ref": "worker-read-only",
                "permission_profile_ref": "read-only",
                "inference_budget": {"max_turns": 4},
                "timeout_budget": {"dispatch_seconds": 60, "poll_seconds": 1},
                "retry_policy": {"max_attempts": 1, "backoff_seconds": 0},
                "context_policy_ref": "contract-minimal-v1",
            }
            contract = valid_contract(requested_actions=["inspect"])
            contract["validation_commands"] = ["python3 -V"]
            contract["worktree"] = str(root)
            contract["attempt_receipt_path"] = str(root / "attempts" / "attempt.json")
            contract.pop("contract_digest", None)
            contract["contract_digest"] = digest_object(contract)
            adapter = PeerExecutionAdapter(
                root / "runtime" / "peer-execution",
                descriptor=descriptor,
                provider=_OverclaimingProvider("synthetic-overclaim"),
                execution_profile=profile,
            )
            adapter.probe(
                ProbeContext(
                    repository_root=str(root),
                    runtime_root=str(root / "runtime" / "peer-execution"),
                    program_lock_digest=contract["program_digest"],
                )
            )
            prepared = adapter.prepare(contract)
            with self.assertRaisesRegex(ValueError, "not proven by probe"):
                adapter.dispatch({"dispatch_id": prepared.dispatch_id})

    def test_two_providers_share_identical_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = self._exercise("synthetic-a", root)
            second = self._exercise("synthetic-b", root)
        self.assertEqual(first["schema"], second["schema"])
        self.assertEqual(first["task_id"], second["task_id"])
        self.assertEqual(first["claimed_status"], second["claimed_status"])
        first_evidence = first["produced_evidence"][0]
        second_evidence = second["produced_evidence"][0]
        self.assertNotEqual(
            first_evidence["provider_metadata"],
            second_evidence["provider_metadata"],
        )


if __name__ == "__main__":
    unittest.main()

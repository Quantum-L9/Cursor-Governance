"""A provider-reported failure reaches the lifecycle receipt as canonical + adapter codes."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from conformance.helpers import PROGRAM_DIGEST, valid_contract
from peer_execution.digests import digest_object
from peer_execution.execution import PeerExecutionAdapter
from peer_execution.imports import pe_script
from peer_execution.models import ProbeContext
from peer_execution.profiles import resolve_profile_for_provider
from peer_execution.provider import CanonicalProviderResult, ProviderInvocation, ProviderProbe

_provider_loader = pe_script("provider_loader")


class _FailingProvider:
    provider_id = "cursor-foreground"

    def probe(self, context) -> ProviderProbe:
        return ProviderProbe(
            status="PASS",
            evidence=({"type": "synthetic_probe"},),
            observed_capabilities=("inspect",),
        )

    def invoke(self, request) -> ProviderInvocation:
        result = CanonicalProviderResult(
            execution_id=request.execution_id,
            status="FAIL",
            structured_payload={
                "candidate_sha": None,
                "changed_files": [],
                "validation_results": [],
                "residual_unknowns": [],
            },
            provider_metadata={"provider": self.provider_id},
            observed_capabilities=("inspect",),
            errors=({"type": "host_error", "message": "exit 1"},),
        )
        return ProviderInvocation(
            status="FAIL", result=result, adapter_error_code="HOST_EXECUTION_FAILED"
        )

    def poll(self, request, state) -> ProviderInvocation:
        return ProviderInvocation(status="PASS", state=state)

    def cancel(self, request, state) -> ProviderInvocation:
        return ProviderInvocation(status="UNSUPPORTED", state=state)


class ErrorTaxonomyTests(unittest.TestCase):
    def test_adapter_code_is_mapped_onto_the_dispatch_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory) / "runtime"
            descriptor = _provider_loader.descriptor_for("cursor-foreground")
            profile = resolve_profile_for_provider(
                _provider_loader.subsystem_root(),
                _provider_loader.repository_root(),
                "cursor-foreground",
                "worker-read-only",
            )
            adapter = PeerExecutionAdapter(
                runtime,
                descriptor=descriptor,
                provider=_FailingProvider(),
                execution_profile=profile,
            )
            adapter.probe(
                ProbeContext(
                    repository_root=str(_provider_loader.repository_root()),
                    runtime_root=str(runtime),
                    program_lock_digest=PROGRAM_DIGEST,
                )
            )
            contract = valid_contract(requested_actions=["inspect"], allowed_actions=["inspect"])
            contract["validation_commands"] = ["python3 -V"]
            contract.pop("contract_digest")
            contract["contract_digest"] = digest_object(contract)
            prepared = adapter.prepare(contract)
            dispatched = adapter.dispatch({"dispatch_id": prepared.dispatch_id})
            self.assertEqual(dispatched.status, "FAIL")
            self.assertEqual(dispatched.adapter_error_code, "HOST_EXECUTION_FAILED")
            self.assertEqual(dispatched.canonical_error_code, "VALIDATION_FAILURE")
            progressed = adapter.status(prepared.dispatch_id)
            self.assertEqual(progressed.canonical_error_code, "VALIDATION_FAILURE")
            record = adapter.runtime.load(prepared.dispatch_id)
            self.assertEqual(record["error_codes"]["adapter"], "HOST_EXECUTION_FAILED")

    def test_a_passing_invocation_may_not_carry_a_code(self) -> None:
        with self.assertRaises(ValueError):
            ProviderInvocation(status="RUNNING", adapter_error_code="HOST_EXECUTION_FAILED")

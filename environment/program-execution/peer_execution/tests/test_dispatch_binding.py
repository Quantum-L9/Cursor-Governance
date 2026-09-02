"""Result application binds to the probe that ADMITTED the dispatch.

A capability receipt's TTL (900 s) gates admission -- prepare and dispatch.
Execution profiles allow a provider window of 1200-1800 s, so a legitimate
invoke can outlive the probe. Re-checking freshness AFTER the provider
returned discarded the result as a capability failure, left the record
DISPATCHING forever, and (because AdapterFailure is not a ValueError) skipped
the FAIL-persisting path entirely.
"""

from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path

from conformance.helpers import PROGRAM_DIGEST, valid_contract
from peer_execution.digests import digest_object
from peer_execution.driver_execution import DriverExecutionAdapter
from peer_execution.execution import PeerExecutionAdapter
from peer_execution.imports import pe_script
from peer_execution.models import CapabilityReceipt, ProbeContext
from peer_execution.profiles import resolve_profile_for_provider
from peer_execution.provider import (
    CanonicalProviderResult,
    ProviderInvocation,
    ProviderProbe,
)

_provider_loader = pe_script("provider_loader")
descriptor_for = _provider_loader.descriptor_for
subsystem_root = _provider_loader.subsystem_root
repository_root = _provider_loader.repository_root


class _ExpiringProvider:
    """A provider whose invoke outlives the probe TTL (simulated)."""

    # Identity must match the descriptor it is bound to; the adapter refuses otherwise.
    provider_id = "cursor-foreground"

    def __init__(self) -> None:
        self.adapter: PeerExecutionAdapter | None = None

    def probe(self, context) -> ProviderProbe:
        return ProviderProbe(
            status="PASS",
            evidence=({"type": "synthetic_probe"},),
            observed_capabilities=("inspect",),
        )

    def invoke(self, request) -> ProviderInvocation:
        assert self.adapter is not None
        # The probe that admitted this dispatch expires while the provider runs.
        stored = self.adapter.runtime.load_capability(self.adapter.adapter_id)
        assert stored is not None
        expired = CapabilityReceipt.create(
            adapter_id=stored["adapter_id"],
            adapter_version=stored["adapter_version"],
            status="PASS",
            capabilities=list(stored["capabilities"]),
            program_lock_digest=stored["program_lock_digest"],
            ttl_seconds=1,
            evidence=[],
            blocked_reason=None,
        )
        time.sleep(1.2)
        assert not expired.is_fresh(), "the simulated probe must have expired"
        self.adapter.runtime.save_capability(self.adapter.adapter_id, expired.to_dict())
        self.adapter._last_probe = None
        return ProviderInvocation(
            status="PASS",
            result=CanonicalProviderResult(
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
            ),
        )

    def poll(self, request, state) -> ProviderInvocation:
        return ProviderInvocation(status="PASS", state=state)

    def cancel(self, request, state) -> ProviderInvocation:
        return ProviderInvocation(status="UNSUPPORTED", state=state)


def _peer_adapter(runtime: Path, provider) -> PeerExecutionAdapter:
    descriptor = descriptor_for("cursor-foreground")
    profile = resolve_profile_for_provider(
        subsystem_root(), repository_root(), "cursor-foreground", "worker-read-only"
    )
    adapter = PeerExecutionAdapter(
        runtime, descriptor=descriptor, provider=provider, execution_profile=profile
    )
    return adapter


def _contract() -> dict:
    contract = valid_contract(requested_actions=["inspect"], allowed_actions=["inspect"])
    # The context manifest requires one command string per entry.
    contract["validation_commands"] = ["python3 -V"]
    contract.pop("contract_digest")
    contract["contract_digest"] = digest_object(contract)
    return contract


class AdmittingProbeTests(unittest.TestCase):
    def test_result_applies_against_the_admitting_probe_after_ttl_expiry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory) / "runtime"
            provider = _ExpiringProvider()
            adapter = _peer_adapter(runtime, provider)
            provider.adapter = adapter
            adapter.probe(
                ProbeContext(
                    repository_root=str(repository_root()),
                    runtime_root=str(runtime),
                    program_lock_digest=PROGRAM_DIGEST,
                )
            )
            prepared = adapter.prepare(_contract())
            record = adapter.runtime.load(prepared.dispatch_id)
            self.assertEqual(record["admitting_probe"]["program_lock_digest"], PROGRAM_DIGEST)
            self.assertIn("inspect", record["admitting_probe"]["capabilities"])
            dispatched = adapter.dispatch({"dispatch_id": prepared.dispatch_id})
            self.assertEqual(dispatched.status, "PASS")
            self.assertEqual(adapter.runtime.load(prepared.dispatch_id)["status"], "PASS")

    def test_unproven_capability_is_a_persisted_fail_not_a_stuck_dispatch(self) -> None:
        class _Overclaiming(_ExpiringProvider):
            def invoke(self, request) -> ProviderInvocation:
                invocation = super().invoke(request)
                assert invocation.result is not None
                overclaimed = CanonicalProviderResult(
                    execution_id=invocation.result.execution_id,
                    status="PASS",
                    structured_payload=invocation.result.structured_payload,
                    provider_metadata=invocation.result.provider_metadata,
                    observed_capabilities=("inspect", "local_write"),
                )
                return ProviderInvocation(status="PASS", result=overclaimed)

        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory) / "runtime"
            provider = _Overclaiming()
            adapter = _peer_adapter(runtime, provider)
            provider.adapter = adapter
            adapter.probe(
                ProbeContext(
                    repository_root=str(repository_root()),
                    runtime_root=str(runtime),
                    program_lock_digest=PROGRAM_DIGEST,
                )
            )
            prepared = adapter.prepare(_contract())
            with self.assertRaises(ValueError):
                adapter.dispatch({"dispatch_id": prepared.dispatch_id})
            record = adapter.runtime.load(prepared.dispatch_id)
            self.assertEqual(record["status"], "FAIL")
            self.assertIn("payload_shape_error", [item["type"] for item in record["evidence"]])
            # The lifecycle chain shows the dispatch phase, not a trail that
            # ends at `prepare PASS` for a dispatch that ran.
            chain = runtime / "lifecycle-receipts.jsonl"
            phases = [
                json.loads(line)["phase"]
                for line in chain.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertIn("dispatch", phases)


class _MalformedDriver:
    provider_id = "ci-generic-shell"

    def probe(self, context):
        return ProviderProbe(status="PASS", evidence=(), observed_capabilities=("verify",))

    def invoke(self, request):
        from peer_execution.driver_execution import DriverInvocation

        return DriverInvocation(status="PASS", payload={"not": "a verification payload"})

    def poll(self, request, state):
        raise AssertionError("not polled")

    def cancel(self, request, state):
        raise AssertionError("not cancelled")


class DriverPayloadShapeTests(unittest.TestCase):
    def test_malformed_terminal_payload_persists_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory) / "runtime"
            adapter = DriverExecutionAdapter(
                runtime, descriptor=descriptor_for("ci-generic-shell"), driver=_MalformedDriver()
            )
            adapter.probe(
                ProbeContext(
                    repository_root=str(repository_root()),
                    runtime_root=str(runtime),
                    program_lock_digest=PROGRAM_DIGEST,
                )
            )
            contract = valid_contract(requested_actions=["verify"], allowed_actions=["verify"])
            contract["candidate_sha"] = "3" * 40
            contract.pop("contract_digest")
            contract["contract_digest"] = digest_object(contract)
            prepared = adapter.prepare(contract)
            with self.assertRaises(ValueError):
                adapter.dispatch({"dispatch_id": prepared.dispatch_id})
            record = adapter.runtime.load(prepared.dispatch_id)
            self.assertEqual(record["status"], "FAIL")
            self.assertIn("payload_shape_error", [item["type"] for item in record["evidence"]])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from .approvals import require_exact_approval
from .base import BaseExecutionAdapter
from .contracts import ContractBinding, validate_contract
from .errors import AdapterFailure, CanonicalErrorCode
from .models import ProbeContext
from .provider import ProviderProbe
from .terminal_receipts import (
    deployment_from_payload,
    remote_action_from_payload,
    verification_from_payload,
)

_DRIVER_STATUSES = frozenset({"PASS", "FAIL", "BLOCKED", "CANCELLED", "RUNNING", "UNSUPPORTED"})
_READ_ONLY_ACTIONS = frozenset({"read_checks", "read_environment", "verify"})


def _required_string(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


@dataclass(frozen=True)
class DriverExecutionRequest:
    dispatch_id: str
    adapter_id: str
    adapter_kind: str
    contract: Mapping[str, Any]
    approval_id: str
    timeout_seconds: int

    def __post_init__(self) -> None:
        for name in ("dispatch_id", "adapter_id", "adapter_kind", "approval_id"):
            _required_string(name, getattr(self, name))
        if not isinstance(self.contract, Mapping):
            raise ValueError("driver contract must be a mapping")
        if isinstance(self.timeout_seconds, bool) or not isinstance(self.timeout_seconds, int):
            raise ValueError("driver timeout_seconds must be an integer")
        if not 1 <= self.timeout_seconds <= 7200:
            raise ValueError("driver timeout_seconds must be between 1 and 7200")


@dataclass(frozen=True)
class DriverInvocation:
    status: str
    state: Mapping[str, Any] = field(default_factory=dict)
    evidence: tuple[dict[str, Any], ...] = ()
    payload: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.status not in _DRIVER_STATUSES:
            raise ValueError(f"unsupported driver status: {self.status}")
        if not isinstance(self.state, Mapping):
            raise ValueError("driver state must be a mapping")
        if not all(isinstance(item, Mapping) for item in self.evidence):
            raise ValueError("driver evidence must contain objects")
        if self.payload is not None and not isinstance(self.payload, Mapping):
            raise ValueError("driver payload must be an object")
        if self.status == "PASS" and self.payload is None:
            raise ValueError("PASS driver invocation requires a payload")
        if self.status in {"RUNNING", "UNSUPPORTED"} and self.payload is not None:
            raise ValueError(f"{self.status} driver invocation must not include a payload")


class ThinExecutionDriver(Protocol):
    provider_id: str

    def probe(self, context: ProbeContext) -> ProviderProbe:
        ...

    def invoke(self, request: DriverExecutionRequest) -> DriverInvocation:
        ...

    def poll(
        self, request: DriverExecutionRequest, state: Mapping[str, Any]
    ) -> DriverInvocation: ...

    def cancel(
        self, request: DriverExecutionRequest, state: Mapping[str, Any]
    ) -> DriverInvocation: ...


class DriverExecutionAdapter(BaseExecutionAdapter):
    """Shared lifecycle owner for verifier, remote-action, and deployment drivers."""

    def __init__(
        self,
        runtime_root: str | Path,
        *,
        descriptor: Mapping[str, Any],
        driver: ThinExecutionDriver,
    ) -> None:
        super().__init__(runtime_root)
        self.descriptor = dict(descriptor)
        self.driver = driver
        self.adapter_id = _required_string("adapter_id", self.descriptor.get("adapter_id"))
        self.adapter_version = _required_string(
            "adapter_version", self.descriptor.get("adapter_version")
        )
        self.adapter_kind = _required_string("adapter_kind", self.descriptor.get("adapter_kind"))
        if driver.provider_id != self.adapter_id:
            raise ValueError("thin execution driver identity mismatch")
        capabilities = self.descriptor.get("capabilities")
        if not isinstance(capabilities, Mapping):
            raise ValueError("adapter capabilities must be an object")
        actions = capabilities.get("actions")
        if not isinstance(actions, list) or not all(isinstance(item, str) for item in actions):
            raise ValueError("adapter capabilities.actions must be an array of strings")
        self.capabilities = tuple(actions)
        self.cancellation = str(capabilities.get("cancellation") or "unsupported")
        self._observed_capabilities: tuple[str, ...] = ()

    def _probe_status(self, context: ProbeContext):
        probe = self.driver.probe(context)
        self._observed_capabilities = tuple(probe.observed_capabilities)
        return probe.status, probe.blocked_reason, [dict(item) for item in probe.evidence]

    def _effective_capabilities(self, context, status, evidence):
        if status != "PASS":
            return ()
        return tuple(sorted(set(self.capabilities) & set(self._observed_capabilities)))

    def prepare(self, contract: Mapping[str, Any]):
        binding = validate_contract(contract)
        probe = self._require_fresh_probe(binding.program_lock_digest)
        unsupported = sorted(set(binding.requested_actions) - set(probe.capabilities))
        if unsupported:
            raise AdapterFailure(
                CanonicalErrorCode.CAPABILITY_UNSUPPORTED,
                f"Execution driver capabilities were not proven: {unsupported}",
                "DRIVER_CAPABILITY_NOT_PROBED",
            )
        return super().prepare(contract)

    def _approval_id(self, binding: ContractBinding) -> str:
        if len(binding.requested_actions) != 1:
            raise AdapterFailure(
                CanonicalErrorCode.VALIDATION_FAILURE,
                "Execution-kind drivers require exactly one requested action",
                "DRIVER_ACTION_CARDINALITY_INVALID",
            )
        action = binding.requested_actions[0]
        if action in _READ_ONLY_ACTIONS:
            return "READ_ONLY"
        return require_exact_approval(binding.raw, action).approval_id

    def _request(self, record: Mapping[str, Any]) -> DriverExecutionRequest:
        binding = validate_contract(record["contract"])
        timeout = binding.raw.get("timeout_seconds", 900)
        if isinstance(timeout, bool) or not isinstance(timeout, int):
            raise ValueError("timeout_seconds must be an integer")
        return DriverExecutionRequest(
            dispatch_id=_required_string("dispatch_id", record.get("dispatch_id")),
            adapter_id=self.adapter_id,
            adapter_kind=self.adapter_kind,
            contract=binding.raw,
            approval_id=self._approval_id(binding),
            timeout_seconds=timeout,
        )

    def _terminal_receipt(
        self,
        request: DriverExecutionRequest,
        invocation: DriverInvocation,
    ) -> dict[str, Any]:
        if invocation.payload is None:
            raise ValueError("terminal driver invocation is missing payload")
        evidence = [dict(item) for item in invocation.evidence]
        if self.adapter_kind == "verifier":
            return verification_from_payload(request.contract, invocation.payload)
        if self.adapter_kind == "remote_action":
            return remote_action_from_payload(
                request.contract,
                invocation.payload,
                approval_id=request.approval_id,
                evidence=evidence,
            )
        if self.adapter_kind == "deployment_record":
            return deployment_from_payload(
                request.contract,
                invocation.payload,
                approval_id=request.approval_id,
            )
        raise ValueError(f"unsupported execution driver kind: {self.adapter_kind}")

    def _apply_invocation(
        self,
        record: dict[str, Any],
        request: DriverExecutionRequest,
        invocation: DriverInvocation,
    ) -> tuple[str, list[dict[str, Any]]]:
        record["driver_state"] = dict(invocation.state)
        evidence = [dict(item) for item in invocation.evidence]
        if invocation.payload is not None:
            record["result"] = self._terminal_receipt(request, invocation)
        return invocation.status, evidence

    def _dispatch_record(self, record: dict[str, Any]):
        request = self._request(record)
        record["status"] = "DISPATCHING"
        self.runtime.save(request.dispatch_id, record)
        try:
            invocation = self.driver.invoke(request)
        except Exception as exc:
            record["status"] = "BLOCKED"
            record["evidence"] = [
                {"type": "driver_invoke_exception", "error_type": type(exc).__name__}
            ]
            self.runtime.save(request.dispatch_id, record)
            raise
        return self._apply_invocation(record, request, invocation)

    def status(self, dispatch_id: str):
        record = self.runtime.load(dispatch_id)
        if record.get("status") == "RUNNING":
            request = self._request(record)
            invocation = self.driver.poll(request, dict(record.get("driver_state") or {}))
            status, evidence = self._apply_invocation(record, request, invocation)
            record["status"] = status
            record["evidence"] = evidence
            self.runtime.save(dispatch_id, record)
        return super().status(dispatch_id)

    def cancel(self, dispatch_id: str):
        record = self.runtime.load(dispatch_id)
        binding = validate_contract(record["contract"])
        if self.cancellation == "unsupported":
            return self._append(
                phase="cancel",
                binding=binding,
                status="UNSUPPORTED",
                dispatch_id=dispatch_id,
                canonical_error_code=CanonicalErrorCode.CANCELLATION_UNSUPPORTED.value,
            )
        request = self._request(record)
        invocation = self.driver.cancel(request, dict(record.get("driver_state") or {}))
        status, evidence = self._apply_invocation(record, request, invocation)
        if status not in {"CANCELLED", "FAIL", "BLOCKED"}:
            status = "UNSUPPORTED"
        record["status"] = status
        record["evidence"] = evidence
        self.runtime.save(dispatch_id, record)
        return self._append(
            phase="cancel",
            binding=binding,
            status=status,
            dispatch_id=dispatch_id,
            evidence=evidence,
            canonical_error_code=(
                CanonicalErrorCode.CANCELLATION_UNSUPPORTED.value
                if status == "UNSUPPORTED"
                else None
            ),
        )

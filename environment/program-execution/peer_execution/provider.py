from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from .digests import normalize_digest
from .models import ProbeContext

_PROVIDER_PROBE_STATUSES = frozenset({"PASS", "BLOCKED", "FAIL"})
_PROVIDER_INVOCATION_STATUSES = frozenset(
    {"PASS", "FAIL", "BLOCKED", "CANCELLED", "RUNNING", "UNSUPPORTED"}
)
_PROVIDER_RESULT_STATUSES = frozenset({"PASS", "FAIL", "BLOCKED", "CANCELLED"})


def _require_non_empty(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _require_mapping(name: str, value: object) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return value


def _require_string_tuple(name: str, value: object, *, non_empty: bool) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{name} must be a list or tuple of strings")
    normalized = tuple(_require_non_empty(name, item) for item in value)
    if non_empty and not normalized:
        raise ValueError(f"{name} must not be empty")
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{name} must contain unique values")
    return normalized


def _optional_string(name: str, value: object) -> str | None:
    if value is None:
        return None
    return _require_non_empty(name, value)


def _bounded_int(
    mapping: Mapping[str, Any],
    key: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{key} must be an integer")
    if not minimum <= value <= maximum:
        raise ValueError(f"{key} must be between {minimum} and {maximum}")
    return value


def _dict_tuple(name: str, value: object) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{name} must be a list or tuple of mappings")
    result: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise ValueError(f"{name} entries must be mappings")
        result.append(dict(item))
    return tuple(result)


@dataclass(frozen=True)
class ProviderProbe:
    status: str
    blocked_reason: str | None = None
    evidence: tuple[dict[str, Any], ...] = ()
    observed_capabilities: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_non_empty("provider probe status", self.status)
        if self.status not in _PROVIDER_PROBE_STATUSES:
            raise ValueError(f"unsupported provider probe status: {self.status}")
        if self.status == "PASS" and self.blocked_reason is not None:
            raise ValueError("PASS provider probe must not include blocked_reason")
        if self.status != "PASS" and self.blocked_reason is not None:
            _require_non_empty("blocked_reason", self.blocked_reason)
        _dict_tuple("provider probe evidence", self.evidence)
        _require_string_tuple(
            "provider probe capabilities",
            self.observed_capabilities,
            non_empty=self.status == "PASS",
        )


class CanonicalProviderResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    execution_id: str
    status: str
    structured_payload: dict[str, Any]
    raw_output_digest: str | None = None
    provider_metadata: dict[str, Any] = {}
    usage: dict[str, Any] = {}
    session_or_run_id: str | None = None
    observed_capabilities: tuple[str, ...] = ()
    errors: tuple[dict[str, Any], ...] = ()
    transport_evidence_refs: tuple[dict[str, Any], ...] = ()

    @field_validator("execution_id")
    @classmethod
    def _execution_id(cls, value: str) -> str:
        return _require_non_empty("execution_id", value)

    @field_validator("status")
    @classmethod
    def _status(cls, value: str) -> str:
        status = _require_non_empty("provider result status", value)
        if status not in _PROVIDER_RESULT_STATUSES:
            raise ValueError(f"unsupported canonical provider result status: {status}")
        return status

    @field_validator(
        "structured_payload",
        "provider_metadata",
        "usage",
        mode="before",
    )
    @classmethod
    def _mapping(cls, value: object) -> dict[str, Any]:
        return dict(_require_mapping("mapping", value))

    @field_validator("raw_output_digest", "session_or_run_id")
    @classmethod
    def _optional(cls, value: object) -> str | None:
        return _optional_string("optional", value)

    @field_validator("observed_capabilities", mode="before")
    @classmethod
    def _caps(cls, value: object) -> tuple[str, ...]:
        return _require_string_tuple("provider result capabilities", value, non_empty=False)

    @field_validator("errors", "transport_evidence_refs", mode="before")
    @classmethod
    def _dicts(cls, value: object) -> tuple[dict[str, Any], ...]:
        return _dict_tuple("provider result collection", value)

    @model_validator(mode="after")
    def _pass_has_no_errors(self) -> CanonicalProviderResult:
        if self.status == "PASS" and self.errors:
            raise ValueError("PASS provider result must not include errors")
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "l9.peer-execution.provider-result.v1",
            "execution_id": self.execution_id,
            "status": self.status,
            "structured_payload": dict(self.structured_payload),
            "raw_output_digest": self.raw_output_digest,
            "provider_metadata": dict(self.provider_metadata),
            "usage": dict(self.usage),
            "session_or_run_id": self.session_or_run_id,
            "observed_capabilities": list(self.observed_capabilities),
            "errors": [dict(item) for item in self.errors],
            "transport_evidence_refs": [dict(item) for item in self.transport_evidence_refs],
        }


@dataclass(frozen=True)
class ProviderInvocation:
    status: str
    state: Mapping[str, Any] = field(default_factory=dict)
    evidence: tuple[dict[str, Any], ...] = ()
    result: CanonicalProviderResult | None = None

    def __post_init__(self) -> None:
        _require_non_empty("provider invocation status", self.status)
        if self.status not in _PROVIDER_INVOCATION_STATUSES:
            raise ValueError(f"unsupported provider invocation status: {self.status}")
        _require_mapping("provider invocation state", self.state)
        _dict_tuple("provider invocation evidence", self.evidence)
        if self.result is not None and not isinstance(self.result, CanonicalProviderResult):
            raise ValueError("provider invocation result must be CanonicalProviderResult")
        if self.result is not None and self.result.status != self.status:
            raise ValueError(
                "provider invocation status must equal canonical provider result status"
            )
        if self.status == "PASS" and self.result is None:
            raise ValueError("PASS provider invocation requires a canonical provider result")
        if self.status in {"RUNNING", "UNSUPPORTED"} and self.result is not None:
            raise ValueError(f"{self.status} provider invocation must not include a result")


class CanonicalExecutionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    execution_id: str
    task_id: str
    program_lock_digest: str
    rendered_contract_digest: str
    worktree_ref: str
    objective: str
    context_manifest_ref: str
    context_manifest_digest: str
    rendered_contract: dict[str, Any]
    worker_instruction: str
    permission_profile_ref: str
    permission_profile: dict[str, Any]
    inference_budget: dict[str, Any]
    timeout_budget: dict[str, Any]
    requested_capabilities: tuple[str, ...]
    telemetry_context: dict[str, Any]
    agent_ref: str | None = None
    surface: str | None = None
    provider_ref: str = ""
    execution_profile_ref: str = ""

    @model_validator(mode="after")
    def _validate_request(self) -> CanonicalExecutionRequest:
        for name in (
            "execution_id",
            "task_id",
            "worktree_ref",
            "objective",
            "context_manifest_ref",
            "worker_instruction",
            "permission_profile_ref",
        ):
            _require_non_empty(name, getattr(self, name))
        object.__setattr__(
            self,
            "program_lock_digest",
            normalize_digest(_require_non_empty("program_lock_digest", self.program_lock_digest)),
        )
        object.__setattr__(
            self,
            "rendered_contract_digest",
            normalize_digest(
                _require_non_empty("rendered_contract_digest", self.rendered_contract_digest)
            ),
        )
        object.__setattr__(
            self,
            "context_manifest_digest",
            normalize_digest(
                _require_non_empty("context_manifest_digest", self.context_manifest_digest)
            ),
        )
        _require_mapping("rendered_contract", self.rendered_contract)
        permission = _require_mapping("permission_profile", self.permission_profile)
        if permission.get("profile_ref") != self.permission_profile_ref:
            raise ValueError("permission profile reference does not match resolved profile")
        inference = _require_mapping("inference_budget", self.inference_budget)
        timeout = _require_mapping("timeout_budget", self.timeout_budget)
        _bounded_int(inference, "max_turns", minimum=1, maximum=64)
        _bounded_int(timeout, "dispatch_seconds", minimum=1, maximum=7200)
        _bounded_int(timeout, "poll_seconds", minimum=1, maximum=600)
        requested = _require_string_tuple(
            "requested_capabilities",
            self.requested_capabilities,
            non_empty=True,
        )
        allowed = permission.get("allowed_actions")
        if not isinstance(allowed, list) or not set(requested) <= set(allowed):
            raise ValueError("resolved permission profile does not allow requested capabilities")
        _require_mapping("telemetry_context", self.telemetry_context)
        for name in ("provider_ref", "execution_profile_ref"):
            _require_non_empty(name, getattr(self, name))
        for name in ("agent_ref", "surface"):
            _optional_string(name, getattr(self, name))
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "l9.peer-execution.request.v1",
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "program_lock_digest": self.program_lock_digest,
            "rendered_contract_digest": self.rendered_contract_digest,
            "worktree_ref": self.worktree_ref,
            "objective": self.objective,
            "context_manifest_ref": self.context_manifest_ref,
            "context_manifest_digest": self.context_manifest_digest,
            "rendered_contract": dict(self.rendered_contract),
            "worker_instruction": self.worker_instruction,
            "permission_profile_ref": self.permission_profile_ref,
            "permission_profile": dict(self.permission_profile),
            "inference_budget": dict(self.inference_budget),
            "timeout_budget": dict(self.timeout_budget),
            "requested_capabilities": list(self.requested_capabilities),
            "telemetry_context": dict(self.telemetry_context),
            "agent_ref": self.agent_ref,
            "surface": self.surface,
            "provider_ref": self.provider_ref,
            "execution_profile_ref": self.execution_profile_ref,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> CanonicalExecutionRequest:
        if value.get("schema") != "l9.peer-execution.request.v1":
            raise ValueError("unsupported canonical execution request schema")
        capabilities = _require_string_tuple(
            "requested_capabilities",
            value.get("requested_capabilities"),
            non_empty=True,
        )
        return cls(
            execution_id=_require_non_empty("execution_id", value.get("execution_id")),
            task_id=_require_non_empty("task_id", value.get("task_id")),
            program_lock_digest=_require_non_empty(
                "program_lock_digest", value.get("program_lock_digest")
            ),
            rendered_contract_digest=_require_non_empty(
                "rendered_contract_digest", value.get("rendered_contract_digest")
            ),
            worktree_ref=_require_non_empty("worktree_ref", value.get("worktree_ref")),
            objective=_require_non_empty("objective", value.get("objective")),
            context_manifest_ref=_require_non_empty(
                "context_manifest_ref", value.get("context_manifest_ref")
            ),
            context_manifest_digest=_require_non_empty(
                "context_manifest_digest", value.get("context_manifest_digest")
            ),
            rendered_contract=dict(
                _require_mapping("rendered_contract", value.get("rendered_contract"))
            ),
            worker_instruction=_require_non_empty(
                "worker_instruction", value.get("worker_instruction")
            ),
            permission_profile_ref=_require_non_empty(
                "permission_profile_ref", value.get("permission_profile_ref")
            ),
            permission_profile=dict(
                _require_mapping("permission_profile", value.get("permission_profile"))
            ),
            inference_budget=dict(
                _require_mapping("inference_budget", value.get("inference_budget"))
            ),
            timeout_budget=dict(_require_mapping("timeout_budget", value.get("timeout_budget"))),
            requested_capabilities=capabilities,
            telemetry_context=dict(
                _require_mapping("telemetry_context", value.get("telemetry_context"))
            ),
            agent_ref=_optional_string("agent_ref", value.get("agent_ref")),
            surface=_optional_string("surface", value.get("surface")),
            provider_ref=_require_non_empty("provider_ref", value.get("provider_ref")),
            execution_profile_ref=_require_non_empty(
                "execution_profile_ref", value.get("execution_profile_ref")
            ),
        )


def validate_provider_invocation(
    request: CanonicalExecutionRequest,
    invocation: ProviderInvocation,
) -> None:
    """Fail closed when provider lifecycle and canonical result bindings diverge."""

    result = invocation.result
    if result is None:
        return
    if result.execution_id != request.execution_id:
        raise ValueError("canonical provider result execution_id does not match execution request")


class ThinProvider(Protocol):
    provider_id: str

    def probe(self, context: ProbeContext) -> ProviderProbe:
        ...

    def invoke(self, request: CanonicalExecutionRequest) -> ProviderInvocation:
        ...

    def poll(
        self,
        request: CanonicalExecutionRequest,
        state: Mapping[str, Any],
    ) -> ProviderInvocation: ...

    def cancel(
        self,
        request: CanonicalExecutionRequest,
        state: Mapping[str, Any],
    ) -> ProviderInvocation: ...

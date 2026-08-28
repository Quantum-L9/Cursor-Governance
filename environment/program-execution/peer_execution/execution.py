from __future__ import annotations

import json
import os
import subprocess
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import structlog

from .base import BaseExecutionAdapter
from .context import write_context_manifest
from .contracts import ContractBinding, validate_contract
from .core_receipts import attempt_receipt, verification_receipt
from .errors import AdapterFailure, CanonicalErrorCode
from .permissions import resolve_permission_profile
from .provider import (
    CanonicalExecutionRequest,
    CanonicalProviderResult,
    ProviderInvocation,
    ThinProvider,
    validate_autonomy_authority,
    validate_provider_invocation,
)

log = structlog.get_logger("peer_execution")

_TERMINAL_PROVIDER_STATUSES = {"PASS", "FAIL", "BLOCKED", "CANCELLED"}
_CLAIMED_STATUSES = {"completed", "failed", "blocked", "stopped"}
#: Actions Program Execution performs at its own boundary instead of delegating.
#: A Rendered Contract's `requested_actions` states the *task's* authority; the
#: provider is asked only for the part of it the worker actually carries out.
#: The worker mutates the worktree and PE stages and commits exactly the work
#: the Controller verified, so `commit` is never a provider capability -- every
#: adapter descriptor and every provider probe declares inspect / local_write /
#: artifact_production and none declares commit. Declaring it there would assert
#: a capability that does not exist and widen what the worker may do.
PE_RETAINED_ACTIONS = frozenset({"commit"})


def delegated_actions(requested: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    """The subset of a contract's actions the provider is actually asked for."""
    return tuple(action for action in requested if action not in PE_RETAINED_ACTIONS)


def _required_string(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _string_list(payload: Mapping[str, Any], key: str, *, required: bool) -> list[str]:
    value = payload.get(key)
    if isinstance(value, str) and value.strip():
        value = [value.strip()]
    if value is None and not required:
        return []
    if not isinstance(value, list):
        raise ValueError(f"provider payload {key} must be an array")
    output: list[str] = []
    for item in value:
        output.append(_required_string(f"provider payload {key} item", item))
    if len(set(output)) != len(output):
        raise ValueError(f"provider payload {key} must contain unique values")
    return output


def _observe_worktree_changes(contract: Mapping[str, Any]) -> list[str]:
    worktree = contract.get("worktree")
    if not isinstance(worktree, str) or not worktree.strip():
        return []
    root = Path(worktree).expanduser()
    if not root.is_dir():
        return []
    completed = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return []
    # NUL-delimited, parsed exactly as pec/controller.py::_changed_paths does.
    # Without -z git quotes any path containing a space, and the quotes end up
    # in the recorded filename, so verification against the controller's
    # NUL-parsed set fails changed_files_exact on an otherwise valid attempt.
    paths: set[str] = set()
    parts = completed.stdout.split("\0")
    index = 0
    while index < len(parts):
        entry = parts[index]
        if not entry:
            index += 1
            continue
        status_code = entry[:2]
        path = entry[3:]
        if status_code[0] in {"R", "C"} and index + 1 < len(parts):
            index += 1
            path = parts[index]
        if path:
            paths.add(path.replace("\\", "/"))
        index += 1
    return sorted(paths)


def _mapping_list(
    payload: Mapping[str, Any],
    key: str,
    *,
    required: bool,
) -> list[dict[str, Any]]:
    value = payload.get(key)
    if value is None and not required:
        return []
    if not isinstance(value, list):
        raise ValueError(f"provider payload {key} must be an array")
    output: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise ValueError(f"provider payload {key} entries must be objects")
        output.append(dict(item))
    return output


class PeerExecutionAdapter(BaseExecutionAdapter):
    """Provider-neutral lifecycle owner for peer/provider execution."""

    def __init__(
        self,
        runtime_root: str | Path,
        *,
        descriptor: Mapping[str, Any],
        provider: ThinProvider,
        execution_profile: Mapping[str, Any],
        binding_context: Mapping[str, Any] | None = None,
        autonomy_authority: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(runtime_root)
        self.descriptor = dict(descriptor)
        self.provider = provider
        self.execution_profile = dict(execution_profile)
        self.binding_context = dict(binding_context or {})
        self.autonomy_authority: dict[str, Any] | None = (
            validate_autonomy_authority(autonomy_authority)
            if autonomy_authority is not None
            else None
        )
        self.adapter_id = _required_string("adapter_id", self.descriptor.get("adapter_id"))
        self.adapter_version = _required_string(
            "adapter_version",
            self.descriptor.get("adapter_version"),
        )
        if provider.provider_id != self.adapter_id:
            raise ValueError(
                f"provider identity mismatch: descriptor={self.adapter_id} "
                f"provider={provider.provider_id}"
            )
        bound_provider = self.binding_context.get("provider_ref")
        if bound_provider is not None and bound_provider != self.adapter_id:
            raise ValueError(
                f"binding provider_ref mismatch: expected {self.adapter_id}, found {bound_provider}"
            )
        profile_ref = _required_string(
            "profile_ref",
            self.execution_profile.get("profile_ref"),
        )
        bound_profile = self.binding_context.get("execution_profile_ref")
        if bound_profile is not None and bound_profile != profile_ref:
            raise ValueError(
                f"binding execution_profile_ref mismatch: expected {profile_ref}, "
                f"found {bound_profile}"
            )
        capabilities = self.descriptor.get("capabilities") or {}
        if not isinstance(capabilities, Mapping):
            raise ValueError("adapter capabilities must be an object")
        actions = capabilities.get("actions") or []
        if not isinstance(actions, list):
            raise ValueError("adapter capabilities.actions must be an array")
        self.capabilities = tuple(_required_string("adapter capability", item) for item in actions)
        self.cancellation = _required_string(
            "adapter cancellation mode",
            capabilities.get("cancellation") or "unsupported",
        )
        self._provider_observed_capabilities: tuple[str, ...] = ()

    def bind_autonomy_authority(self, authority: Mapping[str, Any] | None) -> None:
        """Carry one task-scoped root authority sidecar beside the contract.

        The sidecar never enters the rendered contract or its digest: Program
        identity is the Controller's, and root authority is evidence that
        travels next to it.
        """
        self.autonomy_authority = (
            validate_autonomy_authority(authority) if authority is not None else None
        )

    def _authority_for(self, contract: Mapping[str, Any]) -> dict[str, Any] | None:
        """This adapter's authority, refused when it belongs to another task."""
        if self.autonomy_authority is None:
            return None
        task_id = contract.get("task_id") or contract.get("id")
        return validate_autonomy_authority(
            self.autonomy_authority,
            task_id=str(task_id) if task_id is not None else None,
        )

    def _probe_status(self, context):
        probe = self.provider.probe(context)
        self._provider_observed_capabilities = tuple(probe.observed_capabilities)
        evidence = [dict(item) for item in probe.evidence]
        evidence.append(
            {
                "type": "peer_execution_profile",
                "profile_ref": self.execution_profile["profile_ref"],
            }
        )
        return probe.status, probe.blocked_reason, evidence

    def _effective_capabilities(self, context, status, evidence):
        if status != "PASS":
            return ()
        declared = set(self.capabilities)
        observed = set(self._provider_observed_capabilities)
        return tuple(sorted(declared & observed))

    def prepare(self, contract: Mapping[str, Any]):
        expected = contract.get("program_lock_digest") or contract.get("program_digest")
        binding = validate_contract(contract, expected_program_lock_digest=expected)
        probe = self._require_fresh_probe(binding.program_lock_digest)
        delegated = delegated_actions(binding.requested_actions)
        unsupported = sorted(set(delegated) - set(probe.capabilities))
        if unsupported:
            raise AdapterFailure(
                CanonicalErrorCode.CAPABILITY_UNSUPPORTED,
                "Rendered Contract requests capabilities not proven by the provider probe",
                "REQUESTED_CAPABILITY_NOT_PROBED",
            )
        permission_profile = resolve_permission_profile(
            _required_string(
                "permission_profile_ref",
                self.execution_profile.get("permission_profile_ref"),
            ),
            delegated,
        )
        denied = sorted(set(delegated) - set(permission_profile.get("allowed_actions") or []))
        if denied:
            raise AdapterFailure(
                CanonicalErrorCode.AUTHORIZATION_INFLATION,
                f"Execution profile denies requested actions: {denied}",
                "EXECUTION_PROFILE_DENIES_REQUESTED_ACTION",
            )
        receipt = super().prepare(contract)
        record = self.runtime.load(str(receipt.dispatch_id))
        record["execution_profile_ref"] = self.execution_profile["profile_ref"]
        record["binding_context"] = dict(self.binding_context)
        authority = self._authority_for(contract)
        record["autonomy_authority"] = dict(authority) if authority is not None else None
        self.runtime.save(str(receipt.dispatch_id), record)
        return receipt

    def _request_for(
        self,
        record: Mapping[str, Any],
        binding: ContractBinding,
    ) -> CanonicalExecutionRequest:
        contract = binding.raw
        dispatch_id = _required_string("dispatch_id", record.get("dispatch_id"))
        context_path = write_context_manifest(self.runtime.root, dispatch_id, contract)
        context_value = json.loads(context_path.read_text(encoding="utf-8"))
        context_errors = self.schemas.validate_context_manifest(context_value)
        if context_errors:
            raise ValueError(f"context manifest schema errors: {context_errors}")
        profile = self.execution_profile
        context = self.binding_context
        permission_profile = resolve_permission_profile(
            _required_string(
                "permission_profile_ref",
                profile.get("permission_profile_ref"),
            ),
            delegated_actions(binding.requested_actions),
        )
        return CanonicalExecutionRequest(
            execution_id=dispatch_id,
            task_id=binding.task_id,
            program_lock_digest=binding.program_lock_digest,
            rendered_contract_digest=binding.rendered_contract_digest,
            worktree_ref=_required_string("worktree", context_value.get("worktree")),
            objective=_required_string("objective", contract.get("objective")),
            context_manifest_ref=str(context_path),
            context_manifest_digest=_required_string(
                "context_manifest_digest", context_value.get("manifest_digest")
            ),
            rendered_contract=dict(context_value["rendered_contract"]),
            worker_instruction=_required_string(
                "worker_instruction", context_value.get("worker_instruction")
            ),
            permission_profile_ref=_required_string(
                "permission_profile_ref",
                profile.get("permission_profile_ref"),
            ),
            permission_profile=permission_profile,
            inference_budget=dict(profile.get("inference_budget") or {}),
            timeout_budget=dict(profile.get("timeout_budget") or {}),
            requested_capabilities=delegated_actions(binding.requested_actions),
            telemetry_context={
                "provider_ref": self.adapter_id,
                "execution_profile_ref": profile["profile_ref"],
                "task_id": binding.task_id,
                "agent_ref": context.get("agent_ref"),
                "surface": context.get("surface"),
            },
            agent_ref=(
                _required_string("agent_ref", context["agent_ref"])
                if context.get("agent_ref") is not None
                else None
            ),
            surface=(
                _required_string("surface", context["surface"])
                if context.get("surface") is not None
                else None
            ),
            provider_ref=self.adapter_id,
            execution_profile_ref=_required_string(
                "profile_ref",
                profile.get("profile_ref"),
            ),
            autonomy_authority=self._authority_for(contract),
        )

    def _request_from_record(
        self,
        record: Mapping[str, Any],
    ) -> CanonicalExecutionRequest:
        raw = record.get("canonical_execution_request")
        if not isinstance(raw, Mapping):
            raise ValueError("canonical execution request is missing from dispatch record")
        request_errors = self.schemas.validate_peer_execution_request(raw)
        if request_errors:
            raise ValueError(f"canonical execution request schema errors: {request_errors}")
        request = CanonicalExecutionRequest.from_dict(raw)
        dispatch_id = _required_string("dispatch_id", record.get("dispatch_id"))
        if request.execution_id != dispatch_id:
            raise ValueError("canonical execution request execution_id drift")
        binding = validate_contract(record["contract"])
        expected = {
            "task_id": binding.task_id,
            "program_lock_digest": binding.program_lock_digest,
            "rendered_contract_digest": binding.rendered_contract_digest,
            "worktree_ref": _required_string("worktree", binding.raw.get("worktree")),
            "objective": _required_string("objective", binding.raw.get("objective")),
            "provider_ref": self.adapter_id,
            "execution_profile_ref": self.execution_profile["profile_ref"],
            "permission_profile_ref": self.execution_profile["permission_profile_ref"],
        }
        for key, expected_value in expected.items():
            if getattr(request, key) != expected_value:
                raise ValueError(f"canonical execution request {key} drift")
        if request.requested_capabilities != delegated_actions(binding.requested_actions):
            raise ValueError("canonical execution request requested_capabilities drift")
        if dict(request.inference_budget) != dict(
            self.execution_profile.get("inference_budget") or {}
        ):
            raise ValueError("canonical execution request inference_budget drift")
        if dict(request.timeout_budget) != dict(self.execution_profile.get("timeout_budget") or {}):
            raise ValueError("canonical execution request timeout_budget drift")
        expected_context = (
            self.runtime.root / "contexts" / f"{request.execution_id}.json"
        ).resolve()
        if Path(request.context_manifest_ref).expanduser().resolve() != expected_context:
            raise ValueError("canonical execution request context_manifest_ref drift")
        context_value = json.loads(expected_context.read_text(encoding="utf-8"))
        context_errors = self.schemas.validate_context_manifest(context_value)
        if context_errors:
            raise ValueError(f"context manifest schema errors: {context_errors}")
        if request.context_manifest_digest != context_value.get("manifest_digest"):
            raise ValueError("canonical execution request context_manifest_digest drift")
        if dict(request.rendered_contract) != dict(context_value.get("rendered_contract") or {}):
            raise ValueError("canonical execution request rendered_contract drift")
        if request.worker_instruction != context_value.get("worker_instruction"):
            raise ValueError("canonical execution request worker_instruction drift")
        expected_permission = resolve_permission_profile(
            request.permission_profile_ref,
            delegated_actions(binding.requested_actions),
        )
        if dict(request.permission_profile) != expected_permission:
            raise ValueError("canonical execution request permission_profile drift")
        for key in ("agent_ref", "surface"):
            expected_value = self.binding_context.get(key)
            if expected_value is not None and getattr(request, key) != expected_value:
                raise ValueError(f"canonical execution request {key} drift")
        expected_authority = record.get("autonomy_authority")
        if expected_authority is None:
            expected_authority = self._authority_for(binding.raw)
        if request.autonomy_authority is not None or expected_authority is not None:
            if request.autonomy_authority is None or expected_authority is None:
                raise ValueError("canonical execution request autonomy_authority drift")
            if dict(request.autonomy_authority) != dict(expected_authority):
                raise ValueError("canonical execution request autonomy_authority drift")
        return request

    @staticmethod
    def _provider_evidence(result: CanonicalProviderResult) -> dict[str, Any]:
        return {
            "type": "peer_execution_provider_result",
            "execution_id": result.execution_id,
            "status": result.status,
            "raw_output_digest": result.raw_output_digest,
            "provider_metadata": dict(result.provider_metadata),
            "usage": dict(result.usage),
            "session_or_run_id": result.session_or_run_id,
            "observed_capabilities": list(result.observed_capabilities),
            "errors": [dict(item) for item in result.errors],
            "transport_evidence_refs": [dict(item) for item in result.transport_evidence_refs],
        }

    def _attempt_receipt(
        self,
        contract: Mapping[str, Any],
        result: CanonicalProviderResult,
    ) -> dict[str, Any]:
        payload = dict(result.structured_payload)
        claimed_status_value = payload.get("claimed_status")
        claimed_status = (
            claimed_status_value
            if isinstance(claimed_status_value, str)
            else ("completed" if result.status == "PASS" else "failed")
        )
        if claimed_status not in _CLAIMED_STATUSES:
            raise ValueError(f"provider payload claimed_status is invalid: {claimed_status}")
        if result.status == "PASS" and claimed_status != "completed":
            raise ValueError("PASS provider result must claim completed status")
        if result.status != "PASS" and claimed_status == "completed":
            claimed_status = "failed"
        candidate_sha = payload.get("candidate_sha")
        if candidate_sha is not None and not isinstance(candidate_sha, str):
            raise ValueError("provider payload candidate_sha must be a string or null")
        residuals = _string_list(payload, "residual_unknowns", required=False)
        raw_changed = payload.get("changed_files")
        if isinstance(raw_changed, str) and raw_changed.strip():
            payload["changed_files"] = [raw_changed.strip()]
            residuals.append("changed_files_coerced_from_string")
        try:
            changed_files = _string_list(payload, "changed_files", required=False)
        except ValueError:
            changed_files = []
            residuals.append("changed_files_unusable_shape")
        if not changed_files:
            observed = _observe_worktree_changes(contract)
            if observed:
                changed_files = observed
                residuals.append("changed_files_recovered_from_worktree")
        try:
            validation_results = _mapping_list(
                payload,
                "validation_results",
                required=False,
            )
        except ValueError:
            validation_results = []
            residuals.append("validation_results_unusable_shape")
        return attempt_receipt(
            contract,
            candidate_sha=candidate_sha,
            changed_files=changed_files,
            validation_results=validation_results,
            produced_evidence=[self._provider_evidence(result)],
            residual_unknowns=residuals,
            claimed_status=claimed_status,
        )

    def _verification_receipt(
        self,
        contract: Mapping[str, Any],
        result: CanonicalProviderResult,
    ) -> dict[str, Any]:
        payload = dict(result.structured_payload)
        candidate_sha = payload.get("candidate_sha")
        if candidate_sha is not None and not isinstance(candidate_sha, str):
            raise ValueError("provider payload candidate_sha must be a string or null")
        required = result.status == "PASS"
        gates = payload.get("gates")
        if gates is None and not required:
            gates = {}
        if not isinstance(gates, Mapping):
            raise ValueError("provider payload gates must be an object")
        normalized_gates: dict[str, str] = {}
        for key, value in gates.items():
            normalized_gates[_required_string("provider payload gate id", key)] = _required_string(
                "provider payload gate status", value
            )
        return verification_receipt(
            contract,
            candidate_sha=candidate_sha,
            declared_changed_files=_string_list(
                payload,
                "declared_changed_files",
                required=required,
            ),
            observed_changed_files=_string_list(
                payload,
                "observed_changed_files",
                required=required,
            ),
            validations=_mapping_list(payload, "validations", required=required),
            gates=normalized_gates,
        )

    def _terminal_receipt(
        self,
        contract: Mapping[str, Any],
        result: CanonicalProviderResult,
    ) -> dict[str, Any]:
        receipts = self.descriptor.get("receipts") or {}
        if not isinstance(receipts, Mapping):
            raise ValueError("adapter receipts must be an object")
        kind = receipts.get("terminal_core_receipt")
        if kind == "attempt":
            return self._attempt_receipt(contract, result)
        if kind == "verification":
            return self._verification_receipt(contract, result)
        raise ValueError(f"peer execution terminal receipt kind is unsupported: {kind}")

    def _apply_invocation(
        self,
        record: dict[str, Any],
        request: CanonicalExecutionRequest,
        invocation: ProviderInvocation,
    ) -> tuple[str, list[dict[str, Any]]]:
        validate_provider_invocation(request, invocation)
        record["provider_state"] = dict(invocation.state)
        evidence = [dict(item) for item in invocation.evidence]
        if invocation.result is not None:
            probe = self._require_fresh_probe(request.program_lock_digest)
            unexpected = sorted(
                set(invocation.result.observed_capabilities) - set(probe.capabilities)
            )
            if unexpected:
                raise ValueError(
                    f"provider result reports capabilities not proven by probe: {unexpected}"
                )
            provider_result = invocation.result.to_dict()
            result_errors = self.schemas.validate_provider_result(provider_result)
            if result_errors:
                raise ValueError(f"canonical provider result schema errors: {result_errors}")
            record["provider_result"] = provider_result
            record["result"] = self._terminal_receipt(record["contract"], invocation.result)
            evidence.append(self._provider_evidence(invocation.result))
        return invocation.status, evidence

    def _dispatch_record(self, record: dict[str, Any]):
        binding = validate_contract(record["contract"])
        request = self._request_for(record, binding)
        request_value = request.to_dict()
        request_errors = self.schemas.validate_peer_execution_request(request_value)
        if request_errors:
            raise ValueError(f"canonical execution request schema errors: {request_errors}")
        record["canonical_execution_request"] = request_value
        record["status"] = "DISPATCHING"
        self.runtime.save(request.execution_id, record)
        try:
            invocation = self.provider.invoke(request)
        except Exception as exc:
            record["status"] = "BLOCKED"
            record["evidence"] = [
                {
                    "type": "provider_invoke_exception",
                    "error_type": type(exc).__name__,
                }
            ]
            self.runtime.save(request.execution_id, record)
            raise
        try:
            return self._apply_invocation(record, request, invocation)
        except ValueError as exc:
            record["status"] = "FAIL"
            evidence = [dict(item) for item in invocation.evidence]
            if invocation.result is not None:
                record["provider_result"] = invocation.result.to_dict()
                evidence.append(self._provider_evidence(invocation.result))
            evidence.append(
                {
                    "type": "payload_shape_error",
                    "error_type": type(exc).__name__,
                    "message": str(exc)[:500],
                }
            )
            record["evidence"] = evidence
            self.runtime.save(request.execution_id, record)
            raise

    def status(self, dispatch_id: str):
        record = self.runtime.load(dispatch_id)
        if record.get("status") == "RUNNING":
            request = self._request_from_record(record)
            invocation = self.provider.poll(
                request,
                dict(record.get("provider_state") or {}),
            )
            status, evidence = self._apply_invocation(record, request, invocation)
            record["status"] = status
            record["evidence"] = evidence
            self.runtime.save(dispatch_id, record)
        return super().status(dispatch_id)

    def _attempt_receipt_target(self, contract: Mapping[str, Any]) -> Path | None:
        value = contract.get("attempt_receipt_path")
        if value is None:
            return None
        target = Path(_required_string("attempt_receipt_path", value)).expanduser()
        if not target.is_absolute():
            raise ValueError("attempt receipt target must be absolute")
        runtime_root = self.runtime.root.resolve()
        if len(runtime_root.parents) < 2 or runtime_root.name != "peer-execution":
            raise ValueError("peer execution runtime root is not Controller-workspace bound")
        workspace = runtime_root.parents[1]
        attempts_root = (workspace / "attempts").resolve()
        resolved = target.resolve(strict=False)
        try:
            resolved.relative_to(attempts_root)
        except ValueError as exc:
            raise ValueError("attempt receipt target escapes Controller attempts root") from exc
        cursor = attempts_root
        relative = resolved.relative_to(attempts_root)
        for part in relative.parts[:-1]:
            cursor /= part
            if cursor.is_symlink():
                raise ValueError(f"refusing symlinked attempt receipt parent: {cursor}")
        if resolved.is_symlink():
            raise ValueError(f"refusing symlinked attempt receipt target: {resolved}")
        return resolved

    @staticmethod
    def _write_attempt_receipt(target: Path, result: Mapping[str, Any]) -> None:
        payload = (json.dumps(dict(result), indent=2, sort_keys=True) + "\n").encode("utf-8")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_file():
            if target.read_bytes() == payload:
                return
            raise ValueError("attempt receipt target already contains conflicting evidence")
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile("wb", dir=target.parent, delete=False) as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
                temporary = Path(handle.name)
            os.replace(temporary, target)
            temporary = None
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()

    def collect(self, dispatch_id: str):
        record = self.runtime.load(dispatch_id)
        terminal = {"PASS", "COMPLETED", "FAIL", "FAILED", "BLOCKED", "CANCELLED"}
        if record.get("status") not in terminal:
            raise AdapterFailure(
                CanonicalErrorCode.VALIDATION_FAILURE,
                "Dispatch is not complete",
                "DISPATCH_NOT_COMPLETE",
            )
        result = record.get("result")
        if not isinstance(result, Mapping):
            raise AdapterFailure(
                CanonicalErrorCode.VALIDATION_FAILURE,
                "Dispatch has no typed terminal result",
                "TERMINAL_RESULT_MISSING",
            )
        errors = self.schemas.validate_terminal_receipt(result)
        if errors:
            raise AdapterFailure(
                CanonicalErrorCode.VALIDATION_FAILURE,
                "Terminal result failed schema validation",
                "TERMINAL_RESULT_SCHEMA_INVALID",
            )
        contract = record.get("contract")
        if not isinstance(contract, Mapping):
            raise ValueError("dispatch record contract is missing")
        if result.get("schema") == "program-execution-controller.attempt-receipt.v2":
            target = self._attempt_receipt_target(contract)
            if target is None:
                raise ValueError("attempt receipt target is required")
            self._write_attempt_receipt(target, result)
        binding = validate_contract(contract)
        self._append(
            phase="collect",
            binding=binding,
            status="PASS",
            dispatch_id=dispatch_id,
            evidence=[{"type": "terminal_result", "kind": result.get("schema")}],
        )
        return dict(result)

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
        request = self._request_from_record(record)
        invocation = self.provider.cancel(
            request,
            dict(record.get("provider_state") or {}),
        )
        status, evidence = self._apply_invocation(record, request, invocation)
        if status not in _TERMINAL_PROVIDER_STATUSES and status != "RUNNING":
            status = "UNSUPPORTED"
        # A RUNNING cancel means the request was accepted but termination is
        # not yet acknowledged by the owning host: keep the record RUNNING so
        # status() keeps polling for the real terminal acknowledgement instead
        # of freezing a false UNSUPPORTED/CANCELLED verdict.
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

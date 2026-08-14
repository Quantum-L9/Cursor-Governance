from __future__ import annotations

import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .contracts import ContractBinding, validate_contract
from .errors import AdapterFailure, CanonicalErrorCode
from .models import CapabilityReceipt, LifecycleReceipt, ProbeContext
from .receipts import ReceiptChain
from .runtime_store import RuntimeStore
from .schema_registry import SchemaRegistry


class BaseExecutionAdapter:
    adapter_id = "base"
    adapter_version = "1.0.0"
    capabilities: tuple[str, ...] = ()
    cancellation = "unsupported"

    def __init__(self, runtime_root: str | Path) -> None:
        self.runtime = RuntimeStore(runtime_root)
        self.chain = ReceiptChain(runtime_root)
        self.schemas = SchemaRegistry(Path(__file__).resolve().parents[1])
        self._last_probe: CapabilityReceipt | None = None

    def _append(
        self,
        *,
        phase: str,
        binding: ContractBinding | None,
        status: str,
        dispatch_id: str | None = None,
        evidence: list[dict[str, Any]] | None = None,
        canonical_error_code: str | None = None,
        adapter_error_code: str | None = None,
        program_lock_digest: str | None = None,
    ) -> LifecycleReceipt:
        lock_digest = program_lock_digest
        if binding is not None:
            lock_digest = binding.program_lock_digest
        if lock_digest is None:
            raise ValueError("Program Lock digest is required")
        receipt = LifecycleReceipt.create(
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
            phase=phase,
            program_lock_digest=lock_digest,
            rendered_contract_digest=(binding.rendered_contract_digest if binding else None),
            task_id=binding.task_id if binding else None,
            dispatch_id=dispatch_id,
            status=status,
            canonical_error_code=canonical_error_code,
            adapter_error_code=adapter_error_code,
            evidence=evidence,
            previous_receipt_digest=self.chain.last_digest(),
        )
        errors = self.schemas.validate_lifecycle(receipt.to_dict())
        if errors:
            raise ValueError(f"lifecycle receipt schema errors: {errors}")
        self.chain.append(receipt)
        return receipt

    def _probe_status(self, context: ProbeContext) -> tuple[str, str | None, list[dict[str, Any]]]:
        return "PASS", None, []

    def _effective_capabilities(
        self,
        context: ProbeContext,
        status: str,
        _evidence: list[dict[str, Any]],
    ) -> tuple[str, ...]:
        if status != "PASS":
            return ()
        return self.capabilities

    def probe(self, context: ProbeContext) -> CapabilityReceipt:
        status, reason, evidence = self._probe_status(context)
        effective = self._effective_capabilities(context, status, evidence)
        receipt = CapabilityReceipt.create(
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
            status=status,
            capabilities=list(effective),
            program_lock_digest=context.program_lock_digest,
            evidence=evidence,
            blocked_reason=reason,
        )
        capability_errors = self.schemas.validate_capability(receipt.to_dict())
        if capability_errors:
            raise ValueError(f"capability receipt schema errors: {capability_errors}")
        self._last_probe = receipt
        self.runtime.save_capability(self.adapter_id, receipt.to_dict())
        self._append(
            phase="probe",
            binding=None,
            status=status,
            evidence=evidence,
            program_lock_digest=context.program_lock_digest,
            canonical_error_code=(
                CanonicalErrorCode.CAPABILITY_UNSUPPORTED.value if status != "PASS" else None
            ),
        )
        return receipt

    def _require_fresh_probe(self, program_lock_digest: str) -> CapabilityReceipt:
        probe = self._last_probe
        if probe is None:
            stored = self.runtime.load_capability(self.adapter_id)
            if stored is not None:
                probe = CapabilityReceipt.from_dict(stored)
                self._last_probe = probe
        if probe is None or not probe.is_valid() or not probe.is_fresh():
            raise AdapterFailure(
                CanonicalErrorCode.CAPABILITY_UNSUPPORTED,
                "A fresh capability receipt is required",
                "CAPABILITY_RECEIPT_MISSING_OR_STALE",
            )
        if probe.program_lock_digest != program_lock_digest:
            raise AdapterFailure(
                CanonicalErrorCode.PROGRAM_LOCK_STALE,
                "Capability receipt is bound to a different Program Lock",
                "CAPABILITY_PROGRAM_LOCK_MISMATCH",
            )
        return probe

    def prepare(self, contract: Mapping[str, Any]) -> LifecycleReceipt:
        expected = contract.get("program_lock_digest") or contract.get("program_digest")
        binding = validate_contract(contract, expected_program_lock_digest=expected)
        self._require_fresh_probe(binding.program_lock_digest)
        dispatch_id = f"{self.adapter_id}-{uuid.uuid4().hex}"
        record = {
            "dispatch_id": dispatch_id,
            "adapter_id": self.adapter_id,
            "status": "PREPARED",
            "binding": {
                "task_id": binding.task_id,
                "program_lock_digest": binding.program_lock_digest,
                "rendered_contract_digest": binding.rendered_contract_digest,
                "requested_actions": list(binding.requested_actions),
            },
            "contract": binding.raw,
        }
        self.runtime.save(dispatch_id, record)
        return self._append(
            phase="prepare",
            binding=binding,
            status="PASS",
            dispatch_id=dispatch_id,
            evidence=[{"type": "dispatch_record", "dispatch_id": dispatch_id}],
        )

    def _dispatch_record(self, _record: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
        return "RUNNING", []

    def dispatch(self, prepared: Mapping[str, Any]) -> LifecycleReceipt:
        dispatch_id = prepared.get("dispatch_id")
        if not isinstance(dispatch_id, str):
            raise ValueError("dispatch_id is required")
        record = self.runtime.load(dispatch_id)
        if record.get("status") != "PREPARED":
            raise ValueError("dispatch record is not PREPARED")
        binding = validate_contract(record["contract"])
        self._require_fresh_probe(binding.program_lock_digest)
        status, evidence = self._dispatch_record(record)
        record["status"] = status
        record["evidence"] = evidence
        self.runtime.save(dispatch_id, record)
        return self._append(
            phase="dispatch",
            binding=binding,
            status=status,
            dispatch_id=dispatch_id,
            evidence=evidence,
        )

    def status(self, dispatch_id: str) -> LifecycleReceipt:
        record = self.runtime.load(dispatch_id)
        binding = validate_contract(record["contract"])
        return self._append(
            phase="progress",
            binding=binding,
            status=str(record.get("status", "BLOCKED")),
            dispatch_id=dispatch_id,
            evidence=list(record.get("evidence") or []),
        )

    def collect(self, dispatch_id: str) -> Mapping[str, Any]:
        record = self.runtime.load(dispatch_id)
        terminal_statuses = {
            "PASS",
            "COMPLETED",
            "FAIL",
            "FAILED",
            "BLOCKED",
            "CANCELLED",
        }
        if record.get("status") not in terminal_statuses:
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
        binding = validate_contract(record["contract"])
        self._append(
            phase="collect",
            binding=binding,
            status="PASS",
            dispatch_id=dispatch_id,
            evidence=[{"type": "terminal_result", "kind": result.get("schema")}],
        )
        return dict(result)

    def cancel(self, dispatch_id: str) -> LifecycleReceipt:
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
        record["status"] = "CANCELLED"
        self.runtime.save(dispatch_id, record)
        return self._append(
            phase="cancel",
            binding=binding,
            status="CANCELLED",
            dispatch_id=dispatch_id,
            evidence=[{"type": "adapter_cancellation", "confirmed": True}],
        )

    def cleanup(self, dispatch_id: str) -> LifecycleReceipt:
        record = self.runtime.load(dispatch_id)
        binding = validate_contract(record["contract"])
        deleted = self.runtime.delete(dispatch_id)
        return self._append(
            phase="cleanup",
            binding=binding,
            status="PASS",
            dispatch_id=dispatch_id,
            evidence=[{"type": "adapter_cleanup", "record_deleted": deleted}],
        )

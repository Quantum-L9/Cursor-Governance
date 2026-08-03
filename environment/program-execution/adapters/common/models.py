from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass, field
from typing import Any

from .digests import digest_object, normalize_digest, verify_embedded_digest

CAPABILITY_RECEIPT_SCHEMA = "program-execution-adapter.capability-receipt.v1"


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()


def parse_time(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


@dataclass(frozen=True)
class ProbeContext:
    repository_root: str
    runtime_root: str
    program_lock_digest: str
    requested_capabilities: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CapabilityReceipt:
    adapter_id: str
    adapter_version: str
    status: str
    capabilities: tuple[str, ...]
    program_lock_digest: str
    observed_at: str
    expires_at: str
    evidence: tuple[dict[str, Any], ...]
    blocked_reason: str | None
    receipt_digest: str

    @classmethod
    def create(
        cls,
        *,
        adapter_id: str,
        adapter_version: str,
        status: str,
        capabilities: list[str] | tuple[str, ...],
        program_lock_digest: str,
        ttl_seconds: int = 900,
        evidence: list[dict[str, Any]] | None = None,
        blocked_reason: str | None = None,
    ) -> CapabilityReceipt:
        observed = dt.datetime.now(dt.UTC).replace(microsecond=0)
        expires = observed + dt.timedelta(seconds=ttl_seconds)
        body = {
            "schema": CAPABILITY_RECEIPT_SCHEMA,
            "adapter_id": adapter_id,
            "adapter_version": adapter_version,
            "status": status,
            "capabilities": sorted(set(capabilities)),
            "program_lock_digest": normalize_digest(program_lock_digest),
            "observed_at": observed.isoformat(),
            "expires_at": expires.isoformat(),
            "evidence": evidence or [],
            "blocked_reason": blocked_reason,
        }
        return cls(
            adapter_id=adapter_id,
            adapter_version=adapter_version,
            status=status,
            capabilities=tuple(body["capabilities"]),
            program_lock_digest=body["program_lock_digest"],
            observed_at=body["observed_at"],
            expires_at=body["expires_at"],
            evidence=tuple(body["evidence"]),
            blocked_reason=blocked_reason,
            receipt_digest=digest_object(body),
        )

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> CapabilityReceipt:
        if value.get("schema") != CAPABILITY_RECEIPT_SCHEMA:
            raise ValueError("unsupported capability receipt schema")
        receipt = cls(
            adapter_id=str(value["adapter_id"]),
            adapter_version=str(value["adapter_version"]),
            status=str(value["status"]),
            capabilities=tuple(str(item) for item in value["capabilities"]),
            program_lock_digest=normalize_digest(str(value["program_lock_digest"])),
            observed_at=str(value["observed_at"]),
            expires_at=str(value["expires_at"]),
            evidence=tuple(dict(item) for item in value.get("evidence") or []),
            blocked_reason=(
                str(value["blocked_reason"]) if value.get("blocked_reason") is not None else None
            ),
            receipt_digest=normalize_digest(str(value["receipt_digest"])),
        )
        if not receipt.is_valid():
            raise ValueError("capability receipt digest mismatch")
        return receipt

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": CAPABILITY_RECEIPT_SCHEMA,
            "adapter_id": self.adapter_id,
            "adapter_version": self.adapter_version,
            "status": self.status,
            "capabilities": list(self.capabilities),
            "program_lock_digest": self.program_lock_digest,
            "observed_at": self.observed_at,
            "expires_at": self.expires_at,
            "evidence": list(self.evidence),
            "blocked_reason": self.blocked_reason,
            "receipt_digest": self.receipt_digest,
        }

    def is_fresh(self, at: dt.datetime | None = None) -> bool:
        point = at or dt.datetime.now(dt.UTC)
        return self.status == "PASS" and parse_time(self.expires_at) > point

    def is_valid(self) -> bool:
        return verify_embedded_digest(self.to_dict(), "receipt_digest")


@dataclass(frozen=True)
class LifecycleReceipt:
    receipt_id: str
    adapter_id: str
    adapter_version: str
    phase: str
    program_lock_digest: str
    rendered_contract_digest: str | None
    task_id: str | None
    dispatch_id: str | None
    status: str
    canonical_error_code: str | None
    adapter_error_code: str | None
    evidence: tuple[dict[str, Any], ...]
    created_at: str
    previous_receipt_digest: str | None
    receipt_digest: str

    @classmethod
    def create(
        cls,
        *,
        adapter_id: str,
        adapter_version: str,
        phase: str,
        program_lock_digest: str,
        status: str,
        rendered_contract_digest: str | None = None,
        task_id: str | None = None,
        dispatch_id: str | None = None,
        canonical_error_code: str | None = None,
        adapter_error_code: str | None = None,
        evidence: list[dict[str, Any]] | None = None,
        previous_receipt_digest: str | None = None,
    ) -> LifecycleReceipt:
        body = {
            "schema": "program-execution-adapter.lifecycle-receipt.v1",
            "receipt_id": "LCR-" + uuid.uuid4().hex,
            "adapter_id": adapter_id,
            "adapter_version": adapter_version,
            "phase": phase,
            "program_lock_digest": normalize_digest(program_lock_digest),
            "rendered_contract_digest": (
                normalize_digest(rendered_contract_digest) if rendered_contract_digest else None
            ),
            "task_id": task_id,
            "dispatch_id": dispatch_id,
            "status": status,
            "canonical_error_code": canonical_error_code,
            "adapter_error_code": adapter_error_code,
            "evidence": evidence or [],
            "created_at": utc_now(),
            "previous_receipt_digest": (
                normalize_digest(previous_receipt_digest) if previous_receipt_digest else None
            ),
        }
        values = {key: value for key, value in body.items() if key not in {"schema", "evidence"}}
        return cls(
            **values,
            evidence=tuple(body["evidence"]),
            receipt_digest=digest_object(body),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "program-execution-adapter.lifecycle-receipt.v1",
            "receipt_id": self.receipt_id,
            "adapter_id": self.adapter_id,
            "adapter_version": self.adapter_version,
            "phase": self.phase,
            "program_lock_digest": self.program_lock_digest,
            "rendered_contract_digest": self.rendered_contract_digest,
            "task_id": self.task_id,
            "dispatch_id": self.dispatch_id,
            "status": self.status,
            "canonical_error_code": self.canonical_error_code,
            "adapter_error_code": self.adapter_error_code,
            "evidence": list(self.evidence),
            "created_at": self.created_at,
            "previous_receipt_digest": self.previous_receipt_digest,
            "receipt_digest": self.receipt_digest,
        }

    def is_valid(self) -> bool:
        return verify_embedded_digest(self.to_dict(), "receipt_digest")

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class CanonicalErrorCode(StrEnum):
    PROGRAM_LOCK_STALE = "PROGRAM_LOCK_STALE"
    AUTHORIZATION_INFLATION = "AUTHORIZATION_INFLATION"
    REPOSITORY_STATE_DRIFT = "REPOSITORY_STATE_DRIFT"
    SCOPE_VIOLATION = "SCOPE_VIOLATION"
    VALIDATION_FAILURE = "VALIDATION_FAILURE"
    EVIDENCE_INVALID_OR_STALE = "EVIDENCE_INVALID_OR_STALE"
    LEASE_EXPIRED = "LEASE_EXPIRED"
    CAPABILITY_UNSUPPORTED = "CAPABILITY_UNSUPPORTED"
    IDENTITY_BINDING_MISSING = "IDENTITY_BINDING_MISSING"
    CREDENTIAL_UNAVAILABLE = "CREDENTIAL_UNAVAILABLE"
    CANCELLATION_UNSUPPORTED = "CANCELLATION_UNSUPPORTED"


@dataclass(frozen=True)
class AdapterFailure(Exception):
    code: CanonicalErrorCode
    message: str
    adapter_code: str | None = None
    transient: bool = False
    evidence: list[dict[str, Any]] | None = None

    def __str__(self) -> str:
        return f"{self.code.value}: {self.message}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "FAIL",
            "canonical_error_code": self.code.value,
            "adapter_error_code": self.adapter_code,
            "message": self.message,
            "transient": self.transient,
            "evidence": self.evidence or [],
        }

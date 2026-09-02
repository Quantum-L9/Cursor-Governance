from __future__ import annotations

import functools
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml


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


ERROR_MAPPING_PATH = (
    Path(__file__).resolve().parents[1] / "registry" / "EXECUTION_ERROR_MAPPING.yaml"
)
ERROR_MAPPING_SCHEMA = "program-execution-adapter.error-mapping.v1"


@functools.lru_cache(maxsize=1)
def load_error_mapping() -> dict[str, CanonicalErrorCode]:
    """Adapter error code -> canonical code, from EXECUTION_ERROR_MAPPING.yaml.

    The registry existed and nothing read it: adapters reported failures as
    free text and every lifecycle receipt carried a null canonical code. A
    mapping to a code the taxonomy does not define is a registry defect and
    is refused at load.
    """
    value = yaml.safe_load(ERROR_MAPPING_PATH.read_text(encoding="utf-8")) or {}
    if value.get("schema") != ERROR_MAPPING_SCHEMA:
        raise ValueError(f"error mapping schema mismatch: {value.get('schema')!r}")
    mapping: dict[str, CanonicalErrorCode] = {}
    for adapter_code, canonical in (value.get("mappings") or {}).items():
        try:
            mapping[str(adapter_code)] = CanonicalErrorCode(str(canonical))
        except ValueError as exc:
            raise ValueError(
                f"error mapping {adapter_code!r} names unknown canonical code {canonical!r}"
            ) from exc
    return mapping


def canonical_code_for(adapter_code: str | None) -> CanonicalErrorCode | None:
    """The canonical code an adapter code maps to, or None when unmapped."""
    if not adapter_code:
        return None
    return load_error_mapping().get(str(adapter_code))

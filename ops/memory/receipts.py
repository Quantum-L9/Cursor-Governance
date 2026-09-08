"""Consumer-side parsing of canonical memory receipts.

These are *views* over the JSON the memory-owned CLI prints, not a second
schema. Each view keeps the complete receipt under ``raw`` and exposes only
the fields Cursor session composition needs.

They are deliberately **not** the validation authority. Canonical validation
lives in :mod:`ops.memory.canonical_validation`, which checks the raw payload
against the schema the *bound release* exported, and the client runs it before
any view here reads a field (audit CG-P1-02). An in-process
``import l9_graphite_memory.contracts`` cannot serve that purpose: in pinned
mode the memory runtime is a different interpreter, so such a check can only
ever decline, and a validator that declines is how structural acceptance
becomes the silent default.

A receipt that lacks the fields a view requires raises
:class:`InvalidReceiptError`; the client maps that to ``INVALID_RECEIPT`` and
never treats it as success (INV-06).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

#: Canonical write statuses that count as "the record exists" (accepted set).
ACCEPTED_WRITE_STATUSES = frozenset({"admitted", "duplicate"})
#: Candidate ingestion statuses that mean the candidate is durably stored.
ACCEPTED_CANDIDATE_STATUSES = frozenset({"admitted", "duplicate"})


class InvalidReceiptError(ValueError):
    """The memory transport returned something that is not a canonical receipt."""


def _require(raw: dict[str, Any], *keys: str) -> None:
    missing = [key for key in keys if key not in raw]
    if missing:
        raise InvalidReceiptError(f"receipt is missing required fields: {', '.join(missing)}")


def _optional_str(value: Any) -> str | None:
    return None if value is None else str(value)


def result_digest(payload: Any) -> str:
    """Stable digest of a receipt for integration evidence (never the content)."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CapabilitiesReceipt:
    package: str
    package_version: str
    schema_version: str
    contract_version: str
    cli_operations: dict[str, str]
    mcp_operations: dict[str, str]
    exit_codes: dict[str, int]
    raw: dict[str, Any] = field(repr=False)

    @classmethod
    def parse(cls, raw: dict[str, Any]) -> CapabilitiesReceipt:
        _require(raw, "package", "package_version", "contract_version", "transports")
        transports = {
            str(item.get("transport")): dict(item.get("operations") or {})
            for item in raw.get("transports") or []
            if isinstance(item, dict)
        }
        return cls(
            package=str(raw["package"]),
            package_version=str(raw["package_version"]),
            schema_version=str(raw.get("schema_version", "")),
            contract_version=str(raw["contract_version"]),
            cli_operations=transports.get("cli", {}),
            mcp_operations=transports.get("mcp", {}),
            exit_codes={str(k): int(v) for k, v in (raw.get("exit_codes") or {}).items()},
            raw=raw,
        )


@dataclass(frozen=True)
class HealthReceipt:
    status: str
    package_version: str
    contract_version: str | None
    store_healthy: bool
    projection_name: str | None
    projection_healthy: bool | None
    degraded_reasons: tuple[str, ...]
    outbox_backlog: int
    raw: dict[str, Any] = field(repr=False)

    @classmethod
    def parse(cls, raw: dict[str, Any]) -> HealthReceipt:
        _require(raw, "status", "package_version", "store", "projection")
        store = raw.get("store") or {}
        projection = raw.get("projection") or {}
        projection_name = _optional_str(projection.get("name"))
        return cls(
            status=str(raw["status"]),
            package_version=str(raw["package_version"]),
            contract_version=_optional_str(raw.get("contract_version")),
            store_healthy=bool(store.get("healthy")),
            projection_name=projection_name,
            projection_healthy=(
                None if projection_name in (None, "none") else bool(projection.get("healthy"))
            ),
            degraded_reasons=tuple(str(item) for item in raw.get("degraded_reasons") or ()),
            outbox_backlog=int(raw.get("outbox_backlog") or 0),
            raw=raw,
        )

    @property
    def canonical_ready(self) -> bool:
        return self.store_healthy and self.status in {"complete", "partial"}


@dataclass(frozen=True)
class ResolveReceipt:
    group_id: str | None
    method: str
    readonly: bool
    error: str | None
    raw: dict[str, Any] = field(repr=False)

    @classmethod
    def parse(cls, raw: dict[str, Any]) -> ResolveReceipt:
        _require(raw, "method", "readonly")
        return cls(
            group_id=_optional_str(raw.get("group_id")),
            method=str(raw["method"]),
            readonly=bool(raw["readonly"]),
            error=_optional_str(raw.get("error")),
            raw=raw,
        )


@dataclass(frozen=True)
class HydrationSection:
    memory_class: str
    content: str
    record_ids: tuple[str, ...]
    tokens_estimated: int
    highest_score: float


@dataclass(frozen=True)
class HydrationReceipt:
    receipt_id: str
    status: str
    task: str
    sections: tuple[HydrationSection, ...]
    token_budget: int
    tokens_used: int
    result_digest: str
    warnings: tuple[str, ...]
    raw: dict[str, Any] = field(repr=False)

    @classmethod
    def parse(cls, raw: dict[str, Any]) -> HydrationReceipt:
        _require(raw, "receipt_id", "status", "task", "result_digest", "sections")
        sections = tuple(
            HydrationSection(
                memory_class=str(item.get("memory_class", "")),
                content=str(item.get("content", "")),
                record_ids=tuple(str(value) for value in item.get("record_ids") or ()),
                tokens_estimated=int(item.get("tokens_estimated") or 0),
                highest_score=float(item.get("highest_score") or 0.0),
            )
            for item in raw.get("sections") or []
            if isinstance(item, dict)
        )
        return cls(
            receipt_id=str(raw["receipt_id"]),
            status=str(raw["status"]),
            task=str(raw["task"]),
            sections=sections,
            token_budget=int(raw.get("token_budget") or 0),
            tokens_used=int(raw.get("tokens_used") or 0),
            result_digest=str(raw["result_digest"]),
            warnings=tuple(str(item) for item in raw.get("warnings") or ()),
            raw=raw,
        )

    @property
    def record_ids(self) -> tuple[str, ...]:
        seen: dict[str, None] = {}
        for section in self.sections:
            for record_id in section.record_ids:
                seen.setdefault(record_id, None)
        return tuple(seen)

    @property
    def has_hits(self) -> bool:
        return bool(self.record_ids)


@dataclass(frozen=True)
class SearchRecordView:
    """The canonical record inside a search hit (full metadata, never a summary)."""

    record_id: str
    namespace: str
    memory_class: str
    state: str
    content: str
    tags: tuple[str, ...]
    metadata: dict[str, Any]
    created_at: str | None
    recorded_at: str | None
    raw: dict[str, Any] = field(repr=False)

    @classmethod
    def parse(cls, raw: dict[str, Any]) -> SearchRecordView:
        _require(raw, "record_id", "namespace", "memory_class")
        temporal = raw.get("temporal") or {}
        metadata = raw.get("metadata")
        return cls(
            record_id=str(raw["record_id"]),
            namespace=str(raw["namespace"]),
            memory_class=str(raw["memory_class"]),
            state=str(raw.get("state") or ""),
            content=str(raw.get("content") or ""),
            tags=tuple(str(item) for item in raw.get("tags") or ()),
            metadata=dict(metadata) if isinstance(metadata, dict) else {},
            created_at=_optional_str(raw.get("created_at")),
            recorded_at=_optional_str(temporal.get("recorded_at")) if temporal else None,
            raw=raw,
        )


@dataclass(frozen=True)
class SearchHitView:
    record: SearchRecordView
    score: float
    matched_by: tuple[str, ...]


@dataclass(frozen=True)
class SearchReceipt:
    receipt_id: str
    status: str
    query: str
    namespaces_authorized: tuple[str, ...]
    hits: tuple[SearchHitView, ...]
    raw: dict[str, Any] = field(repr=False)

    @classmethod
    def parse(cls, raw: dict[str, Any]) -> SearchReceipt:
        _require(raw, "receipt_id", "status", "query", "namespaces_authorized")
        hits: list[SearchHitView] = []
        for item in raw.get("hits") or []:
            if not isinstance(item, dict) or not isinstance(item.get("record"), dict):
                raise InvalidReceiptError("search hit without a record")
            hits.append(
                SearchHitView(
                    record=SearchRecordView.parse(item["record"]),
                    score=float(item.get("score") or 0.0),
                    matched_by=tuple(str(value) for value in item.get("matched_by") or ()),
                )
            )
        return cls(
            receipt_id=str(raw["receipt_id"]),
            status=str(raw["status"]),
            query=str(raw["query"]),
            namespaces_authorized=tuple(str(v) for v in raw["namespaces_authorized"]),
            hits=tuple(hits),
            raw=raw,
        )

    @property
    def has_hits(self) -> bool:
        return bool(self.hits)


@dataclass(frozen=True)
class WriteReceipt:
    """View over the memory write receipt (generic ``write``)."""

    receipt_id: str
    status: str
    namespace: str
    record_id: str | None
    idempotency_key: str | None
    admission_reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    raw: dict[str, Any] = field(repr=False)

    @classmethod
    def parse(cls, raw: dict[str, Any]) -> WriteReceipt:
        _require(raw, "receipt_id", "status", "namespace")
        admission = raw.get("admission") or {}
        reasons = admission.get("reasons") if isinstance(admission, dict) else ()
        return cls(
            receipt_id=str(raw["receipt_id"]),
            status=str(raw["status"]),
            namespace=str(raw["namespace"]),
            record_id=_optional_str(raw.get("record_id")),
            idempotency_key=_optional_str(raw.get("idempotency_key")),
            admission_reasons=tuple(str(item) for item in reasons or ()),
            warnings=tuple(str(item) for item in raw.get("warnings") or ()),
            raw=raw,
        )

    @property
    def accepted(self) -> bool:
        return self.status in ACCEPTED_WRITE_STATUSES and self.record_id is not None


@dataclass(frozen=True)
class CandidateReceipt:
    status: str
    candidate_id: str
    namespace: str
    record_id: str | None
    write_receipt_id: str | None
    storage_committed: bool
    memory_state: str | None
    reason: str | None
    raw: dict[str, Any] = field(repr=False)
    #: Records memory superseded on admission (the candidate named them in
    #: ``supersedes``; memory validated and applied the transition). Empty on
    #: every other verdict — a refused supersession rejects the candidate.
    superseded_record_ids: tuple[str, ...] = ()

    @classmethod
    def parse(cls, raw: dict[str, Any]) -> CandidateReceipt:
        _require(raw, "status", "candidate_id", "namespace")
        return cls(
            status=str(raw["status"]),
            candidate_id=str(raw["candidate_id"]),
            namespace=str(raw["namespace"]),
            record_id=_optional_str(raw.get("record_id")),
            write_receipt_id=_optional_str(raw.get("write_receipt_id")),
            storage_committed=bool(raw.get("storage_committed")),
            memory_state=_optional_str(raw.get("memory_state")),
            reason=_optional_str(raw.get("reason")),
            raw=raw,
            superseded_record_ids=tuple(
                str(item) for item in raw.get("superseded_record_ids") or ()
            ),
        )

    @property
    def accepted(self) -> bool:
        return self.status in ACCEPTED_CANDIDATE_STATUSES and self.record_id is not None


@dataclass(frozen=True)
class CloseReceipt:
    receipt_id: str
    status: str
    namespace: str
    record_id: str | None
    write_receipt_id: str | None
    replayed: bool
    raw: dict[str, Any] = field(repr=False)
    #: Replay forensics (audit P2-01): on an idempotent replay memory reports
    #: whether the replayed payload matched the stored record, with both
    #: digests. ``None`` when the close was not a replay (or the runtime
    #: predates the field); ``False`` is payload drift, which the caller must
    #: surface — an idempotent status alone never proves the same request.
    replay_payload_matched: bool | None = None
    stored_digest: str | None = None
    replay_digest: str | None = None
    warnings: tuple[str, ...] = ()

    @classmethod
    def parse(cls, raw: dict[str, Any]) -> CloseReceipt:
        _require(raw, "receipt_id", "status", "namespace", "write_receipt_id")
        matched = raw.get("replay_payload_matched")
        return cls(
            receipt_id=str(raw["receipt_id"]),
            status=str(raw["status"]),
            namespace=str(raw["namespace"]),
            record_id=_optional_str(raw.get("record_id")),
            write_receipt_id=_optional_str(raw.get("write_receipt_id")),
            replayed=bool(raw.get("replayed", False)),
            raw=raw,
            replay_payload_matched=None if matched is None else bool(matched),
            stored_digest=_optional_str(raw.get("stored_digest")),
            replay_digest=_optional_str(raw.get("replay_digest")),
            warnings=tuple(str(item) for item in raw.get("warnings") or ()),
        )

    @property
    def committed(self) -> bool:
        """Only a COMPLETE close with a record is a canonical close (INV-06)."""

        return self.status == "complete" and self.record_id is not None

    @property
    def payload_drifted(self) -> bool:
        """A replay whose payload memory proved different from the stored close."""

        return self.replayed and self.replay_payload_matched is False


@dataclass(frozen=True)
class ConflictsReceipt:
    namespace: str
    status: str
    conflict_count: int
    checked_record_count: int
    snapshot_digest: str
    raw: dict[str, Any] = field(repr=False)

    @classmethod
    def parse(cls, raw: dict[str, Any]) -> ConflictsReceipt:
        _require(raw, "namespace", "conflicts", "snapshot_digest")
        return cls(
            namespace=str(raw["namespace"]),
            status=str(raw.get("status", "complete")),
            conflict_count=len(raw.get("conflicts") or []),
            checked_record_count=int(raw.get("checked_record_count") or 0),
            snapshot_digest=str(raw["snapshot_digest"]),
            raw=raw,
        )

    @property
    def has_conflicts(self) -> bool:
        return self.conflict_count > 0


@dataclass(frozen=True)
class PhaseLockReceipt:
    lock_id: str
    namespace: str
    task_signature: str
    granted: bool
    snapshot_digest: str
    expires_at: str
    raw: dict[str, Any] = field(repr=False)

    @classmethod
    def parse(cls, raw: dict[str, Any]) -> PhaseLockReceipt:
        _require(raw, "lock_id", "namespace", "task_signature", "granted", "expires_at")
        return cls(
            lock_id=str(raw["lock_id"]),
            namespace=str(raw["namespace"]),
            task_signature=str(raw["task_signature"]),
            granted=bool(raw["granted"]),
            snapshot_digest=str(raw.get("snapshot_digest", "")),
            expires_at=str(raw["expires_at"]),
            raw=raw,
        )


@dataclass(frozen=True)
class PhaseLockVerificationReceipt:
    namespace: str
    task_signature: str
    valid: bool
    reasons: tuple[str, ...]
    current_snapshot_digest: str
    raw: dict[str, Any] = field(repr=False)

    @classmethod
    def parse(cls, raw: dict[str, Any]) -> PhaseLockVerificationReceipt:
        _require(raw, "namespace", "task_signature", "valid", "reasons")
        return cls(
            namespace=str(raw["namespace"]),
            task_signature=str(raw["task_signature"]),
            valid=bool(raw["valid"]),
            reasons=tuple(str(item) for item in raw.get("reasons") or ()),
            current_snapshot_digest=str(raw.get("current_snapshot_digest", "")),
            raw=raw,
        )


__all__ = [
    "ACCEPTED_CANDIDATE_STATUSES",
    "ACCEPTED_WRITE_STATUSES",
    "CandidateReceipt",
    "CapabilitiesReceipt",
    "CloseReceipt",
    "ConflictsReceipt",
    "HealthReceipt",
    "HydrationReceipt",
    "HydrationSection",
    "InvalidReceiptError",
    "PhaseLockReceipt",
    "PhaseLockVerificationReceipt",
    "ResolveReceipt",
    "SearchHitView",
    "SearchReceipt",
    "SearchRecordView",
    "WriteReceipt",
    "result_digest",
]

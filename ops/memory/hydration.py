"""Canonical session hydration (plan §10, §12; campaign stages C3/C4).

The only source of resume memory for a Cursor or Claude session is the
canonical memory control plane:

    repository identity + requested namespaces
        → memory.health            (interpreted in layers, never "Graphiti is up")
        → memory.hydrate           (bounded context; fan-in requested, memory authorizes)
        → memory.search --tag session_continuation
                                   (typed records; the latest valid capsule is evidence)
        → CanonicalHydration       (what Cursor composes its packet from)

Nothing here reruns a provider search, fills gaps from a projection, revives
a superseded record, or overrides record lifecycle state (S-06). A
continuation capsule is evidence: when the checkout has moved on since it
was written it is reported ``stale`` and the current repository state wins
(plan §12, "Repository-state precedence").

Failure is classified, never collapsed into "memory empty" (S-07):
``NO_HITS`` is a normal empty answer; ``CANONICAL_UNAVAILABLE``,
``UNAUTHORIZED_NAMESPACE``, ``TIMEOUT``, ``INVALID_RECEIPT`` and
``BINDING_FAILED`` are not.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ops.memory.control_plane_client import (
    MemoryControlPlaneClient,
    OperationOutcome,
    OutcomeStatus,
)
from ops.memory.namespace_context import (
    NamespaceContext,
    repository_state_digest,
    resolve_namespace_context,
)
from ops.memory.receipts import SearchHitView, result_digest
from ops.memory.runtime_binding import RuntimeBinding, resolve_runtime_binding
from ops.memory.session_contracts import (
    CANDIDATE_CLASS,
    CONTINUATION_SCHEMA,
    ContinuationCapsuleV2,
    ContinuationContractError,
    continuation_from_record_metadata,
    task_signature_for,
)

#: Cursor-side outcome: identity resolved to no namespace Cursor may request.
STATUS_NAMESPACE_UNRESOLVED = "NAMESPACE_UNRESOLVED"
#: The tag memory stamps on an admitted continuation candidate (its class).
CONTINUATION_TAG = CANDIDATE_CLASS
SOURCE_CANONICAL = "canonical"
#: Migration-only marker for a continuation read outside the canonical plane
#: (plan §13). Never produced by this module; consumers that still carry the
#: legacy reader tag their result with it so it can never pass as canonical.
SOURCE_LEGACY_UNVERIFIED = "legacy_unverified"

_OK_STATUSES = frozenset({OutcomeStatus.OK.value, OutcomeStatus.NO_HITS.value})


@dataclass(frozen=True)
class ContinuationEvidence:
    record_id: str
    capsule: ContinuationCapsuleV2
    stale: bool
    recorded_at: str | None
    source: str = SOURCE_CANONICAL

    def as_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "session_id": self.capsule.session_id,
            "task_signature": self.capsule.task_signature,
            "repository_state_digest": self.capsule.repository_state_digest,
            "created_at": self.capsule.created_at,
            "recorded_at": self.recorded_at,
            "stale": self.stale,
            "source": self.source,
            "schema": self.capsule.schema,
            "digest": self.capsule.digest(),
        }


@dataclass(frozen=True)
class CanonicalHydration:
    status: str
    namespace_context: NamespaceContext
    requested_namespaces: tuple[str, ...]
    repository_state_digest: str | None
    task_signature: str | None
    context_sections: tuple[tuple[str, str], ...] = ()
    record_ids: tuple[str, ...] = ()
    continuation: ContinuationEvidence | None = None
    continuation_candidates: int = 0
    projection_status: str | None = None
    fan_in_denied: str | None = None
    error: str | None = None
    calls: int = 0
    latency_ms: int = 0
    hydrate_receipt_digest: str | None = None
    integration_receipts: tuple[dict[str, Any], ...] = field(default_factory=tuple, repr=False)
    warnings: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.status in _OK_STATUSES

    @property
    def degraded(self) -> bool:
        return not self.ok

    @property
    def has_hits(self) -> bool:
        return bool(self.record_ids)

    def as_dict(self) -> dict[str, Any]:
        """Integration-receipt shape (plan §31): ids, digests, statuses; no content."""

        return {
            "status": self.status,
            "transport": "cli",
            "namespace_context": self.namespace_context.as_dict(),
            "requested_namespaces": list(self.requested_namespaces),
            "repository_state_digest": self.repository_state_digest,
            "task_signature": self.task_signature,
            "record_ids": list(self.record_ids),
            "record_count": len(self.record_ids),
            "continuation": self.continuation.as_dict() if self.continuation else None,
            "continuation_candidates": self.continuation_candidates,
            "projection_status": self.projection_status,
            "fan_in_denied": self.fan_in_denied,
            "error": self.error,
            "calls": self.calls,
            "latency_ms": self.latency_ms,
            "hydrate_receipt_digest": self.hydrate_receipt_digest,
            "warnings": list(self.warnings),
            "timestamp": datetime.now(UTC).isoformat(),
        }


def select_continuation(
    hits: Sequence[SearchHitView], *, current_repository_state: str | None
) -> tuple[ContinuationEvidence | None, int, tuple[str, ...]]:
    """The newest valid ``cursor.continuation/v2`` capsule among typed records.

    Returns ``(evidence, candidate_count, warnings)``. Records that claim the
    schema but fail validation are skipped and named; nothing is repaired or
    guessed. Ordering is the canonical record's own ``created_at`` (falling
    back to ``recorded_at``), never the capsule's self-reported clock.
    """

    warnings: list[str] = []
    typed: list[tuple[str, SearchHitView, ContinuationCapsuleV2]] = []
    for hit in hits:
        record = hit.record
        if record.metadata.get("payload_schema") != CONTINUATION_SCHEMA:
            continue
        try:
            capsule = continuation_from_record_metadata(record.metadata)
        except ContinuationContractError as exc:
            warnings.append(f"continuation record {record.record_id[:8]} malformed: {exc}")
            continue
        if capsule is None:
            continue
        order_key = record.created_at or record.recorded_at or ""
        typed.append((order_key, hit, capsule))
    if not typed:
        return None, 0, tuple(warnings)
    typed.sort(key=lambda item: item[0], reverse=True)
    _, newest, capsule = typed[0]
    stale = bool(current_repository_state) and capsule.is_stale_for(str(current_repository_state))
    evidence = ContinuationEvidence(
        record_id=newest.record.record_id,
        capsule=capsule,
        stale=stale,
        recorded_at=newest.record.recorded_at or newest.record.created_at,
    )
    return evidence, len(typed), tuple(warnings)


def _projection_status(health: OperationOutcome | None) -> str | None:
    if health is None:
        return None
    return health.integration_receipt.get("projection_status")


def canonical_hydrate(
    workspace: str | Path,
    *,
    task: str,
    session_id: str | None = None,
    client: MemoryControlPlaneClient | None = None,
    binding: RuntimeBinding | None = None,
    explicit_namespace: str | None = None,
    token_budget: int = 1_200,
    max_records: int = 40,
    continuation_limit: int = 10,
    check_health: bool = True,
) -> CanonicalHydration:
    """Hydrate a session from canonical memory and return typed evidence.

    ``client`` may be injected (tests, diagnostics); otherwise the bound
    runtime is resolved through the binding manifest. Every CLI call's
    integration receipt is kept so the caller can persist observability
    without logging memory content.
    """

    started = time.monotonic()
    workspace_path = str(Path(workspace).expanduser().resolve())
    context = resolve_namespace_context(workspace_path, explicit=explicit_namespace)
    head = repository_state_digest(Path(workspace_path))
    signature = (
        task_signature_for(task, context.repository_identity)
        if context.repository_identity
        else None
    )
    receipts: list[dict[str, Any]] = []
    warnings: list[str] = list(context.warnings)

    def finish(
        status: str,
        *,
        error: str | None = None,
        requested: Sequence[str] = (),
        health: OperationOutcome | None = None,
        **extra: Any,
    ) -> CanonicalHydration:
        return CanonicalHydration(
            status=status,
            namespace_context=context,
            requested_namespaces=tuple(requested),
            repository_state_digest=head,
            task_signature=signature,
            projection_status=_projection_status(health),
            error=error,
            calls=len(receipts),
            latency_ms=int((time.monotonic() - started) * 1000),
            integration_receipts=tuple(receipts),
            warnings=tuple(warnings),
            **extra,
        )

    if not context.read_namespace_hints:
        return finish(STATUS_NAMESPACE_UNRESOLVED, error="no namespace to request")

    if client is None:
        binding = binding or resolve_runtime_binding()
        client = MemoryControlPlaneClient(binding, session_id=session_id)
    if not client.binding.ok:
        return finish(
            OutcomeStatus.BINDING_FAILED.value,
            error="; ".join(client.binding.reasons) or "memory runtime unbound",
        )

    health: OperationOutcome | None = None
    if check_health:
        health = client.health()
        receipts.append(health.integration_receipt)
        if health.status in {
            OutcomeStatus.CANONICAL_UNAVAILABLE,
            OutcomeStatus.TIMEOUT,
            OutcomeStatus.INVALID_RECEIPT,
            OutcomeStatus.BINDING_FAILED,
        }:
            return finish(health.status.value, error=health.error, health=health)
        if health.status is OutcomeStatus.PARTIAL_PROJECTION_DEGRADED:
            warnings.append("projection degraded; canonical operations continue")

    primary = context.write_namespace_hint
    requested = tuple(context.read_namespace_hints)
    hydrate = client.hydrate(
        task,
        workspace=workspace_path,
        write_namespace_hint=primary,
        read_namespace_hints=requested,
        token_budget=token_budget,
        max_records=max_records,
        task_signature=signature,
    )
    receipts.append(hydrate.integration_receipt)
    fan_in_denied: str | None = None
    if hydrate.status is OutcomeStatus.UNAUTHORIZED_NAMESPACE and primary and len(requested) > 1:
        # Memory refused the fan-in; the narrower request to the same
        # authority is the repository's own namespace. Never a fallback to a
        # different store, and the denial stays visible.
        fan_in_denied = hydrate.error
        requested = (primary,)
        hydrate = client.hydrate(
            task,
            workspace=workspace_path,
            write_namespace_hint=primary,
            read_namespace_hints=requested,
            token_budget=token_budget,
            max_records=max_records,
            task_signature=signature,
        )
        receipts.append(hydrate.integration_receipt)
    if hydrate.status not in (OutcomeStatus.OK, OutcomeStatus.NO_HITS):
        return finish(
            hydrate.status.value,
            error=hydrate.error,
            requested=requested,
            health=health,
            fan_in_denied=fan_in_denied,
        )

    sections = tuple(
        (section.memory_class, section.content)
        for section in hydrate.receipt.sections
        if section.content
    )
    record_ids = tuple(hydrate.receipt.record_ids)

    continuation: ContinuationEvidence | None = None
    candidates = 0
    if primary:
        search = client.search(
            task,
            workspace=workspace_path,
            write_namespace_hint=primary,
            read_namespace_hints=(primary,),
            tags=(CONTINUATION_TAG,),
            limit=continuation_limit,
            task_signature=signature,
        )
        receipts.append(search.integration_receipt)
        if search.status is OutcomeStatus.OK:
            continuation, candidates, selection_warnings = select_continuation(
                search.receipt.hits, current_repository_state=head
            )
            warnings.extend(selection_warnings)
        elif search.status is not OutcomeStatus.NO_HITS:
            warnings.append(
                f"continuation search {search.status.value}: {search.error or 'no detail'}"
            )
    else:
        warnings.append("no write namespace hint: continuation not requested")

    status = OutcomeStatus.OK.value if (record_ids or continuation) else OutcomeStatus.NO_HITS.value
    return finish(
        status,
        requested=requested,
        health=health,
        context_sections=sections,
        record_ids=record_ids,
        continuation=continuation,
        continuation_candidates=candidates,
        fan_in_denied=fan_in_denied,
        hydrate_receipt_digest=result_digest(hydrate.receipt.raw),
    )


__all__ = [
    "CONTINUATION_TAG",
    "SOURCE_CANONICAL",
    "SOURCE_LEGACY_UNVERIFIED",
    "STATUS_NAMESPACE_UNRESOLVED",
    "CanonicalHydration",
    "ContinuationEvidence",
    "canonical_hydrate",
    "select_continuation",
]

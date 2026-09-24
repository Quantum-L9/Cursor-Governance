"""Thin consumer adapter over the memory-owned CLI (transport A, plan §5).

``Cursor request → memory-owned command → typed, validated receipt``.

Forbidden here, by design: ranking, deduplication, provider translation,
HTTP provider calls, admission rules, namespace authorization, conflict
discovery, projection logic, durable queues. The exit code and the receipt
the CLI prints are the verdict; this module only classifies them into the
failure taxonomy of plan §10 (S-07) so a caller never collapses
``CANONICAL_UNAVAILABLE`` into "memory empty".
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from ops.memory.canonical_validation import CanonicalValidator, ValidationUnavailable
from ops.memory.hook_envelope import HookEnvelope, envelope_for, operator_principal
from ops.memory.receipts import (
    CandidateReceipt,
    CapabilitiesReceipt,
    CloseReceipt,
    ConflictsReceipt,
    DistillationReceipt,
    HealthReceipt,
    HydrationReceipt,
    InvalidReceiptError,
    PhaseLockReceipt,
    PhaseLockVerificationReceipt,
    ResolveReceipt,
    SearchReceipt,
    WriteReceipt,
    result_digest,
)
from ops.memory.runtime_binding import Runner, RuntimeBinding, default_runner
from ops.memory.search_identity import (
    SearchRequest,
    require_search_identity,
    verify_request_identity,
)

TRANSPORT = "cli"

# Exit codes the memory CLI documents in its capabilities receipt.
EXIT_COMMITTED = 0
EXIT_ERROR = 1
EXIT_FAILED = 2
EXIT_DRY_RUN = 3
EXIT_CANDIDATE_REJECTED = 7

#: The options ``l9-memory distill`` parses at the bound ref (memory-binding
#: ``bounded_hook_cli_commands.distill.options``). There is no input record
#: cap on this release; the hook lane bounds records with a ``--dry-run``
#: preflight instead (see ``MemoryControlPlaneClient.distill``). Anything the
#: client emits outside this set is a cross-repository contract break.
DISTILL_CLI_OPTIONS = frozenset({"--group-id", "--repository", "--dry-run"})

#: The recency selector (ADR-0035). The bound 2.4.0 parser does not define it —
#: it has only ``--recorded-before`` — and answers ``unrecognized arguments``
#: with exit 2. Emitting it unconditionally turned every SessionStart and
#: sessionEnd agent-lane search into ``INVALID_RECEIPT`` and dropped the 24h
#: agent-lane records on the floor. ``search`` now learns once per process and
#: memory CLI that the flag is refused, re-asks without it, and applies the
#: same floor to the hits itself.
RECORDED_AFTER_OPTION = "--recorded-after"
_RECORDED_AFTER_REFUSED: set[str] = set()

# Provider transport variables a stale machine environment may still carry.
# Assembled from parts on purpose: the boundary never spells the provider
# vocabulary, and the secret-isolation suite asserts exactly that.
PROVIDER_TRANSPORT_ENV = frozenset({"GRAPHITI_MCP_" + "URL", "GRAPHITI_MCP_" + "TOKEN"})

_UNAUTHORIZED_ERRORS = frozenset({"AuthorizationError"})
_UNAVAILABLE_ERRORS = frozenset(
    {"ConfigurationError", "StoreError", "OSError", "ConnectionError", "BackendTransitionError"}
)


class OutcomeStatus(StrEnum):
    OK = "OK"
    NO_HITS = "NO_HITS"
    CANONICAL_UNAVAILABLE = "CANONICAL_UNAVAILABLE"
    UNAUTHORIZED_NAMESPACE = "UNAUTHORIZED_NAMESPACE"
    PARTIAL_PROJECTION_DEGRADED = "PARTIAL_PROJECTION_DEGRADED"
    TIMEOUT = "TIMEOUT"
    INVALID_RECEIPT = "INVALID_RECEIPT"
    REJECTED = "REJECTED"
    QUARANTINED = "QUARANTINED"
    NOT_COMMITTED = "NOT_COMMITTED"
    BINDING_FAILED = "BINDING_FAILED"
    #: Same idempotency key, different payload (audit CG-P1-01). Memory is
    #: correct to preserve the first commit and to report the historical
    #: record; this request is *not* the one that committed, so it is never a
    #: canonical close. Distinct from a transport failure on purpose: nothing
    #: is wrong with the runtime, the caller replayed a key under new content.
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    #: Canonical receipt validation was required and could not be performed
    #: (audit CG-P1-02) — the bound release exported no schema for this model,
    #: or no validator was reachable. The receipt was not proved wrong; it was
    #: not proved right, and structural acceptance is not a substitute.
    VALIDATION_UNAVAILABLE = "VALIDATION_UNAVAILABLE"
    #: The receipt could not prove it answers the request Cursor made (audit
    #: MEM-P2-01) — a result-affecting selector it does not bind, where the
    #: caller requires that identity. A receipt whose selectors *contradict*
    #: the request is INVALID_RECEIPT instead: that one is provably wrong.
    REQUEST_IDENTITY_UNPROVEN = "REQUEST_IDENTITY_UNPROVEN"


#: Fault classes (ADR-0032). A memory operation that did not answer is one of
#: exactly two different facts, and every consumer must be able to tell them
#: apart without re-reading rendered text:
#:
#: - ``environment`` — the operation never reached canonical memory. The bound
#:   runtime is unbound (a missing or drifted governance ``.venv``, a package
#:   that predates the contract). Nothing canonical was observed, so nothing
#:   canonical is degraded; the repair is a bootstrap repair.
#: - ``canonical`` — memory ran and did not answer as asked: unavailable,
#:   timed out, refused the namespace, returned an invalid receipt, rejected
#:   or quarantined the write.
#: - ``none`` — memory answered (``OK`` / ``NO_HITS`` / a projection warning).
FAULT_NONE = "none"
FAULT_ENVIRONMENT = "environment"
FAULT_CANONICAL = "canonical"

_NO_FAULT_STATUSES = frozenset(
    {OutcomeStatus.OK, OutcomeStatus.NO_HITS, OutcomeStatus.PARTIAL_PROJECTION_DEGRADED}
)
_ENVIRONMENT_FAULT_STATUSES = frozenset({OutcomeStatus.BINDING_FAILED})


def fault_class_for(status: OutcomeStatus | str) -> str:
    """Classify an outcome status as ``none`` / ``environment`` / ``canonical``."""

    try:
        resolved = status if isinstance(status, OutcomeStatus) else OutcomeStatus(str(status))
    except ValueError:
        # A status this client never produces (e.g. Cursor's own
        # NAMESPACE_UNRESOLVED) did not come from canonical memory.
        return FAULT_ENVIRONMENT
    if resolved in _NO_FAULT_STATUSES:
        return FAULT_NONE
    if resolved in _ENVIRONMENT_FAULT_STATUSES:
        return FAULT_ENVIRONMENT
    return FAULT_CANONICAL


@dataclass(frozen=True)
class OperationOutcome:
    operation: str
    status: OutcomeStatus
    receipt: Any = None
    exit_code: int | None = None
    latency_ms: int = 0
    error: str | None = None
    integration_receipt: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def ok(self) -> bool:
        return self.status is OutcomeStatus.OK

    @property
    def fault_class(self) -> str:
        return fault_class_for(self.status)

    @property
    def environment_fault(self) -> bool:
        """The operation never reached memory (unbound runtime)."""

        return self.fault_class == FAULT_ENVIRONMENT

    @property
    def memory_degraded(self) -> bool:
        """Memory ran and failed to answer as asked. Never true for an unbound runtime."""

        return self.fault_class == FAULT_CANONICAL


@dataclass
class _Raw:
    exit_code: int | None
    payload: dict[str, Any] | None
    error_name: str | None
    error_message: str | None
    latency_ms: int
    timed_out: bool = False


class MemoryControlPlaneClient:
    """The hook lane's door to memory; every call becomes one CLI invocation.

    This client is for *automatic* machinery (SessionStart / SessionEnd, plan
    prefetch, ``make pr`` publish, SGD ingest) and for the human operator form
    (``python -m ops.memory.cli``). It is not the agent lane: an agent writes
    and reads through the package's public ``l9-memory`` / MCP surface
    directly and Cursor-Governance does not mediate that (ADR-0033, INV-03b).

    A hook caller names its ``surface``; the matching envelope in
    ``ops/config/memory-hook-envelopes.json`` narrows what this instance may
    ask memory for and is enforced *before a process is spawned*. Same
    ``MemoryService``, same admission, same store — narrower capability. A
    client with no surface is the operator form and is stamped as such.
    """

    def __init__(
        self,
        binding: RuntimeBinding,
        *,
        runner: Runner | None = None,
        timeout: float = 30.0,
        env: Mapping[str, str] | None = None,
        session_id: str | None = None,
        validator: CanonicalValidator | None = None,
        surface: str | None = None,
    ) -> None:
        self.binding = binding
        self._run = runner or default_runner
        self.timeout = timeout
        self._env = dict(env) if env is not None else None
        self.session_id = session_id
        #: ADR-0033 B7. ``None`` is the operator form; a hook surface binds the
        #: envelope at construction so an unregistered surface fails here, not
        #: on the first memory call.
        self.surface = surface
        self.envelope: HookEnvelope | None = envelope_for(surface) if surface else None
        self._records_committed = 0
        #: CG-P1-02. Every receipt this client accepts as authoritative is
        #: validated against the schema the *bound release* exported, before
        #: the structural view in ``receipts.py`` reads a single field.
        self.validator = validator or CanonicalValidator.for_binding(binding, env=self._env)
        self._last_validation: str | None = None
        self._last_search_identity: Any = None
        self._v2_store_prepared = False

    def _checked(self, payload: Any, model_name: str, parser: Any) -> Any:
        """Canonical validation, then the structural view — in that order.

        Raises :class:`InvalidReceiptError` when the payload violates the
        bound release's contract and :class:`ValidationUnavailable` when
        validation was required and could not run. Neither is ever swallowed
        into a success: a receipt Cursor cannot check is not a receipt Cursor
        may act on.
        """

        self._last_validation = self.validator.validate(payload, model_name)
        return parser(payload)

    # ------------------------------------------------------------------
    # Transport
    # ------------------------------------------------------------------
    def _child_env(self) -> dict[str, str]:
        """The environment the memory CLI runs in: never a provider transport.

        Cursor-Governance holds no provider URL or bearer (stage C9). Even when
        a stale machine environment still carries one, it must not reach the
        memory runtime through this boundary — the runtime resolves its own
        credentials from its own configuration (memory ADR-016), and a value
        smuggled in here would be an undeclared second configuration path.
        """
        base = self._env if self._env is not None else os.environ
        return {
            key: value
            for key, value in base.items()
            if key not in PROVIDER_TRANSPORT_ENV and not key.startswith("GRAPHITI_SSH_")
        }

    def _invoke(
        self,
        argv: Sequence[str],
        *,
        cwd: str | None = None,
        input_text: str | None = None,
    ) -> _Raw:
        assert self.binding.memory_cli is not None  # guarded by _guard()
        started = time.monotonic()
        if not self._v2_store_prepared:
            from ops.memory.store_compat import prepare_v2_sqlite_store

            receipt = prepare_v2_sqlite_store(env=self._child_env())
            if receipt.get("status") == "error":
                return _Raw(
                    None,
                    None,
                    "StoreCompatError",
                    str(receipt.get("error") or receipt),
                    _ms(started),
                )
            self._v2_store_prepared = True
        try:
            completed = self._run(
                [self.binding.memory_cli, *argv],
                cwd=cwd,
                input_text=input_text,
                timeout=self.timeout,
                env=self._child_env(),
            )
        except subprocess.TimeoutExpired:
            return _Raw(None, None, "Timeout", "memory CLI timed out", _ms(started), True)
        except OSError as exc:
            return _Raw(None, None, "OSError", str(exc), _ms(started))
        payload: dict[str, Any] | None = None
        stdout = (completed.stdout or "").strip()
        if stdout:
            try:
                decoded = json.loads(stdout)
                payload = decoded if isinstance(decoded, dict) else None
            except ValueError:
                payload = None
        error_name, error_message = _parse_stderr(completed.stderr or "")
        return _Raw(completed.returncode, payload, error_name, error_message, _ms(started))

    def _guard(
        self,
        operation: str,
        *,
        memory_class: str | None = None,
        records: int = 0,
        byte_size: int | None = None,
        provenance: bool | None = None,
        namespace: str | None = None,
    ) -> OperationOutcome | None:
        """Refuse before spawning: unbound runtime, then hook-envelope violation.

        The envelope check is the hook lane's bound (ADR-0033 B7). A refusal is
        ``REJECTED`` with ``fault_class=canonical`` on purpose: nothing about
        the runtime is wrong and nothing canonical is degraded — the *caller*
        asked for more than its surface may. The error text starts with
        ``REJECTED:envelope`` so consumers can tell it from a memory rejection.
        """

        if not (self.binding.ok and self.binding.memory_cli):
            return self._outcome(
                operation,
                OutcomeStatus.BINDING_FAILED,
                _Raw(None, None, "BindingError", "; ".join(self.binding.reasons), 0),
            )
        if self.envelope is None:
            return None
        reason = self.envelope.violation(
            operation,
            memory_class=memory_class,
            records_used=self._records_committed,
            records=records,
            byte_size=byte_size,
            provenance=provenance,
            namespace=namespace,
        )
        if reason is None:
            return None
        return self._outcome(
            operation,
            OutcomeStatus.REJECTED,
            _Raw(None, None, "EnvelopeViolation", reason, 0),
            error_override=reason,
        )

    def _count_committed(self, outcome: OperationOutcome, records: int = 1) -> OperationOutcome:
        """Tally a committed write against the surface's ``max_records``."""

        if outcome.ok and self.envelope is not None:
            self._records_committed += records
        return outcome

    def principal(self) -> dict[str, Any]:
        """Which lane this instance runs on, as stamped into every receipt."""

        return self.envelope.principal() if self.envelope else operator_principal()

    def _outcome(
        self,
        operation: str,
        status: OutcomeStatus,
        raw: _Raw,
        receipt: Any = None,
        *,
        namespaces: Sequence[str] = (),
        task_signature: str | None = None,
        projection_status: str | None = None,
        error_override: str | None = None,
    ) -> OperationOutcome:
        receipt_raw = getattr(receipt, "raw", None)
        canonical_id = None
        if isinstance(receipt_raw, dict):
            canonical_id = receipt_raw.get("receipt_id") or receipt_raw.get("write_receipt_id")
        integration = {
            "operation": operation,
            "session_id": self.session_id,
            "principal": self.principal(),
            "task_signature": task_signature,
            "requested_namespaces": list(namespaces),
            "memory_package_version": self.binding.memory_version,
            "transport": TRANSPORT,
            "status": status.value,
            "fault_class": fault_class_for(status),
            "environment_heal": self.binding.environment_heal,
            "exit_code": raw.exit_code,
            "canonical_receipt_id": str(canonical_id) if canonical_id else None,
            "canonical_validation": self._last_validation,
            "contract_schema_digest": self.validator.schema_digest,
            "result_digest": result_digest(receipt_raw) if receipt_raw is not None else None,
            "latency_ms": raw.latency_ms,
            "projection_status": projection_status,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        error = None
        if status is not OutcomeStatus.OK and status is not OutcomeStatus.NO_HITS:
            error = (
                error_override
                or raw.error_message
                or raw.error_name
                or _receipt_reason(raw.payload)
            )
        return OperationOutcome(
            operation=operation,
            status=status,
            receipt=receipt,
            exit_code=raw.exit_code,
            latency_ms=raw.latency_ms,
            error=error,
            integration_receipt=integration,
        )

    def _classify_failure(self, raw: _Raw) -> OutcomeStatus:
        if raw.timed_out:
            return OutcomeStatus.TIMEOUT
        if raw.error_name in _UNAUTHORIZED_ERRORS:
            return OutcomeStatus.UNAUTHORIZED_NAMESPACE
        if raw.error_name in _UNAVAILABLE_ERRORS or raw.error_name == "OSError":
            return OutcomeStatus.CANONICAL_UNAVAILABLE
        if raw.payload is None:
            return OutcomeStatus.INVALID_RECEIPT
        return OutcomeStatus.CANONICAL_UNAVAILABLE

    # ------------------------------------------------------------------
    # Lifecycle operations
    # ------------------------------------------------------------------
    def resolve(self, workspace: str, *, explicit: str | None = None) -> OperationOutcome:
        if guard := self._guard("resolve"):
            return guard
        argv = ["resolve"]
        if explicit:
            argv += ["--group-id", explicit]
        raw = self._invoke(argv, cwd=workspace)
        if raw.payload is None:
            return self._outcome("resolve", self._classify_failure(raw), raw)
        try:
            receipt = self._checked(raw.payload, "ResolveReceipt", ResolveReceipt.parse)
        except InvalidReceiptError as exc:
            return self._outcome("resolve", OutcomeStatus.INVALID_RECEIPT, _err(raw, exc))
        except ValidationUnavailable as exc:
            return self._outcome("resolve", OutcomeStatus.VALIDATION_UNAVAILABLE, _err(raw, exc))
        return self._outcome("resolve", OutcomeStatus.OK, raw, receipt)

    def health(self) -> OperationOutcome:
        if guard := self._guard("health"):
            return guard
        raw = self._invoke(["health"])
        if raw.payload is None:
            return self._outcome("health", self._classify_failure(raw), raw)
        try:
            receipt = self._checked(raw.payload, "HealthReceipt", HealthReceipt.parse)
        except InvalidReceiptError as exc:
            return self._outcome("health", OutcomeStatus.INVALID_RECEIPT, _err(raw, exc))
        except ValidationUnavailable as exc:
            return self._outcome("health", OutcomeStatus.VALIDATION_UNAVAILABLE, _err(raw, exc))
        projection = (
            "none"
            if receipt.projection_name in (None, "none")
            else ("healthy" if receipt.projection_healthy else "unhealthy")
        )
        if not receipt.store_healthy or receipt.status == "failed":
            status = OutcomeStatus.CANONICAL_UNAVAILABLE
        elif receipt.status == "partial":
            status = OutcomeStatus.PARTIAL_PROJECTION_DEGRADED
        else:
            status = OutcomeStatus.OK
        return self._outcome("health", status, raw, receipt, projection_status=projection)

    def capabilities(self) -> OperationOutcome:
        if guard := self._guard("capabilities"):
            return guard
        raw = self._invoke(["capabilities"])
        if raw.payload is None or raw.exit_code != 0:
            return self._outcome("capabilities", self._classify_failure(raw), raw)
        try:
            receipt = self._checked(raw.payload, "CapabilitiesReceipt", CapabilitiesReceipt.parse)
        except InvalidReceiptError as exc:
            return self._outcome("capabilities", OutcomeStatus.INVALID_RECEIPT, _err(raw, exc))
        except ValidationUnavailable as exc:
            return self._outcome(
                "capabilities", OutcomeStatus.VALIDATION_UNAVAILABLE, _err(raw, exc)
            )
        return self._outcome("capabilities", OutcomeStatus.OK, raw, receipt)

    def hydrate(
        self,
        task: str,
        *,
        workspace: str,
        write_namespace_hint: str | None,
        read_namespace_hints: Sequence[str],
        token_budget: int = 1_200,
        max_records: int = 40,
        task_signature: str | None = None,
        topics: Sequence[str] = (),
    ) -> OperationOutcome:
        """Canonical hydrate. Read fan-in is requested; memory authorizes it."""

        if guard := self._guard("hydrate"):
            return guard
        argv = [
            "hydrate",
            task,
            "--token-budget",
            str(token_budget),
            "--max-records",
            str(max_records),
        ]
        if write_namespace_hint:
            argv += ["--group-id", write_namespace_hint]
        for namespace in read_namespace_hints:
            argv += ["--namespace", namespace]
        for topic in topics:
            argv += ["--topic", topic]
        raw = self._invoke(argv, cwd=workspace)
        namespaces = tuple(read_namespace_hints)
        if raw.payload is None:
            return self._outcome(
                "hydrate",
                self._classify_failure(raw),
                raw,
                namespaces=namespaces,
                task_signature=task_signature,
            )
        try:
            receipt = self._checked(raw.payload, "HydrationReceipt", HydrationReceipt.parse)
        except InvalidReceiptError as exc:
            return self._outcome(
                "hydrate",
                OutcomeStatus.INVALID_RECEIPT,
                _err(raw, exc),
                namespaces=namespaces,
                task_signature=task_signature,
            )
        except ValidationUnavailable as exc:
            return self._outcome(
                "hydrate",
                OutcomeStatus.VALIDATION_UNAVAILABLE,
                _err(raw, exc),
                namespaces=namespaces,
                task_signature=task_signature,
            )
        if receipt.status == "failed":
            status = OutcomeStatus.CANONICAL_UNAVAILABLE
        elif receipt.has_hits:
            status = OutcomeStatus.OK
        else:
            status = OutcomeStatus.NO_HITS
        return self._outcome(
            "hydrate", status, raw, receipt, namespaces=namespaces, task_signature=task_signature
        )

    def search(
        self,
        query: str,
        *,
        workspace: str,
        write_namespace_hint: str | None,
        read_namespace_hints: Sequence[str],
        tags: Sequence[str] = (),
        limit: int = 10,
        memory_classes: Sequence[str] = (),
        task_signature: str | None = None,
        recorded_after: datetime | None = None,
    ) -> OperationOutcome:
        """Canonical search returning full records (the typed-continuation path).

        ``tags`` is a selector memory applies (every tag required), so a
        consumer can retrieve its ``session_continuation`` records without
        depending on query text. ``recorded_after`` is the recency-window
        selector (ADR-0035): when the bound CLI accepts it, memory returns
        authorized records after that floor even without query overlap.
        Read fan-in is requested; memory authorizes.
        """

        if guard := self._guard("search"):
            return guard
        argv = ["search", query, "--limit", str(limit)]
        if write_namespace_hint:
            argv += ["--group-id", write_namespace_hint]
        for namespace in read_namespace_hints:
            argv += ["--namespace", namespace]
        for memory_class in memory_classes:
            argv += ["--memory-class", memory_class]
        for tag in tags:
            argv += ["--tag", tag]
        cli = str(self.binding.memory_cli)
        # The floor memory is asked to apply; None when the bound parser refuses
        # the selector and the floor is applied to the hits below instead.
        sent_after = recorded_after if cli not in _RECORDED_AFTER_REFUSED else None
        selector: list[str] = []
        if sent_after is not None:
            selector = [
                RECORDED_AFTER_OPTION,
                sent_after.astimezone(UTC).replace(microsecond=0).isoformat(),
            ]
        raw = self._invoke(argv + selector, cwd=workspace)
        if selector and _refused_option(raw, RECORDED_AFTER_OPTION):
            _RECORDED_AFTER_REFUSED.add(cli)
            sent_after = None
            raw = self._invoke(argv, cwd=workspace)
        namespaces = tuple(read_namespace_hints)
        if raw.payload is None:
            return self._outcome(
                "search",
                self._classify_failure(raw),
                raw,
                namespaces=namespaces,
                task_signature=task_signature,
            )
        try:
            receipt = self._checked(raw.payload, "SearchReceipt", SearchReceipt.parse)
        except InvalidReceiptError as exc:
            return self._outcome(
                "search",
                OutcomeStatus.INVALID_RECEIPT,
                _err(raw, exc),
                namespaces=namespaces,
                task_signature=task_signature,
            )
        except ValidationUnavailable as exc:
            return self._outcome(
                "search",
                OutcomeStatus.VALIDATION_UNAVAILABLE,
                _err(raw, exc),
                namespaces=namespaces,
                task_signature=task_signature,
            )
        identity = verify_request_identity(
            SearchRequest(
                query=query,
                namespaces=tuple(read_namespace_hints),
                tags=tuple(tags),
                limit=limit,
                memory_classes=tuple(memory_classes),
                recorded_after=sent_after,
            ),
            receipt,
            requested_namespaces=tuple(read_namespace_hints),
        )
        self._last_search_identity = identity
        if identity.contradicted:
            # The receipt describes a different search; its hits are not
            # answers to this question (MEM-P2-01, consumer half).
            return self._outcome(
                "search",
                OutcomeStatus.INVALID_RECEIPT,
                raw,
                receipt,
                namespaces=namespaces,
                task_signature=task_signature,
                error_override=(
                    "search receipt does not answer this request: " + "; ".join(identity.detail)
                ),
            )
        if identity.unbound and require_search_identity(self._env):
            return self._outcome(
                "search",
                OutcomeStatus.REQUEST_IDENTITY_UNPROVEN,
                raw,
                receipt,
                namespaces=namespaces,
                task_signature=task_signature,
                error_override=(
                    "the receipt binds no identity for result-affecting selector(s) "
                    + ", ".join(identity.unbound)
                    + "; it cannot prove these hits answer this request"
                ),
            )
        if recorded_after is not None and sent_after is None:
            receipt = replace(
                receipt,
                hits=tuple(h for h in receipt.hits if _recorded_since(h.record, recorded_after)),
            )
        if receipt.status == "failed":
            status = OutcomeStatus.CANONICAL_UNAVAILABLE
        elif receipt.has_hits:
            status = OutcomeStatus.OK
        else:
            status = OutcomeStatus.NO_HITS
        return self._outcome(
            "search", status, raw, receipt, namespaces=namespaces, task_signature=task_signature
        )

    def write(
        self,
        content: str,
        *,
        workspace: str,
        namespace: str,
        memory_class: str,
        tags: Sequence[str] = (),
        idempotency_key: str | None = None,
        source: str = "cursor-governance",
        source_id: str | None = None,
        dry_run: bool = False,
    ) -> OperationOutcome:
        """Generic canonical write (the last resort of the write taxonomy, plan §14).

        Purpose-specific ingress (``ingest_candidate``) is preferred; this is
        for durable observations, decisions, and lessons promoted at close.
        The receipt status is the verdict: ``rejected`` and ``quarantined``
        stay visible, a duplicate names the record already committed.
        """

        if guard := self._guard(
            "write",
            memory_class=memory_class,
            records=0 if dry_run else 1,
            byte_size=len(content.encode("utf-8")),
            provenance=bool(source and source_id),
            namespace=namespace,
        ):
            return guard
        argv = [
            "write",
            content,
            "--kind",
            memory_class,
            "--group-id",
            namespace,
            "--source",
            source,
        ]
        for tag in tags:
            argv += ["--tag", tag]
        if idempotency_key:
            argv += ["--idempotency-key", idempotency_key]
        if source_id:
            argv += ["--source-id", source_id]
        if dry_run:
            argv.append("--dry-run")
        raw = self._invoke(argv, cwd=workspace)
        namespaces = (namespace,)
        if raw.payload is None:
            return self._outcome("write", self._classify_failure(raw), raw, namespaces=namespaces)
        try:
            receipt = self._checked(raw.payload, "WriteReceipt", WriteReceipt.parse)
        except InvalidReceiptError as exc:
            return self._outcome(
                "write", OutcomeStatus.INVALID_RECEIPT, _err(raw, exc), namespaces=namespaces
            )
        except ValidationUnavailable as exc:
            return self._outcome(
                "write", OutcomeStatus.VALIDATION_UNAVAILABLE, _err(raw, exc), namespaces=namespaces
            )
        if receipt.status == "rejected":
            status = OutcomeStatus.REJECTED
        elif receipt.status == "quarantined":
            status = OutcomeStatus.QUARANTINED
        elif dry_run:
            status = OutcomeStatus.NOT_COMMITTED
        elif receipt.accepted or receipt.status == "superseded":
            status = OutcomeStatus.OK
        else:
            status = OutcomeStatus.INVALID_RECEIPT
        return self._count_committed(
            self._outcome("write", status, raw, receipt, namespaces=namespaces)
        )

    def ingest_candidate(self, candidate: Mapping[str, Any], *, workspace: str) -> OperationOutcome:
        """Admit a governed candidate (the continuation capsule's ingress)."""

        source = candidate.get("source") or {}
        knowledge = candidate.get("knowledge") or {}
        primary_class = knowledge.get("primary_class") if isinstance(knowledge, Mapping) else None
        body = json.dumps(dict(candidate), sort_keys=True)
        if guard := self._guard(
            "ingest_candidate",
            memory_class=str(primary_class) if primary_class else None,
            records=1,
            byte_size=len(body.encode("utf-8")),
            provenance=bool(isinstance(source, Mapping) and source.get("repository")),
        ):
            return guard
        namespace = str((candidate.get("source") or {}).get("namespace") or "")
        raw = self._invoke(["ingest-governed-candidate"], cwd=workspace, input_text=body)
        namespaces = (namespace,) if namespace else ()
        if raw.payload is None:
            return self._outcome(
                "ingest_candidate", self._classify_failure(raw), raw, namespaces=namespaces
            )
        try:
            receipt = self._checked(raw.payload, "CandidateReceipt", CandidateReceipt.parse)
        except InvalidReceiptError as exc:
            return self._outcome(
                "ingest_candidate",
                OutcomeStatus.INVALID_RECEIPT,
                _err(raw, exc),
                namespaces=namespaces,
            )
        except ValidationUnavailable as exc:
            return self._outcome(
                "ingest_candidate",
                OutcomeStatus.VALIDATION_UNAVAILABLE,
                _err(raw, exc),
                namespaces=namespaces,
            )
        if receipt.status == "rejected" or raw.exit_code == EXIT_CANDIDATE_REJECTED:
            status = OutcomeStatus.REJECTED
        elif receipt.status == "quarantined":
            status = OutcomeStatus.QUARANTINED
        elif receipt.accepted:
            status = OutcomeStatus.OK
        else:
            status = OutcomeStatus.INVALID_RECEIPT
        return self._count_committed(
            self._outcome("ingest_candidate", status, raw, receipt, namespaces=namespaces)
        )

    def close(
        self,
        *,
        workspace: str,
        namespace: str,
        summary: str,
        session_id: str | None = None,
        capsule_digest: str | None = None,
        idempotency_key: str | None = None,
        dry_run: bool = False,
    ) -> OperationOutcome:
        """Canonical close. Only ``OK`` means CLOSED_CANONICALLY."""

        if guard := self._guard(
            "close",
            records=0 if dry_run else 1,
            byte_size=len(summary.encode("utf-8")),
            provenance=bool(session_id or self.session_id),
        ):
            return guard
        argv = ["close", "--summary", summary, "--group-id", namespace]
        if session_id or self.session_id:
            argv += ["--session-id", str(session_id or self.session_id)]
        if capsule_digest:
            argv += ["--capsule-digest", capsule_digest]
        if idempotency_key:
            argv += ["--idempotency-key", idempotency_key]
        if dry_run:
            argv.append("--dry-run")
        raw = self._invoke(argv, cwd=workspace)
        namespaces = (namespace,)
        if raw.payload is None:
            return self._outcome("close", self._classify_failure(raw), raw, namespaces=namespaces)
        try:
            receipt = self._checked(raw.payload, "CloseReceipt", CloseReceipt.parse)
        except InvalidReceiptError as exc:
            return self._outcome(
                "close", OutcomeStatus.INVALID_RECEIPT, _err(raw, exc), namespaces=namespaces
            )
        except ValidationUnavailable as exc:
            return self._outcome(
                "close", OutcomeStatus.VALIDATION_UNAVAILABLE, _err(raw, exc), namespaces=namespaces
            )
        if receipt.payload_drifted:
            # CG-P1-01. Memory replayed this key and proved the stored payload
            # differs from the one just sent. The committed record it returns
            # is the *first* close, not this request: promoting it here would
            # let a drifted retry satisfy a close obligation it never wrote.
            # This branch is deliberately ahead of the ``committed`` check —
            # a warning beside a success is precisely the defect (contract §16).
            status = OutcomeStatus.IDEMPOTENCY_CONFLICT
        elif raw.exit_code == EXIT_COMMITTED and receipt.committed:
            status = OutcomeStatus.OK
        elif raw.exit_code == EXIT_DRY_RUN and dry_run:
            status = OutcomeStatus.NOT_COMMITTED
        elif receipt.status == "failed":
            status = OutcomeStatus.REJECTED
        else:
            # A zero exit without a committed receipt, or vice versa, is a
            # contract violation; never report success from half the evidence.
            status = OutcomeStatus.INVALID_RECEIPT
        conflict_detail = None
        if status is OutcomeStatus.IDEMPOTENCY_CONFLICT:
            conflict_detail = (
                f"idempotency key {idempotency_key!r} already committed a different close "
                f"(stored digest {receipt.stored_digest}, "
                f"replayed digest {receipt.replay_digest}); "
                "the returned record is the first close, not this request"
            )
        return self._count_committed(
            self._outcome(
                "close",
                status,
                raw,
                receipt,
                namespaces=namespaces,
                error_override=conflict_detail,
            )
        )

    def distill(
        self,
        *,
        workspace: str,
        namespace: str,
        source_path: str | Path,
        repository: str | None = None,
        dry_run: bool = False,
        timeout: float | None = None,
    ) -> OperationOutcome:
        """Canonical distillation of a redacted source (``l9-memory distill``).

        Memory extracts atomic candidates from ``source_path`` and admits each
        through its own ``MemoryService.write`` under a source-digest
        idempotency key; this side neither extracts, scores nor promotes
        (ADR-0033). ``source_path`` must already be redacted — the hook lane
        prepares the excerpt, it does not interpret it. Only ``OK`` means at
        least one atomic record exists; ``NO_HITS`` means memory found nothing
        to distill, which is not a fault.
        """

        source = Path(source_path)
        try:
            source_bytes: int | None = source.stat().st_size
        except OSError:
            source_bytes = None
        # A committing distill needs at least one record slot; the exact count
        # is only known after memory has extracted, so the preflight below
        # refines this before anything is written.
        if guard := self._guard(
            "distill",
            records=1 if self.envelope is not None else 0,
            byte_size=source_bytes,
            provenance=bool(namespace and source_bytes is not None),
        ):
            return guard
        namespaces = (namespace,)
        argv = self._distill_argv(source_path, namespace, repository, dry_run=dry_run)
        if self.envelope is not None and not dry_run:
            # Hook-lane record bound (ADR-0033 B7). The bound release's
            # ``distill`` takes no input cap (DISTILL_CLI_OPTIONS), so the
            # bound is proved with memory's own cognition: the same
            # deterministic distill under ``--dry-run`` reports exactly the
            # candidates the committing pass would write, and nothing is
            # persisted. Refuse here when that count exceeds the remaining
            # allowance — before the write, not after it.
            preflight, counted = self._distill_pass(
                self._distill_argv(source_path, namespace, repository, dry_run=True),
                workspace=workspace,
                timeout=timeout,
                namespaces=namespaces,
                dry_run=True,
            )
            if counted is None or preflight.status is not OutcomeStatus.NOT_COMMITTED:
                # Nothing to distill, memory rejected every candidate, or memory
                # did not answer: the preflight verdict is the verdict.
                return preflight
            reason = self.envelope.violation(
                "distill",
                records_used=self._records_committed,
                records=counted.candidate_count,
            )
            if reason is not None:
                reason = (
                    f"{reason}; preflight distill of {counted.source_digest} refused before write"
                )
                return self._outcome(
                    "distill",
                    OutcomeStatus.REJECTED,
                    _Raw(None, None, "EnvelopeViolation", reason, preflight.latency_ms),
                    namespaces=namespaces,
                    error_override=reason,
                )
            outcome, receipt = self._distill_pass(
                argv, workspace=workspace, timeout=timeout, namespaces=namespaces, dry_run=False
            )
            if receipt is not None and receipt.source_digest != counted.source_digest:
                # The excerpt changed between the counting pass and the commit:
                # the bound was proved for a different source. Report it; the
                # tally below still charges every record memory says it wrote.
                outcome = self._outcome(
                    "distill",
                    OutcomeStatus.INVALID_RECEIPT,
                    _Raw(
                        outcome.exit_code,
                        receipt.raw,
                        "DistillPreflightMismatch",
                        f"source digest moved between preflight ({counted.source_digest}) "
                        f"and commit ({receipt.source_digest})",
                        outcome.latency_ms,
                    ),
                    receipt,
                    namespaces=namespaces,
                    error_override=(
                        "distill source changed between the counting pass and the commit "
                        f"(preflight {counted.source_digest}, commit {receipt.source_digest})"
                    ),
                )
            return outcome
        outcome, _receipt = self._distill_pass(
            argv, workspace=workspace, timeout=timeout, namespaces=namespaces, dry_run=dry_run
        )
        return outcome

    @staticmethod
    def _distill_argv(
        source_path: str | Path,
        namespace: str,
        repository: str | None,
        *,
        dry_run: bool,
    ) -> list[str]:
        """The exact ``distill`` argv the bound release parses.

        Every option here is in ``DISTILL_CLI_OPTIONS``; anything else is a
        cross-repository contract break that argparse turns into a failed
        session-end distill (audit F-604-DISTILL-CAP).
        """

        argv = ["distill", str(source_path), "--group-id", namespace]
        if repository:
            argv += ["--repository", repository]
        if dry_run:
            argv.append("--dry-run")
        emitted = {flag for flag in argv if flag.startswith("--")}
        extras = emitted - DISTILL_CLI_OPTIONS
        if extras:
            raise RuntimeError(
                "distill argv emitted options outside DISTILL_CLI_OPTIONS: "
                + ", ".join(sorted(extras))
            )
        return argv

    def _distill_pass(
        self,
        argv: Sequence[str],
        *,
        workspace: str,
        timeout: float | None,
        namespaces: tuple[str, ...],
        dry_run: bool,
    ) -> tuple[OperationOutcome, DistillationReceipt | None]:
        """One ``l9-memory distill`` spawn, classified. Tallies committed records."""

        previous_timeout = self.timeout
        if timeout is not None and timeout > 0:
            self.timeout = timeout
        try:
            raw = self._invoke(argv, cwd=workspace)
        finally:
            self.timeout = previous_timeout
        if raw.payload is None:
            return (
                self._outcome("distill", self._classify_failure(raw), raw, namespaces=namespaces),
                None,
            )
        try:
            receipt = self._checked(raw.payload, "DistillationReceipt", DistillationReceipt.parse)
        except InvalidReceiptError as exc:
            return (
                self._outcome(
                    "distill", OutcomeStatus.INVALID_RECEIPT, _err(raw, exc), namespaces=namespaces
                ),
                None,
            )
        except ValidationUnavailable as exc:
            return (
                self._outcome(
                    "distill",
                    OutcomeStatus.VALIDATION_UNAVAILABLE,
                    _err(raw, exc),
                    namespaces=namespaces,
                ),
                None,
            )
        detail = None
        if receipt.failed or raw.exit_code == EXIT_FAILED:
            status = OutcomeStatus.REJECTED
            detail = (
                f"memory rejected every distilled candidate ({receipt.candidate_count} "
                f"candidates, {len(receipt.rejected_items)} rejected items)"
            )
        elif receipt.candidate_count == 0:
            status = OutcomeStatus.NO_HITS
        elif dry_run:
            status = OutcomeStatus.NOT_COMMITTED
        elif receipt.wrote_something:
            status = OutcomeStatus.OK
        else:
            # Candidates without a single record and no dry run: the receipt
            # contradicts itself, and half the evidence is never a success.
            status = OutcomeStatus.INVALID_RECEIPT
            detail = (
                f"distill reported {receipt.candidate_count} candidates and status "
                f"{receipt.status!r} but wrote no record"
            )
        outcome = self._outcome(
            "distill", status, raw, receipt, namespaces=namespaces, error_override=detail
        )
        if dry_run:
            return outcome, receipt
        return self._count_committed(outcome, records=int(receipt.written_count or 0)), receipt

    def conflicts(self, *, workspace: str, namespace: str) -> OperationOutcome:
        if guard := self._guard("conflicts"):
            return guard
        raw = self._invoke(["conflicts", "--group-id", namespace], cwd=workspace)
        if raw.payload is None:
            return self._outcome(
                "conflicts", self._classify_failure(raw), raw, namespaces=(namespace,)
            )
        try:
            receipt = self._checked(raw.payload, "ConflictsReceipt", ConflictsReceipt.parse)
        except InvalidReceiptError as exc:
            return self._outcome(
                "conflicts", OutcomeStatus.INVALID_RECEIPT, _err(raw, exc), namespaces=(namespace,)
            )
        except ValidationUnavailable as exc:
            return self._outcome(
                "conflicts",
                OutcomeStatus.VALIDATION_UNAVAILABLE,
                _err(raw, exc),
                namespaces=(namespace,),
            )
        return self._outcome("conflicts", OutcomeStatus.OK, raw, receipt, namespaces=(namespace,))

    def phase_lock(
        self, *, workspace: str, namespace: str, task_signature: str, ttl_seconds: int = 1_800
    ) -> OperationOutcome:
        if guard := self._guard("phase_lock", provenance=bool(task_signature)):
            return guard
        raw = self._invoke(
            [
                "phase-lock",
                "--group-id",
                namespace,
                "--task-signature",
                task_signature,
                "--ttl-seconds",
                str(ttl_seconds),
            ],
            cwd=workspace,
        )
        if raw.payload is None:
            return self._outcome(
                "phase_lock",
                self._classify_failure(raw),
                raw,
                namespaces=(namespace,),
                task_signature=task_signature,
            )
        try:
            receipt = self._checked(raw.payload, "PhaseLockReceipt", PhaseLockReceipt.parse)
        except InvalidReceiptError as exc:
            return self._outcome(
                "phase_lock",
                OutcomeStatus.INVALID_RECEIPT,
                _err(raw, exc),
                namespaces=(namespace,),
                task_signature=task_signature,
            )
        except ValidationUnavailable as exc:
            return self._outcome(
                "phase_lock",
                OutcomeStatus.VALIDATION_UNAVAILABLE,
                _err(raw, exc),
                namespaces=(namespace,),
                task_signature=task_signature,
            )
        return self._outcome(
            "phase_lock",
            OutcomeStatus.OK if receipt.granted else OutcomeStatus.REJECTED,
            raw,
            receipt,
            namespaces=(namespace,),
            task_signature=task_signature,
        )

    def verify_phase_lock(
        self, *, workspace: str, namespace: str, task_signature: str
    ) -> OperationOutcome:
        if guard := self._guard("verify_phase_lock"):
            return guard
        raw = self._invoke(
            ["verify-phase-lock", task_signature, "--group-id", namespace], cwd=workspace
        )
        if raw.payload is None:
            return self._outcome(
                "verify_phase_lock",
                self._classify_failure(raw),
                raw,
                namespaces=(namespace,),
                task_signature=task_signature,
            )
        try:
            receipt = self._checked(
                raw.payload, "PhaseLockVerificationReceipt", PhaseLockVerificationReceipt.parse
            )
        except InvalidReceiptError as exc:
            return self._outcome(
                "verify_phase_lock",
                OutcomeStatus.INVALID_RECEIPT,
                _err(raw, exc),
                namespaces=(namespace,),
                task_signature=task_signature,
            )
        except ValidationUnavailable as exc:
            return self._outcome(
                "verify_phase_lock",
                OutcomeStatus.VALIDATION_UNAVAILABLE,
                _err(raw, exc),
                namespaces=(namespace,),
                task_signature=task_signature,
            )
        return self._outcome(
            "verify_phase_lock",
            OutcomeStatus.OK if receipt.valid else OutcomeStatus.REJECTED,
            raw,
            receipt,
            namespaces=(namespace,),
            task_signature=task_signature,
        )

    # ------------------------------------------------------------------
    # Probes used by diagnostics (no canonical write ever happens here)
    # ------------------------------------------------------------------
    def write_probe(self, *, workspace: str, namespace: str) -> OperationOutcome:
        """``write --dry-run``: proves admission without committing (R7)."""

        if guard := self._guard("write_probe"):
            return guard
        raw = self._invoke(
            [
                "write",
                "readiness probe: write admission dry run",
                "--group-id",
                namespace,
                "--dry-run",
                "--tag",
                "readiness-probe",
            ],
            cwd=workspace,
        )
        if raw.payload is None:
            return self._outcome(
                "write_probe", self._classify_failure(raw), raw, namespaces=(namespace,)
            )
        status = (
            OutcomeStatus.OK if raw.payload.get("status") != "rejected" else OutcomeStatus.REJECTED
        )
        return self._outcome("write_probe", status, raw, None, namespaces=(namespace,))

    def cursor_client_status(self, *, config_path: str | None = None) -> OperationOutcome:
        """``client cursor status`` — the memory-owned MCP config lifecycle (R4)."""

        if guard := self._guard("cursor_client_status"):
            return guard
        argv = ["client", "cursor", "status"]
        if config_path:
            argv += ["--path", config_path]
        raw = self._invoke(argv)
        if raw.payload is None:
            return self._outcome("cursor_client_status", self._classify_failure(raw), raw)
        status = (
            OutcomeStatus.OK if raw.payload.get("status") == "complete" else OutcomeStatus.REJECTED
        )
        return self._outcome("cursor_client_status", status, raw, None)

    def cursor_client_verify(
        self, *, config_path: str | None = None, timeout_seconds: float = 30.0
    ) -> OperationOutcome:
        """``client cursor verify`` — a real MCP handshake, memory-owned (R5)."""

        if guard := self._guard("cursor_client_verify"):
            return guard
        argv = ["client", "cursor", "verify", "--timeout", str(timeout_seconds)]
        if config_path:
            argv += ["--path", config_path]
        raw = self._invoke(argv)
        if raw.payload is None:
            return self._outcome("cursor_client_verify", self._classify_failure(raw), raw)
        status = (
            OutcomeStatus.OK if raw.payload.get("status") == "complete" else OutcomeStatus.REJECTED
        )
        return self._outcome("cursor_client_verify", status, raw, None)


def _ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


def _refused_option(raw: _Raw, option: str) -> bool:
    """True when the CLI's argument parser rejected ``option`` (argparse exit 2)."""

    return raw.exit_code == 2 and f"unrecognized arguments: {option}" in (raw.error_message or "")


def _recorded_since(record: Any, floor: datetime) -> bool:
    """The recency floor, applied to a hit when memory could not apply it.

    ``recorded_at`` first, then ``created_at``. A record carrying neither cannot
    be shown to fall inside the window, so it is left out — the window is a
    bound, and an unprovable record is not evidence it holds.
    """

    stamp = getattr(record, "recorded_at", None) or getattr(record, "created_at", None)
    if not stamp:
        return False
    try:
        moment = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except ValueError:
        return False
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment >= floor.astimezone(UTC)


def _parse_stderr(stderr: str) -> tuple[str | None, str | None]:
    """The memory CLI prints ``{"error": <type>, "message": ...}`` (pretty-printed)."""

    text = stderr.strip()
    if not text:
        return None, None
    candidates = [text]
    brace = text.find("{")
    if brace > 0:
        candidates.append(text[brace:])
    for candidate in candidates:
        try:
            decoded = json.loads(candidate)
        except ValueError:
            continue
        if isinstance(decoded, dict) and "error" in decoded:
            return str(decoded.get("error")), str(decoded.get("message") or "")
    return None, text[-500:]


def _receipt_reason(payload: dict[str, Any] | None) -> str | None:
    """A human reason from a receipt that reported a non-success status."""

    if not payload:
        return None
    for key in ("reasons", "reason", "degraded_reasons", "warnings"):
        value = payload.get(key)
        if isinstance(value, list) and value:
            return "; ".join(str(item) for item in value)[:500]
        if isinstance(value, str) and value:
            return value[:500]
    status = payload.get("status")
    return f"status={status}" if status else None


def _err(raw: _Raw, exc: Exception) -> _Raw:
    return _Raw(raw.exit_code, raw.payload, type(exc).__name__, str(exc), raw.latency_ms)


__all__ = [
    "EXIT_CANDIDATE_REJECTED",
    "EXIT_COMMITTED",
    "EXIT_DRY_RUN",
    "EXIT_ERROR",
    "EXIT_FAILED",
    "MemoryControlPlaneClient",
    "OperationOutcome",
    "OutcomeStatus",
]

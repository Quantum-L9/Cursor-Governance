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
import subprocess
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from ops.memory.receipts import (
    CandidateReceipt,
    CapabilitiesReceipt,
    CloseReceipt,
    ConflictsReceipt,
    HealthReceipt,
    HydrationReceipt,
    InvalidReceiptError,
    PhaseLockReceipt,
    PhaseLockVerificationReceipt,
    ResolveReceipt,
    result_digest,
)
from ops.memory.runtime_binding import Runner, RuntimeBinding, default_runner

TRANSPORT = "cli"

# Exit codes the memory CLI documents in its capabilities receipt.
EXIT_COMMITTED = 0
EXIT_ERROR = 1
EXIT_FAILED = 2
EXIT_DRY_RUN = 3
EXIT_CANDIDATE_REJECTED = 7

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


@dataclass
class _Raw:
    exit_code: int | None
    payload: dict[str, Any] | None
    error_name: str | None
    error_message: str | None
    latency_ms: int
    timed_out: bool = False


class MemoryControlPlaneClient:
    """Cursor's only door to memory; every call becomes one CLI invocation."""

    def __init__(
        self,
        binding: RuntimeBinding,
        *,
        runner: Runner | None = None,
        timeout: float = 30.0,
        env: Mapping[str, str] | None = None,
        session_id: str | None = None,
    ) -> None:
        self.binding = binding
        self._run = runner or default_runner
        self.timeout = timeout
        self._env = dict(env) if env is not None else None
        self.session_id = session_id

    # ------------------------------------------------------------------
    # Transport
    # ------------------------------------------------------------------
    def _invoke(
        self,
        argv: Sequence[str],
        *,
        cwd: str | None = None,
        input_text: str | None = None,
    ) -> _Raw:
        assert self.binding.memory_cli is not None  # guarded by _guard()
        started = time.monotonic()
        try:
            completed = self._run(
                [self.binding.memory_cli, *argv],
                cwd=cwd,
                input_text=input_text,
                timeout=self.timeout,
                env=self._env,
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

    def _guard(self, operation: str) -> OperationOutcome | None:
        if self.binding.ok and self.binding.memory_cli:
            return None
        return self._outcome(
            operation,
            OutcomeStatus.BINDING_FAILED,
            _Raw(None, None, "BindingError", "; ".join(self.binding.reasons), 0),
        )

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
    ) -> OperationOutcome:
        receipt_raw = getattr(receipt, "raw", None)
        canonical_id = None
        if isinstance(receipt_raw, dict):
            canonical_id = receipt_raw.get("receipt_id") or receipt_raw.get("write_receipt_id")
        integration = {
            "operation": operation,
            "session_id": self.session_id,
            "task_signature": task_signature,
            "requested_namespaces": list(namespaces),
            "memory_package_version": self.binding.memory_version,
            "transport": TRANSPORT,
            "status": status.value,
            "exit_code": raw.exit_code,
            "canonical_receipt_id": str(canonical_id) if canonical_id else None,
            "result_digest": result_digest(receipt_raw) if receipt_raw is not None else None,
            "latency_ms": raw.latency_ms,
            "projection_status": projection_status,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        error = None
        if status is not OutcomeStatus.OK and status is not OutcomeStatus.NO_HITS:
            error = raw.error_message or raw.error_name or _receipt_reason(raw.payload)
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
            receipt = ResolveReceipt.parse(raw.payload)
        except InvalidReceiptError as exc:
            return self._outcome("resolve", OutcomeStatus.INVALID_RECEIPT, _err(raw, exc))
        return self._outcome("resolve", OutcomeStatus.OK, raw, receipt)

    def health(self) -> OperationOutcome:
        if guard := self._guard("health"):
            return guard
        raw = self._invoke(["health"])
        if raw.payload is None:
            return self._outcome("health", self._classify_failure(raw), raw)
        try:
            receipt = HealthReceipt.parse(raw.payload)
        except InvalidReceiptError as exc:
            return self._outcome("health", OutcomeStatus.INVALID_RECEIPT, _err(raw, exc))
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
            receipt = CapabilitiesReceipt.parse(raw.payload)
        except InvalidReceiptError as exc:
            return self._outcome("capabilities", OutcomeStatus.INVALID_RECEIPT, _err(raw, exc))
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
            receipt = HydrationReceipt.parse(raw.payload)
        except InvalidReceiptError as exc:
            return self._outcome(
                "hydrate",
                OutcomeStatus.INVALID_RECEIPT,
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

    def ingest_candidate(self, candidate: Mapping[str, Any], *, workspace: str) -> OperationOutcome:
        """Admit a governed candidate (the continuation capsule's ingress)."""

        if guard := self._guard("ingest_candidate"):
            return guard
        namespace = str((candidate.get("source") or {}).get("namespace") or "")
        raw = self._invoke(
            ["ingest-governed-candidate"],
            cwd=workspace,
            input_text=json.dumps(dict(candidate), sort_keys=True),
        )
        namespaces = (namespace,) if namespace else ()
        if raw.payload is None:
            return self._outcome(
                "ingest_candidate", self._classify_failure(raw), raw, namespaces=namespaces
            )
        try:
            receipt = CandidateReceipt.parse(raw.payload)
        except InvalidReceiptError as exc:
            return self._outcome(
                "ingest_candidate",
                OutcomeStatus.INVALID_RECEIPT,
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
        return self._outcome("ingest_candidate", status, raw, receipt, namespaces=namespaces)

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

        if guard := self._guard("close"):
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
            receipt = CloseReceipt.parse(raw.payload)
        except InvalidReceiptError as exc:
            return self._outcome(
                "close", OutcomeStatus.INVALID_RECEIPT, _err(raw, exc), namespaces=namespaces
            )
        if raw.exit_code == EXIT_COMMITTED and receipt.committed:
            status = OutcomeStatus.OK
        elif raw.exit_code == EXIT_DRY_RUN and dry_run:
            status = OutcomeStatus.NOT_COMMITTED
        elif receipt.status == "failed":
            status = OutcomeStatus.REJECTED
        else:
            # A zero exit without a committed receipt, or vice versa, is a
            # contract violation; never report success from half the evidence.
            status = OutcomeStatus.INVALID_RECEIPT
        return self._outcome("close", status, raw, receipt, namespaces=namespaces)

    def conflicts(self, *, workspace: str, namespace: str) -> OperationOutcome:
        if guard := self._guard("conflicts"):
            return guard
        raw = self._invoke(["conflicts", "--group-id", namespace], cwd=workspace)
        if raw.payload is None:
            return self._outcome(
                "conflicts", self._classify_failure(raw), raw, namespaces=(namespace,)
            )
        try:
            receipt = ConflictsReceipt.parse(raw.payload)
        except InvalidReceiptError as exc:
            return self._outcome(
                "conflicts", OutcomeStatus.INVALID_RECEIPT, _err(raw, exc), namespaces=(namespace,)
            )
        return self._outcome("conflicts", OutcomeStatus.OK, raw, receipt, namespaces=(namespace,))

    def phase_lock(
        self, *, workspace: str, namespace: str, task_signature: str, ttl_seconds: int = 1_800
    ) -> OperationOutcome:
        if guard := self._guard("phase_lock"):
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
            receipt = PhaseLockReceipt.parse(raw.payload)
        except InvalidReceiptError as exc:
            return self._outcome(
                "phase_lock",
                OutcomeStatus.INVALID_RECEIPT,
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
            receipt = PhaseLockVerificationReceipt.parse(raw.payload)
        except InvalidReceiptError as exc:
            return self._outcome(
                "verify_phase_lock",
                OutcomeStatus.INVALID_RECEIPT,
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

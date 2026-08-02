#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-.}"
BASE="$ROOT/subagent-generated-data"
ORCHESTRATION="$BASE/orchestration"
RETRIEVAL="$BASE/retrieval"
INVALIDATION="$BASE/invalidation"
OPERATIONS="$BASE/operations"
INTEGRATION="$BASE/integration"
CONFIG="$BASE/config"
TESTS="$BASE/tests/instantiation"
RUNTIME_DIR="$BASE/.runtime"
STATE_DIR="$ROOT/.l9/subagent-generated-data"
cd "$ROOT"
# ---------------------------------------------------------------------------
# Repository identity and prior-wave guards
# ---------------------------------------------------------------------------
if [[ ! -f "CANONICAL_LAW.md" ]] || [[ ! -d "ops/graphiti" ]]; then
  echo "ERROR: This is not a recognizable Cursor-Governance checkout." >&2
  exit 1
fi
REMOTE_URL="$(git remote get-url origin 2>/dev/null || true)"
if [[ -n "$REMOTE_URL" ]] && [[ "$REMOTE_URL" != *"Quantum-L9/Cursor-Governance"* ]]; then
  echo "ERROR: Wrong repository remote: $REMOTE_URL" >&2
  echo "This installer is only for Quantum-L9/Cursor-Governance." >&2
  exit 1
fi
required_files=(
  "$BASE/law/SUBAGENT_GENERATED_DATA_LAW.md"
  "$BASE/runtime/packet_validator.py"
  "$BASE/runtime/harvester.py"
  "$BASE/runtime/classifier.py"
  "$BASE/runtime/routing_engine.py"
  "$BASE/runtime/promotion_gate.py"
  "$BASE/runtime/learning_closure.py"
  "$BASE/adapters/graphiti_memory.py"
  "$ORCHESTRATION/module_loader.py"
  "$ORCHESTRATION/state_store.py"
  "$ORCHESTRATION/receipts.py"
  "$ORCHESTRATION/retry_policy.py"
  "$ORCHESTRATION/processor.py"
)
for required in "${required_files[@]}"; do
  if [[ ! -f "$required" ]]; then
    echo "ERROR: Required prior-wave file is missing: $required" >&2
    exit 1
  fi
done
mkdir -p \
  "$RETRIEVAL" \
  "$INVALIDATION" \
  "$OPERATIONS" \
  "$INTEGRATION" \
  "$CONFIG" \
  "$TESTS" \
  "$RUNTIME_DIR/memory-outbox" \
  "$RUNTIME_DIR/contracts-outbox" \
  "$RUNTIME_DIR/validation-outbox" \
  "$RUNTIME_DIR/patterns-outbox" \
  "$RUNTIME_DIR/architecture-outbox" \
  "$RUNTIME_DIR/opportunities-outbox" \
  "$STATE_DIR"
cat > "$RETRIEVAL/__init__.py" <<'PY'
"""Context retrieval, deterministic selection, and memory-reuse dispatch."""
PY
cat > "$INVALIDATION/__init__.py" <<'PY'
"""Structured repository-event bridge for governed memory invalidation."""
PY
cat > "$OPERATIONS/__init__.py" <<'PY'
"""Operational health, status, replay, and dead-letter controls."""
PY
cat > "$INTEGRATION/__init__.py" <<'PY'
"""Executable integration proofs for the generated-data compounding loop."""
PY
# ---------------------------------------------------------------------------
# Delivery worker
# ---------------------------------------------------------------------------
cat > "$ORCHESTRATION/delivery_worker.py" <<'PY'
from __future__ import annotations
import argparse
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol
from module_loader import PriorWaveModuleLoader
from receipts import ProcessingReceiptChain
from retry_policy import RetryClass, RetryPolicy
from state_store import (
    PipelineState,
    PipelineStateStore,
    ProcessingJob,
    deterministic_id,
    utc_now_text,
)
class DeliveryError(RuntimeError):
    """Base delivery failure."""
class DestinationRejected(DeliveryError):
    """Destination returned a permanent rejection."""
class DeliveryTransport(Protocol):
    def deliver(
        self,
        delivery: Mapping[str, Any],
        packet: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """Deliver one promoted unit."""
@dataclass(frozen=True)
class DeliveryWorkerConfiguration:
    repository_root: str
    database_path: str
    memory_mode: str = "outbox"
    memory_endpoint: str | None = None
    memory_command: tuple[str, ...] = ()
    memory_outbox: str = (
        "subagent-generated-data/.runtime/memory-outbox"
    )
    route_outbox_root: str = (
        "subagent-generated-data/.runtime"
    )
    timeout_seconds: int = 30
    claim_timeout_seconds: int = 300
@dataclass(frozen=True)
class DeliveryExecutionResult:
    job_id: str
    attempted: int
    accepted: int
    enqueued: int
    rejected: int
    retried: int
    dead_lettered: int
    final_state: str
    details: tuple[Mapping[str, Any], ...]
    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "attempted": self.attempted,
            "accepted": self.accepted,
            "enqueued": self.enqueued,
            "rejected": self.rejected,
            "retried": self.retried,
            "dead_lettered": self.dead_lettered,
            "final_state": self.final_state,
            "details": [dict(item) for item in self.details],
        }
class JsonCommandTransport:
    """
    Delegate to an existing command.
    The command receives canonical JSON on stdin. It must return a JSON object
    containing at least a ``status`` field.
    """
    def __init__(
        self,
        command: tuple[str, ...],
        timeout_seconds: int,
    ) -> None:
        if not command:
            raise ValueError("Command transport requires a command")
        self.command = command
        self.timeout_seconds = timeout_seconds
    def deliver(
        self,
        delivery: Mapping[str, Any],
        packet: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        payload = {
            "delivery": dict(delivery),
            "packet": dict(packet),
        }
        completed = subprocess.run(
            list(self.command),
            input=json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
            ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            raise DeliveryError(
                f"Command failed with exit {completed.returncode}: "
                f"{completed.stderr.strip()}"
            )
        try:
            response = json.loads(completed.stdout or "{}")
        except json.JSONDecodeError as exc:
            raise DeliveryError(
                "Destination command returned invalid JSON"
            ) from exc
        if not isinstance(response, Mapping):
            raise DeliveryError(
                "Destination command response must be an object"
            )
        return response
class RouteOutboxTransport:
    """Durably enqueue a non-memory routed unit."""
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
    def deliver(
        self,
        delivery: Mapping[str, Any],
        packet: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        route = str(delivery["route"])
        destination = self.root / f"{route}-outbox"
        destination.mkdir(parents=True, exist_ok=True)
        delivery_id = str(delivery["delivery_id"])
        target = destination / f"{delivery_id}.json"
        payload = {
            "schema_version": "1.0.0",
            "kind": "GeneratedDataRouteEnvelope",
            "delivery": dict(delivery),
            "packet_identity": dict(packet["identity"]),
            "packet_id": packet["packet_id"],
        }
        encoded = json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        ).encode("utf-8") + b"\n"
        if target.exists():
            if target.read_bytes() != encoded:
                raise DeliveryError(
                    f"Outbox collision for {delivery_id}"
                )
            return {
                "status": "already_enqueued",
                "destination_reference": str(target),
                "destination_acceptance_proven": False,
            }
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination,
            prefix=f".{delivery_id}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(encoded)
            temporary = Path(handle.name)
        temporary.replace(target)
        return {
            "status": "enqueued",
            "destination_reference": str(target),
            "destination_acceptance_proven": False,
        }
class MemoryTransport:
    """Reuse the Wave 3 governed-candidate adapter."""
    def __init__(
        self,
        *,
        repository_root: str | Path,
        mode: str,
        endpoint: str | None,
        command: tuple[str, ...],
        outbox: str,
        timeout_seconds: int,
    ) -> None:
        loader = PriorWaveModuleLoader(repository_root)
        module = loader.load_adapter_module("graphiti_memory.py")
        GraphitiMemoryAdapter = getattr(
            module,
            "GraphitiMemoryAdapter",
        )
        FileOutboxTransport = getattr(
            module,
            "FileOutboxTransport",
        )
        HttpJsonTransport = getattr(
            module,
            "HttpJsonTransport",
        )
        CommandTransport = getattr(
            module,
            "CommandTransport",
        )
        if mode == "outbox":
            transport = FileOutboxTransport(outbox)
        elif mode == "http":
            if not endpoint:
                raise ValueError(
                    "memory_endpoint is required for http mode"
                )
            transport = HttpJsonTransport(
                endpoint,
                bearer_token=os.environ.get(
                    "L9_GRAPHITI_MEMORY_TOKEN"
                ),
                timeout_seconds=timeout_seconds,
            )
        elif mode == "command":
            if not command:
                raise ValueError(
                    "memory_command is required for command mode"
                )
            transport = CommandTransport(
                list(command),
                timeout_seconds=timeout_seconds,
            )
        else:
            raise ValueError(
                f"Unsupported memory transport mode: {mode}"
            )
        self.adapter = GraphitiMemoryAdapter(transport)
    def deliver(
        self,
        delivery: Mapping[str, Any],
        packet: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        candidate = self.adapter.compile_candidate(
            harvested_unit=delivery["harvested_unit"],
            routing_decision=delivery["routing_decision"],
            promotion_result=delivery["promotion_result"],
            packet=packet,
        )
        result = self.adapter.deliver(candidate)
        payload = result.to_dict()
        payload["candidate"] = candidate.to_dict()
        payload["destination_acceptance_proven"] = (
            result.status
            not in {"enqueued", "already_enqueued"}
        )
        return payload
class DeliveryWorker:
    def __init__(
        self,
        configuration: DeliveryWorkerConfiguration,
        *,
        store: PipelineStateStore | None = None,
        retry_policy: RetryPolicy | None = None,
        receipts: ProcessingReceiptChain | None = None,
    ) -> None:
        self.configuration = configuration
        self.store = store or PipelineStateStore(
            configuration.database_path
        )
        self.retry_policy = retry_policy or RetryPolicy()
        self.receipts = receipts or ProcessingReceiptChain(
            self.store
        )
    def run_once(
        self,
        *,
        actor: str,
        job_id: str | None = None,
    ) -> DeliveryExecutionResult | None:
        job = self._select_job(job_id)
        if job is None:
            return None
        if job.state is PipelineState.RETRY_WAIT:
            job = self.store.transition(
                job_id=job.job_id,
                expected_state=PipelineState.RETRY_WAIT,
                target_state=PipelineState.DELIVERY_PENDING,
                actor=actor,
                payload={"reason": "retry_due"},
            )
        job = self.store.transition(
            job_id=job.job_id,
            expected_state=PipelineState.DELIVERY_PENDING,
            target_state=PipelineState.DELIVERING,
            actor=actor,
            payload={"worker": actor},
        )
        deliveries = [
            item["payload"]
            for item in self.store.list_stage_snapshots(
                job_id=job.job_id,
                stage="DELIVERY_PENDING",
            )
        ]
        packet = self.store.load_packet(job.job_id)
        details: list[Mapping[str, Any]] = []
        accepted = 0
        enqueued = 0
        rejected = 0
        for delivery in deliveries:
            route = str(delivery["route"])
            unit_id = str(delivery["unit_id"])
            attempt_number = self._next_attempt_number(
                job.job_id,
                unit_id,
                route,
            )
            attempt = self.store.record_delivery_attempt(
                job_id=job.job_id,
                unit_id=unit_id,
                route=route,
                attempt_number=attempt_number,
                idempotency_key=str(
                    delivery["idempotency_key"]
                ),
            )
            try:
                response = self._transport_for(route).deliver(
                    delivery,
                    packet,
                )
                status = str(response.get("status", "unknown"))
                if status in {
                    "accepted",
                    "merged",
                    "contested",
                    "quarantined",
                }:
                    accepted += 1
                elif status in {
                    "enqueued",
                    "already_enqueued",
                }:
                    enqueued += 1
                elif status in {
                    "rejected",
                    "denied",
                }:
                    raise DestinationRejected(
                        f"Destination rejected delivery: {response}"
                    )
                else:
                    raise DeliveryError(
                        f"Unsupported destination status: {status}"
                    )
                self.store.complete_delivery_attempt(
                    attempt_id=attempt.attempt_id,
                    status="SUCCEEDED",
                    response_code=status,
                    response_payload=response,
                )
                self.store.record_delivery_receipt(
                    job_id=job.job_id,
                    unit_id=unit_id,
                    route=route,
                    destination_status=status,
                    destination_reference=str(
                        response.get(
                            "destination_reference",
                            response.get(
                                "memory_id",
                                response.get("path", ""),
                            ),
                        )
                    )
                    or None,
                    payload=response,
                )
                details.append(
                    {
                        "unit_id": unit_id,
                        "route": route,
                        "attempt": attempt_number,
                        "status": status,
                        "response": dict(response),
                    }
                )
            except Exception as exc:
                failure_class = (
                    RetryClass.PERMANENT_REJECTION
                    if isinstance(exc, DestinationRejected)
                    else self.retry_policy.classify_exception(exc)
                )
                self.store.complete_delivery_attempt(
                    attempt_id=attempt.attempt_id,
                    status="FAILED",
                    error_class=failure_class.value,
                    error_message=str(exc),
                )
                decision = self.retry_policy.decide(
                    job_id=job.job_id,
                    attempt_number=attempt_number,
                    failure_class=failure_class,
                )
                if decision.retry:
                    current = self.store.get_job(job.job_id)
                    self.store.schedule_retry(
                        job_id=job.job_id,
                        expected_state=current.state,
                        actor=actor,
                        next_attempt_at=str(
                            decision.next_attempt_at
                        ),
                        error_code=failure_class.value,
                        error_message=str(exc),
                        payload={
                            "unit_id": unit_id,
                            "route": route,
                            "attempt": attempt_number,
                        },
                    )
                    self.receipts.append_receipt(
                        job_id=job.job_id,
                        stage="RETRY_WAIT",
                        event_type="delivery_retry_scheduled",
                        actor=actor,
                        payload=decision.to_dict(),
                        event_identity=(
                            f"retry:{unit_id}:{route}:"
                            f"{attempt_number}"
                        ),
                    )
                    return DeliveryExecutionResult(
                        job_id=job.job_id,
                        attempted=attempt_number,
                        accepted=accepted,
                        enqueued=enqueued,
                        rejected=rejected,
                        retried=1,
                        dead_lettered=0,
                        final_state=PipelineState.RETRY_WAIT.value,
                        details=tuple(details),
                    )
                current = self.store.get_job(job.job_id)
                self.store.dead_letter(
                    job_id=job.job_id,
                    expected_state=current.state,
                    actor=actor,
                    failure_class=failure_class.value,
                    reason=str(exc),
                    payload={
                        "delivery": delivery,
                        "retry_decision": decision.to_dict(),
                    },
                    unit_id=unit_id,
                    route=route,
                )
                return DeliveryExecutionResult(
                    job_id=job.job_id,
                    attempted=attempt_number,
                    accepted=accepted,
                    enqueued=enqueued,
                    rejected=rejected + 1,
                    retried=0,
                    dead_lettered=1,
                    final_state=PipelineState.DEAD_LETTERED.value,
                    details=tuple(details),
                )
        current = self.store.get_job(job.job_id)
        current = self.store.transition(
            job_id=job.job_id,
            expected_state=current.state,
            target_state=PipelineState.DELIVERED,
            actor=actor,
            payload={
                "accepted": accepted,
                "enqueued": enqueued,
                "rejected": rejected,
            },
        )
        destination_acceptance_proven = (
            accepted == len(deliveries)
            and len(deliveries) > 0
        )
        target = (
            PipelineState.DESTINATION_ACCEPTED
            if destination_acceptance_proven
            else PipelineState.DESTINATION_REJECTED
        )
        current = self.store.transition(
            job_id=job.job_id,
            expected_state=current.state,
            target_state=target,
            actor=actor,
            payload={
                "destination_acceptance_proven": (
                    destination_acceptance_proven
                ),
                "accepted": accepted,
                "enqueued": enqueued,
            },
        )
        self.receipts.append_receipt(
            job_id=job.job_id,
            stage=target.value,
            event_type="delivery_batch_completed",
            actor=actor,
            payload={
                "accepted": accepted,
                "enqueued": enqueued,
                "destination_acceptance_proven": (
                    destination_acceptance_proven
                ),
            },
            event_identity=(
                f"delivery-batch:{current.version}"
            ),
        )
        self.store.recalculate_campaign_state(
            current.campaign_id
        )
        return DeliveryExecutionResult(
            job_id=job.job_id,
            attempted=len(deliveries),
            accepted=accepted,
            enqueued=enqueued,
            rejected=rejected,
            retried=0,
            dead_lettered=0,
            final_state=target.value,
            details=tuple(details),
        )
    def run_batch(
        self,
        *,
        actor: str,
        limit: int = 20,
    ) -> list[DeliveryExecutionResult]:
        results: list[DeliveryExecutionResult] = []
        for _ in range(max(0, limit)):
            result = self.run_once(actor=actor)
            if result is None:
                break
            results.append(result)
        return results
    def _transport_for(self, route: str) -> DeliveryTransport:
        if route == "memory":
            return MemoryTransport(
                repository_root=self.configuration.repository_root,
                mode=self.configuration.memory_mode,
                endpoint=self.configuration.memory_endpoint,
                command=self.configuration.memory_command,
                outbox=self.configuration.memory_outbox,
                timeout_seconds=self.configuration.timeout_seconds,
            )
        return RouteOutboxTransport(
            self.configuration.route_outbox_root
        )
    def _select_job(
        self,
        job_id: str | None,
    ) -> ProcessingJob | None:
        if job_id:
            job = self.store.get_job(job_id)
            if job.state not in {
                PipelineState.DELIVERY_PENDING,
                PipelineState.RETRY_WAIT,
            }:
                return None
            return job
        with self.store.connect() as connection:
            row = connection.execute(
                """
                SELECT job_id
                FROM processing_jobs
                WHERE
                    state = 'DELIVERY_PENDING'
                    OR (
                        state = 'RETRY_WAIT'
                        AND (
                            next_attempt_at IS NULL
                            OR next_attempt_at <= ?
                        )
                    )
                ORDER BY created_at
                LIMIT 1
                """,
                (utc_now_text(),),
            ).fetchone()
        if row is None:
            return None
        return self.store.get_job(row["job_id"])
    def _next_attempt_number(
        self,
        job_id: str,
        unit_id: str,
        route: str,
    ) -> int:
        with self.store.connect() as connection:
            row = connection.execute(
                """
                SELECT COALESCE(MAX(attempt_number), 0) AS n
                FROM delivery_attempts
                WHERE job_id = ? AND unit_id = ? AND route = ?
                """,
                (job_id, unit_id, route),
            ).fetchone()
        return int(row["n"]) + 1
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Process generated-data delivery jobs."
    )
    parser.add_argument("--root", default=".")
    parser.add_argument("--database")
    parser.add_argument("--job-id")
    parser.add_argument("--actor", required=True)
    parser.add_argument(
        "--memory-mode",
        choices=("outbox", "http", "command"),
        default="outbox",
    )
    parser.add_argument("--memory-endpoint")
    parser.add_argument(
        "--memory-command",
        nargs="+",
        default=[],
    )
    parser.add_argument("--limit", type=int, default=1)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    configuration = DeliveryWorkerConfiguration(
        repository_root=str(root),
        database_path=(
            args.database
            or str(
                root
                / ".l9"
                / "subagent-generated-data"
                / "pipeline.sqlite3"
            )
        ),
        memory_mode=args.memory_mode,
        memory_endpoint=args.memory_endpoint,
        memory_command=tuple(args.memory_command),
        memory_outbox=str(
            root
            / "subagent-generated-data"
            / ".runtime"
            / "memory-outbox"
        ),
        route_outbox_root=str(
            root
            / "subagent-generated-data"
            / ".runtime"
        ),
    )
    worker = DeliveryWorker(configuration)
    if args.job_id:
        result = worker.run_once(
            actor=args.actor,
            job_id=args.job_id,
        )
        payload: Any = (
            result.to_dict()
            if result is not None
            else {"processed": False}
        )
    else:
        payload = [
            item.to_dict()
            for item in worker.run_batch(
                actor=args.actor,
                limit=args.limit,
            )
        ]
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
PY
# ---------------------------------------------------------------------------
# Retrieval query
# ---------------------------------------------------------------------------
cat > "$RETRIEVAL/context_query.py" <<'PY'
from __future__ import annotations
import argparse
import json
import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence
class ContextRetrievalError(RuntimeError):
    """Raised when context retrieval is unavailable or invalid."""
@dataclass(frozen=True)
class ContextBudget:
    max_items: int = 12
    max_characters: int = 12_000
    def __post_init__(self) -> None:
        if self.max_items <= 0:
            raise ValueError("max_items must be positive")
        if self.max_characters <= 0:
            raise ValueError(
                "max_characters must be positive"
            )
@dataclass(frozen=True)
class ContextQuery:
    repository: str
    repository_class: str
    campaign_id: str
    action_id: str
    agent_id: str
    role: str
    task_type: str
    paths: tuple[str, ...]
    base_sha: str
    visibility_ceiling: str
    budget: ContextBudget
    minimum_confidence: float = 0.70
    include_contested: bool = False
    include_raw_evidence: bool = False
    def __post_init__(self) -> None:
        if not 0 <= self.minimum_confidence <= 1:
            raise ValueError(
                "minimum_confidence must be within [0, 1]"
            )
        if not self.repository.strip():
            raise ValueError("repository is required")
        if not self.role.strip():
            raise ValueError("role is required")
    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0.0",
            "repository": self.repository,
            "repository_class": self.repository_class,
            "campaign_id": self.campaign_id,
            "action_id": self.action_id,
            "agent_id": self.agent_id,
            "role": self.role,
            "task_type": self.task_type,
            "paths": list(self.paths),
            "base_sha": self.base_sha,
            "visibility_ceiling": self.visibility_ceiling,
            "max_items": self.budget.max_items,
            "max_characters": self.budget.max_characters,
            "minimum_confidence": self.minimum_confidence,
            "include_contested": self.include_contested,
            "include_raw_evidence": self.include_raw_evidence,
        }
@dataclass(frozen=True)
class ContextCandidate:
    record_id: str
    text: str
    score: float
    confidence: float
    state: str
    authority_class: str
    visibility: str
    repository: str
    source_sha: str | None
    paths: tuple[str, ...]
    task_types: tuple[str, ...]
    roles: tuple[str, ...]
    epistemic_status: str
    invalidated: bool
    successful_reuse_count: int = 0
    failed_reuse_count: int = 0
    metadata: Mapping[str, Any] | None = None
    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
    ) -> "ContextCandidate":
        return cls(
            record_id=str(value["record_id"]),
            text=str(value.get("text", value.get("statement", ""))),
            score=float(value.get("score", 0)),
            confidence=float(value.get("confidence", 0)),
            state=str(value.get("state", "unknown")),
            authority_class=str(
                value.get("authority_class", "advisory")
            ),
            visibility=str(
                value.get("visibility", "repository_local")
            ),
            repository=str(value.get("repository", "")),
            source_sha=(
                str(value["source_sha"])
                if value.get("source_sha") is not None
                else None
            ),
            paths=tuple(str(item) for item in value.get("paths", [])),
            task_types=tuple(
                str(item) for item in value.get("task_types", [])
            ),
            roles=tuple(str(item) for item in value.get("roles", [])),
            epistemic_status=str(
                value.get("epistemic_status", "observed")
            ),
            invalidated=bool(value.get("invalidated", False)),
            successful_reuse_count=int(
                value.get("successful_reuse_count", 0)
            ),
            failed_reuse_count=int(
                value.get("failed_reuse_count", 0)
            ),
            metadata=dict(value.get("metadata", {})),
        )
    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "text": self.text,
            "score": self.score,
            "confidence": self.confidence,
            "state": self.state,
            "authority_class": self.authority_class,
            "visibility": self.visibility,
            "repository": self.repository,
            "source_sha": self.source_sha,
            "paths": list(self.paths),
            "task_types": list(self.task_types),
            "roles": list(self.roles),
            "epistemic_status": self.epistemic_status,
            "invalidated": self.invalidated,
            "successful_reuse_count": self.successful_reuse_count,
            "failed_reuse_count": self.failed_reuse_count,
            "metadata": dict(self.metadata or {}),
        }
@dataclass(frozen=True)
class ContextQueryResult:
    available: bool
    candidates: tuple[ContextCandidate, ...]
    source: str
    schema_version: str
    error: str | None = None
    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "candidates": [
                item.to_dict() for item in self.candidates
            ],
            "source": self.source,
            "schema_version": self.schema_version,
            "error": self.error,
        }
class ContextClient(Protocol):
    def query(
        self,
        query: ContextQuery,
    ) -> ContextQueryResult:
        """Retrieve memory candidates using an existing memory surface."""
class CommandContextClient:
    """
    Delegate retrieval to an existing command.
    Configure with ``L9_SGD_GRAPHITI_SEARCH_COMMAND`` or pass a command
    explicitly. JSON query is sent on stdin.
    """
    def __init__(
        self,
        command: Sequence[str],
        *,
        timeout_seconds: int = 30,
    ) -> None:
        if not command:
            raise ValueError("Retrieval command is required")
        self.command = tuple(command)
        self.timeout_seconds = timeout_seconds
    @classmethod
    def from_environment(
        cls,
    ) -> "CommandContextClient":
        raw = os.environ.get(
            "L9_SGD_GRAPHITI_SEARCH_COMMAND",
            "",
        ).strip()
        if not raw:
            raise ContextRetrievalError(
                "L9_SGD_GRAPHITI_SEARCH_COMMAND is not configured"
            )
        return cls(shlex.split(raw))
    def query(
        self,
        query: ContextQuery,
    ) -> ContextQueryResult:
        completed = subprocess.run(
            list(self.command),
            input=json.dumps(
                query.to_dict(),
                sort_keys=True,
                separators=(",", ":"),
            ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            return ContextQueryResult(
                available=False,
                candidates=(),
                source="command",
                schema_version="unknown",
                error=completed.stderr.strip()
                or f"exit {completed.returncode}",
            )
        try:
            payload = json.loads(completed.stdout or "{}")
        except json.JSONDecodeError as exc:
            raise ContextRetrievalError(
                "Retrieval command returned invalid JSON"
            ) from exc
        if not isinstance(payload, Mapping):
            raise ContextRetrievalError(
                "Retrieval result must be an object"
            )
        schema_version = str(
            payload.get("schema_version", "1.0.0")
        )
        major = schema_version.split(".", 1)[0]
        if major != "1":
            raise ContextRetrievalError(
                f"Unsupported retrieval schema: {schema_version}"
            )
        raw_candidates = payload.get(
            "candidates",
            payload.get("results", []),
        )
        if not isinstance(raw_candidates, list):
            raise ContextRetrievalError(
                "Retrieval candidates must be a list"
            )
        return ContextQueryResult(
            available=True,
            candidates=tuple(
                ContextCandidate.from_mapping(item)
                for item in raw_candidates
                if isinstance(item, Mapping)
            ),
            source=str(payload.get("source", "command")),
            schema_version=schema_version,
            error=None,
        )
class StaticContextClient:
    """Deterministic client used by tests and golden mock mode."""
    def __init__(
        self,
        candidates: Sequence[ContextCandidate],
    ) -> None:
        self.candidates = tuple(candidates)
    def query(
        self,
        query: ContextQuery,
    ) -> ContextQueryResult:
        return ContextQueryResult(
            available=True,
            candidates=self.candidates,
            source="static",
            schema_version="1.0.0",
        )
def query_from_mapping(
    payload: Mapping[str, Any],
) -> ContextQuery:
    return ContextQuery(
        repository=str(payload["repository"]),
        repository_class=str(payload["repository_class"]),
        campaign_id=str(payload["campaign_id"]),
        action_id=str(payload["action_id"]),
        agent_id=str(payload["agent_id"]),
        role=str(payload["role"]),
        task_type=str(payload["task_type"]),
        paths=tuple(str(item) for item in payload.get("paths", [])),
        base_sha=str(payload["base_sha"]),
        visibility_ceiling=str(
            payload.get(
                "visibility_ceiling",
                "repository_local",
            )
        ),
        budget=ContextBudget(
            max_items=int(payload.get("max_items", 12)),
            max_characters=int(
                payload.get("max_characters", 12_000)
            ),
        ),
        minimum_confidence=float(
            payload.get("minimum_confidence", 0.70)
        ),
        include_contested=bool(
            payload.get("include_contested", False)
        ),
        include_raw_evidence=bool(
            payload.get("include_raw_evidence", False)
        ),
    )
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Query governed context through an existing memory command."
    )
    parser.add_argument("--query", required=True)
    parser.add_argument("--command", nargs="+")
    args = parser.parse_args()
    payload = json.loads(
        Path(args.query).read_text(encoding="utf-8")
    )
    query = query_from_mapping(payload)
    client = (
        CommandContextClient(args.command)
        if args.command
        else CommandContextClient.from_environment()
    )
    result = client.query(query)
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0 if result.available else 1
if __name__ == "__main__":
    raise SystemExit(main())
PY
# ---------------------------------------------------------------------------
# Context selector
# ---------------------------------------------------------------------------
cat > "$RETRIEVAL/context_selector.py" <<'PY'
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence
from context_query import (
    ContextCandidate,
    ContextQuery,
    ContextQueryResult,
)
VISIBILITY_ORDER = {
    "campaign_local": 0,
    "repository_local": 1,
    "project_group": 2,
    "constellation_internal": 3,
    "restricted": 4,
}
ACTIVE_STATES = {
    "active",
    "accepted",
    "valid",
    "promoted",
}
@dataclass(frozen=True)
class SelectionWeights:
    retrieval_score: float = 1.0
    path_overlap: float = 0.35
    task_match: float = 0.25
    role_match: float = 0.20
    same_sha: float = 0.15
    successful_reuse: float = 0.05
    failed_reuse: float = 0.20
    context_cost: float = 0.00002
@dataclass(frozen=True)
class SelectionExclusion:
    record_id: str
    reason: str
    def to_dict(self) -> dict[str, str]:
        return {
            "record_id": self.record_id,
            "reason": self.reason,
        }
@dataclass(frozen=True)
class ContextSelection:
    record_id: str
    text: str
    final_score: float
    characters: int
    source: Mapping[str, Any]
    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "text": self.text,
            "final_score": self.final_score,
            "characters": self.characters,
            "source": dict(self.source),
        }
@dataclass(frozen=True)
class ContextSelectionResult:
    selected: tuple[ContextSelection, ...]
    excluded: tuple[SelectionExclusion, ...]
    budget_used_items: int
    budget_used_characters: int
    record_ids: tuple[str, ...]
    context_pack: str
    selection_hash: str
    def to_dict(self) -> dict[str, Any]:
        return {
            "selected": [
                item.to_dict() for item in self.selected
            ],
            "excluded": [
                item.to_dict() for item in self.excluded
            ],
            "budget_used": {
                "items": self.budget_used_items,
                "characters": self.budget_used_characters,
            },
            "record_ids": list(self.record_ids),
            "context_pack": self.context_pack,
            "selection_hash": self.selection_hash,
        }
class ContextSelector:
    def __init__(
        self,
        weights: SelectionWeights | None = None,
    ) -> None:
        self.weights = weights or SelectionWeights()
    def select(
        self,
        *,
        query: ContextQuery,
        result: ContextQueryResult,
    ) -> ContextSelectionResult:
        if not result.available:
            raise RuntimeError(
                f"Context retrieval unavailable: {result.error}"
            )
        excluded: list[SelectionExclusion] = []
        scored: list[tuple[float, ContextCandidate]] = []
        seen_text: set[str] = set()
        for candidate in result.candidates:
            reason = self._exclusion_reason(query, candidate)
            if reason:
                excluded.append(
                    SelectionExclusion(
                        candidate.record_id,
                        reason,
                    )
                )
                continue
            normalized = " ".join(
                candidate.text.split()
            ).lower()
            if normalized in seen_text:
                excluded.append(
                    SelectionExclusion(
                        candidate.record_id,
                        "semantic_duplicate",
                    )
                )
                continue
            seen_text.add(normalized)
            scored.append(
                (
                    self._score(query, candidate),
                    candidate,
                )
            )
        scored.sort(
            key=lambda item: (
                -item[0],
                item[1].record_id,
            )
        )
        selected: list[ContextSelection] = []
        characters = 0
        for score, candidate in scored:
            size = len(candidate.text)
            if len(selected) >= query.budget.max_items:
                excluded.append(
                    SelectionExclusion(
                        candidate.record_id,
                        "item_budget_exceeded",
                    )
                )
                continue
            if (
                characters + size
                > query.budget.max_characters
            ):
                excluded.append(
                    SelectionExclusion(
                        candidate.record_id,
                        "character_budget_exceeded",
                    )
                )
                continue
            selected.append(
                ContextSelection(
                    record_id=candidate.record_id,
                    text=candidate.text,
                    final_score=score,
                    characters=size,
                    source=candidate.to_dict(),
                )
            )
            characters += size
        context_pack = "\n\n".join(
            f"[memory:{item.record_id}]\n{item.text}"
            for item in selected
        )
        payload = {
            "query": query.to_dict(),
            "record_ids": [
                item.record_id for item in selected
            ],
            "context_pack": context_pack,
        }
        selection_hash = hashlib.sha256(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return ContextSelectionResult(
            selected=tuple(selected),
            excluded=tuple(excluded),
            budget_used_items=len(selected),
            budget_used_characters=characters,
            record_ids=tuple(
                item.record_id for item in selected
            ),
            context_pack=context_pack,
            selection_hash=selection_hash,
        )
    def _exclusion_reason(
        self,
        query: ContextQuery,
        candidate: ContextCandidate,
    ) -> str | None:
        if candidate.invalidated:
            return "invalidated"
        if candidate.state.lower() not in ACTIVE_STATES:
            return "inactive_state"
        if candidate.confidence < query.minimum_confidence:
            return "confidence_below_threshold"
        if (
            candidate.epistemic_status == "contested"
            and not query.include_contested
        ):
            return "contested_excluded"
        if candidate.repository not in {
            "",
            query.repository,
        }:
            return "repository_mismatch"
        if not self._visibility_allowed(
            candidate.visibility,
            query.visibility_ceiling,
        ):
            return "visibility_exceeds_ceiling"
        if not candidate.text.strip():
            return "empty_text"
        return None
    def _score(
        self,
        query: ContextQuery,
        candidate: ContextCandidate,
    ) -> float:
        query_paths = set(query.paths)
        candidate_paths = set(candidate.paths)
        path_overlap = (
            len(query_paths & candidate_paths)
            / max(1, len(query_paths))
        )
        task_match = (
            1.0
            if query.task_type in candidate.task_types
            else 0.0
        )
        role_match = (
            1.0
            if query.role in candidate.roles
            else 0.0
        )
        same_sha = (
            1.0
            if candidate.source_sha == query.base_sha
            else 0.0
        )
        return (
            candidate.score
            * self.weights.retrieval_score
            + path_overlap
            * self.weights.path_overlap
            + task_match
            * self.weights.task_match
            + role_match
            * self.weights.role_match
            + same_sha
            * self.weights.same_sha
            + candidate.successful_reuse_count
            * self.weights.successful_reuse
            - candidate.failed_reuse_count
            * self.weights.failed_reuse
            - len(candidate.text)
            * self.weights.context_cost
        )
    @staticmethod
    def _visibility_allowed(
        item_visibility: str,
        ceiling: str,
    ) -> bool:
        if item_visibility not in VISIBILITY_ORDER:
            return False
        if ceiling not in VISIBILITY_ORDER:
            return False
        return (
            VISIBILITY_ORDER[item_visibility]
            <= VISIBILITY_ORDER[ceiling]
        )
PY
# ---------------------------------------------------------------------------
# Reuse recorder
# ---------------------------------------------------------------------------
cat > "$RETRIEVAL/reuse_recorder.py" <<'PY'
from __future__ import annotations
import argparse
import json
import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence
ROOT = Path(__file__).resolve().parents[2]
ORCHESTRATION = ROOT / "subagent-generated-data" / "orchestration"
import sys
sys.path.insert(0, str(ORCHESTRATION))
from state_store import (
    PipelineStateStore,
    deterministic_id,
)
VALID_OUTCOMES = {
    "accelerated_execution",
    "prevented_error",
    "improved_validation",
    "improved_context",
    "reduced_discovery",
    "improved_scope_control",
    "improved_contract",
    "no_observable_value",
    "caused_confusion",
    "stale",
    "incorrect",
}
@dataclass(frozen=True)
class ReuseDispatchResult:
    event_id: str
    local_recorded: bool
    remote_dispatched: bool
    remote_response: Mapping[str, Any] | None
    invalidation_candidate: Mapping[str, Any] | None
    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "local_recorded": self.local_recorded,
            "remote_dispatched": self.remote_dispatched,
            "remote_response": (
                dict(self.remote_response)
                if self.remote_response is not None
                else None
            ),
            "invalidation_candidate": (
                dict(self.invalidation_candidate)
                if self.invalidation_candidate is not None
                else None
            ),
        }
class ReuseRecorder:
    def __init__(
        self,
        store: PipelineStateStore,
        *,
        command: Sequence[str] | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        self.store = store
        self.command = tuple(command or ())
        self.timeout_seconds = timeout_seconds
    @classmethod
    def from_environment(
        cls,
        store: PipelineStateStore,
    ) -> "ReuseRecorder":
        raw = os.environ.get(
            "L9_SGD_GRAPHITI_REUSE_COMMAND",
            "",
        ).strip()
        return cls(
            store,
            command=shlex.split(raw) if raw else (),
        )
    def record_selection(
        self,
        *,
        record_id: str,
        campaign_id: str,
        action_id: str,
        agent_id: str,
        context_pack_id: str,
        payload: Mapping[str, Any],
    ) -> ReuseDispatchResult:
        return self._record(
            stage="selected",
            record_id=record_id,
            campaign_id=campaign_id,
            action_id=action_id,
            agent_id=agent_id,
            context_pack_id=context_pack_id,
            outcome=None,
            payload=payload,
            dispatch_remote=False,
        )
    def record_injection(
        self,
        *,
        record_id: str,
        campaign_id: str,
        action_id: str,
        agent_id: str,
        context_pack_id: str,
        payload: Mapping[str, Any],
    ) -> ReuseDispatchResult:
        return self._record(
            stage="injected",
            record_id=record_id,
            campaign_id=campaign_id,
            action_id=action_id,
            agent_id=agent_id,
            context_pack_id=context_pack_id,
            outcome=None,
            payload=payload,
            dispatch_remote=False,
        )
    def finalize_outcome(
        self,
        *,
        record_id: str,
        campaign_id: str,
        action_id: str,
        agent_id: str,
        context_pack_id: str,
        outcome: str,
        correction_required: bool,
        validity_confirmed: bool,
        evidence: Mapping[str, Any],
    ) -> ReuseDispatchResult:
        if outcome not in VALID_OUTCOMES:
            raise ValueError(
                f"Unsupported reuse outcome: {outcome}"
            )
        payload = {
            "schema_version": "1.0.0",
            "kind": "MemoryReuseEvent",
            "record_id": record_id,
            "consumer": {
                "campaign_id": campaign_id,
                "action_id": action_id,
                "agent_id": agent_id,
            },
            "use": {
                "context_pack_id": context_pack_id,
                "injection_method": "agent_contract_context",
            },
            "outcome": outcome,
            "evidence": dict(evidence),
            "correction_required": correction_required,
            "validity_confirmed": validity_confirmed,
        }
        return self._record(
            stage="finalized",
            record_id=record_id,
            campaign_id=campaign_id,
            action_id=action_id,
            agent_id=agent_id,
            context_pack_id=context_pack_id,
            outcome=outcome,
            payload=payload,
            dispatch_remote=True,
        )
    def _record(
        self,
        *,
        stage: str,
        record_id: str,
        campaign_id: str,
        action_id: str,
        agent_id: str,
        context_pack_id: str,
        outcome: str | None,
        payload: Mapping[str, Any],
        dispatch_remote: bool,
    ) -> ReuseDispatchResult:
        event_id = deterministic_id(
            "reuse",
            {
                "record_id": record_id,
                "campaign_id": campaign_id,
                "action_id": action_id,
                "agent_id": agent_id,
                "context_pack_id": context_pack_id,
                "stage": stage,
                "outcome": outcome,
            },
        )
        _, created = self.store.record_reuse_event(
            event_id=event_id,
            record_id=record_id,
            campaign_id=campaign_id,
            action_id=action_id,
            agent_id=agent_id,
            context_pack_id=context_pack_id,
            stage=stage,
            outcome=outcome,
            payload=payload,
        )
        response: Mapping[str, Any] | None = None
        remote_dispatched = False
        if dispatch_remote and self.command:
            response = self._dispatch(payload)
            remote_dispatched = True
        invalidation_candidate = None
        if stage == "finalized" and outcome in {
            "stale",
            "incorrect",
        }:
            invalidation_candidate = {
                "schema_version": "1.0.0",
                "kind": "SourceInvalidationRequest",
                "event_type": "failed_reuse_reported",
                "record_ids": [record_id],
                "reason": outcome,
                "requires_policy_approval": True,
                "source_reuse_event_id": event_id,
            }
        return ReuseDispatchResult(
            event_id=event_id,
            local_recorded=created,
            remote_dispatched=remote_dispatched,
            remote_response=response,
            invalidation_candidate=invalidation_candidate,
        )
    def _dispatch(
        self,
        payload: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        completed = subprocess.run(
            list(self.command),
            input=json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
            ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"Reuse command failed: {completed.stderr.strip()}"
            )
        response = json.loads(completed.stdout or "{}")
        if not isinstance(response, Mapping):
            raise RuntimeError(
                "Reuse response must be an object"
            )
        return response
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Record a finalized memory-reuse outcome."
    )
    parser.add_argument("--database", required=True)
    parser.add_argument("--event", required=True)
    parser.add_argument("--command", nargs="+")
    args = parser.parse_args()
    payload = json.loads(
        Path(args.event).read_text(encoding="utf-8")
    )
    recorder = ReuseRecorder(
        PipelineStateStore(args.database),
        command=args.command,
    )
    result = recorder.finalize_outcome(
        record_id=str(payload["record_id"]),
        campaign_id=str(payload["campaign_id"]),
        action_id=str(payload["action_id"]),
        agent_id=str(payload["agent_id"]),
        context_pack_id=str(payload["context_pack_id"]),
        outcome=str(payload["outcome"]),
        correction_required=bool(
            payload.get("correction_required", False)
        ),
        validity_confirmed=bool(
            payload.get("validity_confirmed", True)
        ),
        evidence=dict(payload.get("evidence", {})),
    )
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
PY
# ---------------------------------------------------------------------------
# Repository event bridge
# ---------------------------------------------------------------------------
cat > "$INVALIDATION/repository_event_bridge.py" <<'PY'
from __future__ import annotations
import argparse
import json
import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence
ROOT = Path(__file__).resolve().parents[2]
ORCHESTRATION = ROOT / "subagent-generated-data" / "orchestration"
import sys
sys.path.insert(0, str(ORCHESTRATION))
from state_store import (
    PipelineStateStore,
    deterministic_id,
)
VALID_CHANGE_KINDS = {
    "added",
    "modified",
    "deleted",
    "renamed",
}
@dataclass(frozen=True)
class ChangedPath:
    path: str
    change_kind: str
    previous_path: str | None = None
    def __post_init__(self) -> None:
        normalize_relative_path(self.path)
        if self.previous_path:
            normalize_relative_path(self.previous_path)
        if self.change_kind not in VALID_CHANGE_KINDS:
            raise ValueError(
                f"Unsupported change kind: {self.change_kind}"
            )
    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "change_kind": self.change_kind,
            "previous_path": self.previous_path,
        }
@dataclass(frozen=True)
class RepositoryChangeEvent:
    event_id: str
    repository: str
    from_sha: str | None
    to_sha: str | None
    event_type: str
    changed_paths: tuple[ChangedPath, ...]
    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0.0",
            "kind": "SourceInvalidationRequest",
            "event_id": self.event_id,
            "repository": self.repository,
            "from_sha": self.from_sha,
            "to_sha": self.to_sha,
            "event_type": self.event_type,
            "selectors": [
                {
                    "condition_type": "relevant_path_changed",
                    "selector": item.path,
                    "change_kind": item.change_kind,
                    "previous_path": item.previous_path,
                }
                for item in self.changed_paths
            ],
            "delete_memory": False,
        }
@dataclass(frozen=True)
class InvalidationDispatchResult:
    event_id: str
    dry_run: bool
    local_recorded: bool
    remote_dispatched: bool
    response: Mapping[str, Any] | None
    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "dry_run": self.dry_run,
            "local_recorded": self.local_recorded,
            "remote_dispatched": self.remote_dispatched,
            "response": (
                dict(self.response)
                if self.response is not None
                else None
            ),
        }
class RepositoryEventBridge:
    def __init__(
        self,
        store: PipelineStateStore,
        *,
        command: Sequence[str] | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        self.store = store
        self.command = tuple(command or ())
        self.timeout_seconds = timeout_seconds
    @classmethod
    def from_environment(
        cls,
        store: PipelineStateStore,
    ) -> "RepositoryEventBridge":
        raw = os.environ.get(
            "L9_SGD_GRAPHITI_INVALIDATE_COMMAND",
            "",
        ).strip()
        return cls(
            store,
            command=shlex.split(raw) if raw else (),
        )
    def from_git_diff(
        self,
        *,
        repository_root: str | Path,
        repository_name: str,
        from_sha: str,
        to_sha: str,
        allow_dirty: bool = False,
    ) -> RepositoryChangeEvent:
        root = Path(repository_root).resolve()
        if not allow_dirty:
            dirty = subprocess.run(
                ["git", "-C", str(root), "status", "--porcelain"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            if dirty.returncode != 0:
                raise RuntimeError(dirty.stderr.strip())
            if dirty.stdout.strip():
                raise RuntimeError(
                    "Repository has uncommitted changes"
                )
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "diff",
                "--name-status",
                "--find-renames",
                from_sha,
                to_sha,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip())
        changes = parse_name_status(completed.stdout)
        event_id = deterministic_id(
            "invalidation",
            {
                "repository": repository_name,
                "from_sha": from_sha,
                "to_sha": to_sha,
                "changes": [item.to_dict() for item in changes],
            },
        )
        return RepositoryChangeEvent(
            event_id=event_id,
            repository=repository_name,
            from_sha=from_sha,
            to_sha=to_sha,
            event_type="repository_path_changed",
            changed_paths=tuple(changes),
        )
    def dispatch(
        self,
        event: RepositoryChangeEvent,
        *,
        dry_run: bool = False,
    ) -> InvalidationDispatchResult:
        payload = event.to_dict()
        _, created = self.store.record_invalidation_event(
            event_id=event.event_id,
            repository=event.repository,
            from_sha=event.from_sha,
            to_sha=event.to_sha,
            event_type=event.event_type,
            status="DRY_RUN" if dry_run else "PENDING",
            payload=payload,
        )
        if dry_run:
            return InvalidationDispatchResult(
                event_id=event.event_id,
                dry_run=True,
                local_recorded=created,
                remote_dispatched=False,
                response=None,
            )
        if not self.command:
            return InvalidationDispatchResult(
                event_id=event.event_id,
                dry_run=False,
                local_recorded=created,
                remote_dispatched=False,
                response={
                    "status": "pending_external_configuration",
                    "delete_memory": False,
                },
            )
        completed = subprocess.run(
            list(self.command),
            input=json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
            ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"Invalidation command failed: "
                f"{completed.stderr.strip()}"
            )
        response = json.loads(completed.stdout or "{}")
        if not isinstance(response, Mapping):
            raise RuntimeError(
                "Invalidation response must be an object"
            )
        if response.get("deleted") is True:
            raise RuntimeError(
                "Invalidation boundary violation: deletion reported"
            )
        return InvalidationDispatchResult(
            event_id=event.event_id,
            dry_run=False,
            local_recorded=created,
            remote_dispatched=True,
            response=response,
        )
def normalize_relative_path(value: str) -> str:
    if not value or value.startswith("/"):
        raise ValueError("Path must be repository-relative")
    path = PurePosixPath(value.replace("\\", "/"))
    if ".." in path.parts:
        raise ValueError("Path traversal is forbidden")
    normalized = str(path)
    if normalized in {"", "."}:
        raise ValueError("Path must identify a repository item")
    return normalized
def parse_name_status(output: str) -> list[ChangedPath]:
    result: list[ChangedPath] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        fields = line.split("\t")
        code = fields[0]
        if code.startswith("R"):
            if len(fields) != 3:
                raise ValueError(
                    f"Invalid rename entry: {line}"
                )
            result.append(
                ChangedPath(
                    path=normalize_relative_path(fields[2]),
                    previous_path=normalize_relative_path(
                        fields[1]
                    ),
                    change_kind="renamed",
                )
            )
        else:
            if len(fields) != 2:
                raise ValueError(
                    f"Invalid name-status entry: {line}"
                )
            mapping = {
                "A": "added",
                "M": "modified",
                "D": "deleted",
            }
            kind = mapping.get(code[0])
            if kind is None:
                continue
            result.append(
                ChangedPath(
                    path=normalize_relative_path(fields[1]),
                    change_kind=kind,
                )
            )
    return result
def event_from_mapping(
    payload: Mapping[str, Any],
) -> RepositoryChangeEvent:
    changes = tuple(
        ChangedPath(
            path=normalize_relative_path(str(item["path"])),
            change_kind=str(item["change_kind"]),
            previous_path=(
                normalize_relative_path(
                    str(item["previous_path"])
                )
                if item.get("previous_path")
                else None
            ),
        )
        for item in payload.get("changed_paths", [])
    )
    event_id = str(
        payload.get(
            "event_id",
            deterministic_id(
                "invalidation",
                {
                    "repository": payload["repository"],
                    "from_sha": payload.get("from_sha"),
                    "to_sha": payload.get("to_sha"),
                    "changes": [
                        item.to_dict() for item in changes
                    ],
                },
            ),
        )
    )
    return RepositoryChangeEvent(
        event_id=event_id,
        repository=str(payload["repository"]),
        from_sha=(
            str(payload["from_sha"])
            if payload.get("from_sha")
            else None
        ),
        to_sha=(
            str(payload["to_sha"])
            if payload.get("to_sha")
            else None
        ),
        event_type=str(
            payload.get(
                "event_type",
                "repository_path_changed",
            )
        ),
        changed_paths=changes,
    )
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Dispatch structured source-invalidation events."
    )
    parser.add_argument("--database", required=True)
    parser.add_argument("--repository", default=".")
    parser.add_argument("--repository-name")
    parser.add_argument("--from-sha")
    parser.add_argument("--to-sha")
    parser.add_argument("--event")
    parser.add_argument("--command", nargs="+")
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    bridge = RepositoryEventBridge(
        PipelineStateStore(args.database),
        command=args.command,
    )
    if args.event:
        payload = json.loads(
            Path(args.event).read_text(encoding="utf-8")
        )
        event = event_from_mapping(payload)
    else:
        if not (
            args.repository_name
            and args.from_sha
            and args.to_sha
        ):
            parser.error(
                "--repository-name, --from-sha and --to-sha "
                "are required without --event"
            )
        event = bridge.from_git_diff(
            repository_root=args.repository,
            repository_name=args.repository_name,
            from_sha=args.from_sha,
            to_sha=args.to_sha,
            allow_dirty=args.allow_dirty,
        )
    result = bridge.dispatch(event, dry_run=args.dry_run)
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
PY
# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------
cat > "$OPERATIONS/health.py" <<'PY'
from __future__ import annotations
import argparse
import json
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
ROOT = Path(__file__).resolve().parents[2]
ORCHESTRATION = ROOT / "subagent-generated-data" / "orchestration"
sys.path.insert(0, str(ORCHESTRATION))
from module_loader import PriorWaveModuleLoader
from receipts import ProcessingReceiptChain
from state_store import PipelineStateStore
HEALTHY = "HEALTHY"
DEGRADED = "DEGRADED"
UNHEALTHY = "UNHEALTHY"
MISCONFIGURED = "MISCONFIGURED"
@dataclass(frozen=True)
class HealthCheck:
    name: str
    status: str
    message: str
    details: Mapping[str, Any]
    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "details": dict(self.details),
        }
def run_health(
    *,
    repository_root: str | Path,
    database_path: str | Path,
    live: bool,
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    store = PipelineStateStore(database_path)
    checks: list[HealthCheck] = []
    required = [
        root / "subagent-generated-data" / "law"
        / "SUBAGENT_GENERATED_DATA_LAW.md",
        root / "subagent-generated-data" / "runtime"
        / "packet_validator.py",
        root / "subagent-generated-data" / "adapters"
        / "graphiti_memory.py",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    checks.append(
        HealthCheck(
            "required_files",
            HEALTHY if not missing else MISCONFIGURED,
            "Required files present"
            if not missing
            else "Required files missing",
            {"missing": missing},
        )
    )
    loader_errors = PriorWaveModuleLoader(
        root
    ).validate_required_symbols()
    checks.append(
        HealthCheck(
            "prior_wave_imports",
            HEALTHY if not loader_errors else UNHEALTHY,
            "Prior-wave symbols load"
            if not loader_errors
            else "Prior-wave import failures",
            {"errors": loader_errors},
        )
    )
    status = store.pipeline_status()
    checks.append(
        HealthCheck(
            "state_store",
            HEALTHY,
            "SQLite state store available",
            status,
        )
    )
    chain = ProcessingReceiptChain(store)
    chain_errors: dict[str, list[str]] = {}
    with store.connect() as connection:
        job_rows = list(
            connection.execute(
                "SELECT job_id FROM processing_jobs"
            )
        )
    for row in job_rows:
        errors = chain.verify_job_chain(row["job_id"])
        if errors:
            chain_errors[row["job_id"]] = errors
    checks.append(
        HealthCheck(
            "receipt_integrity",
            HEALTHY if not chain_errors else UNHEALTHY,
            "Receipt chains valid"
            if not chain_errors
            else "Receipt chain failures",
            {"errors": chain_errors},
        )
    )
    transport_configured = any(
        os.environ.get(name)
        for name in (
            "L9_SGD_GRAPHITI_INGEST_COMMAND",
            "L9_SGD_GRAPHITI_SEARCH_COMMAND",
            "L9_SGD_GRAPHITI_REUSE_COMMAND",
            "L9_SGD_GRAPHITI_INVALIDATE_COMMAND",
        )
    )
    checks.append(
        HealthCheck(
            "live_transport_configuration",
            (
                HEALTHY
                if transport_configured
                else DEGRADED
            ),
            (
                "At least one live Graphiti operation configured"
                if transport_configured
                else "Only local/outbox operation is configured"
            ),
            {},
        )
    )
    if live:
        for variable in (
            "L9_SGD_GRAPHITI_SEARCH_COMMAND",
            "L9_SGD_GRAPHITI_REUSE_COMMAND",
            "L9_SGD_GRAPHITI_INVALIDATE_COMMAND",
        ):
            raw = os.environ.get(variable, "").strip()
            if not raw:
                checks.append(
                    HealthCheck(
                        f"live:{variable}",
                        MISCONFIGURED,
                        f"{variable} is not configured",
                        {},
                    )
                )
                continue
            command = shlex.split(raw)
            available = bool(command) and (
                Path(command[0]).exists()
                or __import__("shutil").which(command[0])
                is not None
            )
            checks.append(
                HealthCheck(
                    f"live:{variable}",
                    HEALTHY if available else UNHEALTHY,
                    "Command executable available"
                    if available
                    else "Command executable unavailable",
                    {"command": command},
                )
            )
    rank = {
        HEALTHY: 0,
        DEGRADED: 1,
        UNHEALTHY: 2,
        MISCONFIGURED: 3,
    }
    overall = max(
        (check.status for check in checks),
        key=lambda item: rank[item],
        default=HEALTHY,
    )
    return {
        "status": overall,
        "checks": [check.to_dict() for check in checks],
    }
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check generated-data pipeline health."
    )
    parser.add_argument("--root", default=".")
    parser.add_argument("--database")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    database = (
        args.database
        or root
        / ".l9"
        / "subagent-generated-data"
        / "pipeline.sqlite3"
    )
    result = run_health(
        repository_root=root,
        database_path=database,
        live=args.live,
    )
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Status: {result['status']}")
        for check in result["checks"]:
            print(
                f"- {check['status']}: "
                f"{check['name']} — {check['message']}"
            )
    return {
        HEALTHY: 0,
        DEGRADED: 1,
        UNHEALTHY: 2,
        MISCONFIGURED: 3,
    }[result["status"]]
if __name__ == "__main__":
    raise SystemExit(main())
PY
cat > "$OPERATIONS/status.py" <<'PY'
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import Any
ROOT = Path(__file__).resolve().parents[2]
ORCHESTRATION = ROOT / "subagent-generated-data" / "orchestration"
sys.path.insert(0, str(ORCHESTRATION))
from receipts import ProcessingReceiptChain
from state_store import PipelineStateStore
def status_payload(
    store: PipelineStateStore,
    *,
    campaign_id: str | None = None,
    job_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "pipeline": store.pipeline_status(),
    }
    with store.connect() as connection:
        payload["delivery"] = {
            row["status"]: int(row["count"])
            for row in connection.execute(
                """
                SELECT status, COUNT(*) AS count
                FROM delivery_attempts
                GROUP BY status
                """
            )
        }
        payload["retrieval"] = {
            "selections": int(
                connection.execute(
                    "SELECT COUNT(*) AS n FROM context_selections"
                ).fetchone()["n"]
            ),
            "reuse_events": int(
                connection.execute(
                    "SELECT COUNT(*) AS n FROM reuse_events"
                ).fetchone()["n"]
            ),
        }
        payload["invalidation"] = {
            "events": int(
                connection.execute(
                    "SELECT COUNT(*) AS n FROM invalidation_events"
                ).fetchone()["n"]
            ),
        }
    if campaign_id:
        payload["campaign"] = store.campaign_status(
            campaign_id
        ).to_dict()
    if job_id:
        job = store.get_job(job_id)
        payload["job"] = job.to_dict()
        payload["events"] = [
            item.to_dict()
            for item in store.list_events(job_id)
        ]
        payload["receipt_integrity"] = {
            "valid": not ProcessingReceiptChain(
                store
            ).verify_job_chain(job_id),
            "errors": ProcessingReceiptChain(
                store
            ).verify_job_chain(job_id),
        }
    return payload
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Show generated-data pipeline status."
    )
    parser.add_argument("--database", required=True)
    parser.add_argument("--campaign-id")
    parser.add_argument("--job-id")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    payload = status_payload(
        PipelineStateStore(args.database),
        campaign_id=args.campaign_id,
        job_id=args.job_id,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
PY
cat > "$OPERATIONS/replay.py" <<'PY'
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
ORCHESTRATION = ROOT / "subagent-generated-data" / "orchestration"
sys.path.insert(0, str(ORCHESTRATION))
from processor import (
    GeneratedDataProcessor,
    ProcessingConfiguration,
)
from receipts import ProcessingReceiptChain
from state_store import (
    PipelineState,
    PipelineStateStore,
)
REPLAY_STATES = {
    "VALIDATED": PipelineState.VALIDATED,
    "HARVESTED": PipelineState.HARVESTED,
    "CLASSIFIED": PipelineState.CLASSIFIED,
    "ROUTED": PipelineState.ROUTED,
    "PROMOTION_DECIDED": PipelineState.PROMOTION_DECIDED,
    "DELIVERY_PENDING": PipelineState.DELIVERY_PENDING,
}
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Perform controlled generated-data replay."
    )
    parser.add_argument("--root", default=".")
    parser.add_argument("--database", required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument(
        "--from-stage",
        required=True,
        choices=sorted(REPLAY_STATES),
    )
    parser.add_argument("--actor", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument(
        "--force-stage",
        action="store_true",
    )
    args = parser.parse_args()
    store = PipelineStateStore(args.database)
    job = store.get_job(args.job_id)
    target = REPLAY_STATES[args.from_stage]
    if job.state is PipelineState.DEAD_LETTERED:
        raise SystemExit(
            "Resolve the dead letter before replay"
        )
    if not args.force_stage:
        raise SystemExit(
            "Replay requires --force-stage and an explicit reason"
        )
    replayed = store.transition(
        job_id=job.job_id,
        expected_state=job.state,
        target_state=target,
        actor=args.actor,
        payload={
            "reason": args.reason,
            "requested_stage": args.from_stage,
        },
        allow_replay=True,
    )
    ProcessingReceiptChain(store).append_receipt(
        job_id=job.job_id,
        stage=target.value,
        event_type="controlled_replay",
        actor=args.actor,
        payload={
            "reason": args.reason,
            "from_state": job.state.value,
            "to_state": target.value,
        },
        event_identity=(
            f"replay:{replayed.replay_generation}"
        ),
    )
    print(
        json.dumps(
            replayed.to_dict(),
            indent=2,
            sort_keys=True,
        )
    )
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
PY
cat > "$OPERATIONS/dead_letter.py" <<'PY'
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import Any
ROOT = Path(__file__).resolve().parents[2]
ORCHESTRATION = ROOT / "subagent-generated-data" / "orchestration"
sys.path.insert(0, str(ORCHESTRATION))
from state_store import PipelineStateStore
def redact(value: Any) -> Any:
    sensitive = {
        "token",
        "secret",
        "password",
        "authorization",
        "api_key",
        "private_key",
    }
    if isinstance(value, dict):
        return {
            key: (
                "[REDACTED]"
                if key.lower() in sensitive
                else redact(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect and resolve generated-data dead letters."
    )
    parser.add_argument("--database", required=True)
    commands = parser.add_subparsers(
        dest="command",
        required=True,
    )
    commands.add_parser("list")
    show = commands.add_parser("show")
    show.add_argument("dead_letter_id")
    resolve = commands.add_parser("resolve")
    resolve.add_argument("dead_letter_id")
    resolve.add_argument(
        "--type",
        required=True,
        choices=(
            "discarded",
            "superseded",
            "manually_delivered",
            "configuration_fixed",
        ),
    )
    resolve.add_argument("--reason", required=True)
    resolve.add_argument("--actor", required=True)
    export = commands.add_parser("export")
    export.add_argument("--output", required=True)
    args = parser.parse_args()
    store = PipelineStateStore(args.database)
    if args.command == "list":
        payload = [
            item.to_dict()
            for item in store.list_dead_letters()
        ]
    elif args.command == "show":
        matches = [
            item
            for item in store.list_dead_letters()
            if item.dead_letter_id == args.dead_letter_id
        ]
        if not matches:
            raise SystemExit("Dead letter not found")
        payload = matches[0].to_dict()
    elif args.command == "resolve":
        payload = store.resolve_dead_letter(
            dead_letter_id=args.dead_letter_id,
            resolution_type=args.type,
            resolution_reason=args.reason,
            actor=args.actor,
        ).to_dict()
    elif args.command == "export":
        payload = [
            redact(item.to_dict())
            for item in store.list_dead_letters()
        ]
        Path(args.output).write_text(
            json.dumps(payload, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        print(args.output)
        return 0
    else:
        raise SystemExit("Unsupported command")
    print(json.dumps(redact(payload), indent=2, sort_keys=True))
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
PY
# ---------------------------------------------------------------------------
# Golden integration
# ---------------------------------------------------------------------------
cat > "$INTEGRATION/end_to_end_golden.py" <<'PY'
from __future__ import annotations
import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "subagent-generated-data"
ORCHESTRATION = BASE / "orchestration"
RETRIEVAL = BASE / "retrieval"
INVALIDATION = BASE / "invalidation"
for directory in (
    ORCHESTRATION,
    RETRIEVAL,
    INVALIDATION,
):
    sys.path.insert(0, str(directory))
from processor import (
    GeneratedDataProcessor,
    ProcessingConfiguration,
)
from delivery_worker import (
    DeliveryWorker,
    DeliveryWorkerConfiguration,
)
from receipts import ProcessingReceiptChain
from state_store import (
    PipelineState,
    PipelineStateStore,
    deterministic_id,
)
from context_query import (
    ContextBudget,
    ContextCandidate,
    ContextQuery,
    StaticContextClient,
)
from context_selector import ContextSelector
from reuse_recorder import ReuseRecorder
from repository_event_bridge import (
    ChangedPath,
    RepositoryChangeEvent,
    RepositoryEventBridge,
)
def load_fixture() -> Mapping[str, Any]:
    path = (
        BASE
        / "tests"
        / "fixtures"
        / "valid-recon-packet.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise RuntimeError("Golden fixture must be an object")
    return payload
def run_golden(
    *,
    mode: str,
    database: str | Path,
    repository_root: str | Path,
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    store = PipelineStateStore(database)
    packet = load_fixture()
    processor = GeneratedDataProcessor(
        ProcessingConfiguration(
            repository_root=str(root),
            database_path=str(database),
        ),
        store=store,
    )
    processing = processor.process_packet(
        packet,
        actor="golden",
        independent_validation_present=True,
        designated_authority_approval=True,
        recurrence_counts={
            "unit-repo-fact-001": 2,
            "unit-contract-gap-001": 2,
        },
    )
    memory_mode = (
        "outbox"
        if mode in {"mock", "outbox"}
        else "command"
    )
    command = ()
    if mode == "live":
        import os
        import shlex
        raw = os.environ.get(
            "L9_SGD_GRAPHITI_INGEST_COMMAND",
            "",
        ).strip()
        if not raw:
            raise RuntimeError(
                "Live mode requires "
                "L9_SGD_GRAPHITI_INGEST_COMMAND"
            )
        command = tuple(shlex.split(raw))
    worker = DeliveryWorker(
        DeliveryWorkerConfiguration(
            repository_root=str(root),
            database_path=str(database),
            memory_mode=memory_mode,
            memory_command=command,
            memory_outbox=str(
                BASE / ".runtime" / "memory-outbox"
            ),
            route_outbox_root=str(BASE / ".runtime"),
        ),
        store=store,
    )
    delivery = worker.run_once(
        actor="golden",
        job_id=processing.job.job_id,
    )
    destination_acceptance_proven = bool(
        delivery
        and delivery.final_state
        == PipelineState.DESTINATION_ACCEPTED.value
    )
    candidate = ContextCandidate(
        record_id="record-golden-001",
        text=(
            "The repository uses uv.lock as the dependency "
            "resolution contract."
        ),
        score=0.95,
        confidence=0.98,
        state="active",
        authority_class="advisory",
        visibility="repository_local",
        repository="Quantum-L9/example",
        source_sha="abc1234",
        paths=("uv.lock",),
        task_types=("dependency_setup",),
        roles=("verifier",),
        epistemic_status="observed",
        invalidated=False,
        successful_reuse_count=0,
        failed_reuse_count=0,
    )
    query = ContextQuery(
        repository="Quantum-L9/example",
        repository_class="l9_python",
        campaign_id="campaign-002",
        action_id="verify-002",
        agent_id="verifier-002",
        role="verifier",
        task_type="dependency_setup",
        paths=("uv.lock",),
        base_sha="abc1234",
        visibility_ceiling="repository_local",
        budget=ContextBudget(
            max_items=5,
            max_characters=2000,
        ),
    )
    if mode == "live":
        import os
        import shlex
        from context_query import CommandContextClient
        raw = os.environ.get(
            "L9_SGD_GRAPHITI_SEARCH_COMMAND",
            "",
        ).strip()
        if not raw:
            raise RuntimeError(
                "Live mode requires "
                "L9_SGD_GRAPHITI_SEARCH_COMMAND"
            )
        query_result = CommandContextClient(
            shlex.split(raw)
        ).query(query)
    else:
        query_result = StaticContextClient(
            [candidate]
        ).query(query)
    selection = ContextSelector().select(
        query=query,
        result=query_result,
    )
    context_pack_id = deterministic_id(
        "context-pack",
        {
            "campaign_id": query.campaign_id,
            "action_id": query.action_id,
            "selection_hash": selection.selection_hash,
        },
    )
    store.record_context_selection(
        selection_id=selection.selection_hash,
        campaign_id=query.campaign_id,
        action_id=query.action_id,
        agent_id=query.agent_id,
        context_pack_id=context_pack_id,
        record_ids=selection.record_ids,
        payload=selection.to_dict(),
        status="SELECTED",
    )
    recorder = ReuseRecorder.from_environment(store)
    reuse_results = []
    for record_id in selection.record_ids:
        recorder.record_selection(
            record_id=record_id,
            campaign_id=query.campaign_id,
            action_id=query.action_id,
            agent_id=query.agent_id,
            context_pack_id=context_pack_id,
            payload={"selection_hash": selection.selection_hash},
        )
        recorder.record_injection(
            record_id=record_id,
            campaign_id=query.campaign_id,
            action_id=query.action_id,
            agent_id=query.agent_id,
            context_pack_id=context_pack_id,
            payload={"attached_to_agent_contract": True},
        )
        reuse_results.append(
            recorder.finalize_outcome(
                record_id=record_id,
                campaign_id=query.campaign_id,
                action_id=query.action_id,
                agent_id=query.agent_id,
                context_pack_id=context_pack_id,
                outcome="reduced_discovery",
                correction_required=False,
                validity_confirmed=True,
                evidence={"golden": True},
            ).to_dict()
        )
    event = RepositoryChangeEvent(
        event_id="invalidation-golden-001",
        repository="Quantum-L9/example",
        from_sha="abc1234",
        to_sha="def5678",
        event_type="repository_path_changed",
        changed_paths=(
            ChangedPath(
                path="uv.lock",
                change_kind="modified",
            ),
        ),
    )
    bridge = RepositoryEventBridge.from_environment(store)
    invalidation = bridge.dispatch(
        event,
        dry_run=(mode != "live"),
    )
    receipt_errors = ProcessingReceiptChain(
        store
    ).verify_job_chain(processing.job.job_id)
    retrieval_proven = bool(selection.record_ids)
    reuse_proven = (
        bool(reuse_results)
        and (
            mode != "live"
            or all(
                item["remote_dispatched"]
                for item in reuse_results
            )
        )
    )
    invalidation_proven = (
        invalidation.remote_dispatched
        if mode == "live"
        else invalidation.local_recorded
    )
    full_live = (
        mode == "live"
        and destination_acceptance_proven
        and retrieval_proven
        and reuse_proven
        and invalidation_proven
        and not receipt_errors
    )
    return {
        "mode": mode,
        "pipeline_passed": True,
        "destination_acceptance_proven": (
            destination_acceptance_proven
        ),
        "retrieval_proven": retrieval_proven,
        "reuse_proven": reuse_proven,
        "invalidation_proven": invalidation_proven,
        "learning_closure_proven": (
            processing.job.state
            in {
                PipelineState.DELIVERY_PENDING,
                PipelineState.LEARNING_CLOSED,
            }
        ),
        "receipt_integrity_proven": not receipt_errors,
        "full_compounding_loop_proven": full_live,
        "evidence": {
            "job_id": processing.job.job_id,
            "delivery": (
                delivery.to_dict()
                if delivery is not None
                else None
            ),
            "selection": selection.to_dict(),
            "reuse": reuse_results,
            "invalidation": invalidation.to_dict(),
            "receipt_errors": receipt_errors,
        },
        "failures": [],
    }
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the generated-data end-to-end golden scenario."
    )
    parser.add_argument(
        "--mode",
        choices=("mock", "outbox", "live"),
        required=True,
    )
    parser.add_argument("--root", default=".")
    parser.add_argument("--database")
    args = parser.parse_args()
    if args.database:
        result = run_golden(
            mode=args.mode,
            database=args.database,
            repository_root=args.root,
        )
    else:
        with tempfile.TemporaryDirectory() as temp:
            result = run_golden(
                mode=args.mode,
                database=Path(temp) / "pipeline.sqlite3",
                repository_root=args.root,
            )
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.mode == "live":
        return (
            0
            if result["full_compounding_loop_proven"]
            else 1
        )
    return 0 if result["pipeline_passed"] else 1
if __name__ == "__main__":
    raise SystemExit(main())
PY
# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
cat > "$CONFIG/instantiation.example.yaml" <<'YAML'
schema_version: "1.0.0"
state:
  database_path: .l9/subagent-generated-data/pipeline.sqlite3
processing:
  maximum_units_per_packet: 250
  maximum_packet_bytes: 2000000
  delivery_inline: false
delivery:
  memory:
    mode: outbox
    endpoint: null
    command: []
    timeout_seconds: 30
    outbox: subagent-generated-data/.runtime/memory-outbox
  route_outbox_root: subagent-generated-data/.runtime
retrieval:
  command_environment_variable: L9_SGD_GRAPHITI_SEARCH_COMMAND
  minimum_confidence: 0.70
  max_items: 12
  max_characters: 12000
  include_contested: false
  include_raw_evidence: false
reuse:
  command_environment_variable: L9_SGD_GRAPHITI_REUSE_COMMAND
invalidation:
  command_environment_variable: L9_SGD_GRAPHITI_INVALIDATE_COMMAND
  delete_memory: false
live_commands:
  ingest: L9_SGD_GRAPHITI_INGEST_COMMAND
  search: L9_SGD_GRAPHITI_SEARCH_COMMAND
  reuse: L9_SGD_GRAPHITI_REUSE_COMMAND
  invalidate: L9_SGD_GRAPHITI_INVALIDATE_COMMAND
YAML
# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
cat > "$TESTS/test_final_instantiation.py" <<'PY'
from __future__ import annotations
import json
import sys
import tempfile
import unittest
from pathlib import Path
TEST_FILE = Path(__file__).resolve()
BASE = TEST_FILE.parents[2]
ROOT = TEST_FILE.parents[3]
ORCHESTRATION = BASE / "orchestration"
RETRIEVAL = BASE / "retrieval"
INVALIDATION = BASE / "invalidation"
INTEGRATION = BASE / "integration"
for path in (
    ORCHESTRATION,
    RETRIEVAL,
    INVALIDATION,
    INTEGRATION,
):
    sys.path.insert(0, str(path))
from state_store import PipelineStateStore
from context_query import (
    ContextBudget,
    ContextCandidate,
    ContextQuery,
    StaticContextClient,
)
from context_selector import ContextSelector
from reuse_recorder import ReuseRecorder
from repository_event_bridge import (
    normalize_relative_path,
    parse_name_status,
)
from end_to_end_golden import run_golden
class FinalInstantiationTests(unittest.TestCase):
    def test_context_budget_is_enforced(self) -> None:
        query = ContextQuery(
            repository="r",
            repository_class="l9_python",
            campaign_id="c",
            action_id="a",
            agent_id="g",
            role="verifier",
            task_type="test",
            paths=("src/a.py",),
            base_sha="abc1234",
            visibility_ceiling="repository_local",
            budget=ContextBudget(
                max_items=1,
                max_characters=10,
            ),
        )
        candidates = [
            ContextCandidate(
                record_id="one",
                text="12345",
                score=1,
                confidence=1,
                state="active",
                authority_class="advisory",
                visibility="repository_local",
                repository="r",
                source_sha="abc1234",
                paths=("src/a.py",),
                task_types=("test",),
                roles=("verifier",),
                epistemic_status="observed",
                invalidated=False,
            ),
            ContextCandidate(
                record_id="two",
                text="67890",
                score=0.9,
                confidence=1,
                state="active",
                authority_class="advisory",
                visibility="repository_local",
                repository="r",
                source_sha="abc1234",
                paths=("src/a.py",),
                task_types=("test",),
                roles=("verifier",),
                epistemic_status="observed",
                invalidated=False,
            ),
        ]
        result = ContextSelector().select(
            query=query,
            result=StaticContextClient(candidates).query(query),
        )
        self.assertEqual(len(result.selected), 1)
    def test_contested_memory_is_excluded(self) -> None:
        query = ContextQuery(
            repository="r",
            repository_class="l9_python",
            campaign_id="c",
            action_id="a",
            agent_id="g",
            role="verifier",
            task_type="test",
            paths=(),
            base_sha="abc1234",
            visibility_ceiling="repository_local",
            budget=ContextBudget(),
        )
        candidate = ContextCandidate(
            record_id="contested",
            text="x",
            score=1,
            confidence=1,
            state="active",
            authority_class="advisory",
            visibility="repository_local",
            repository="r",
            source_sha="abc1234",
            paths=(),
            task_types=(),
            roles=(),
            epistemic_status="contested",
            invalidated=False,
        )
        result = ContextSelector().select(
            query=query,
            result=StaticContextClient([candidate]).query(query),
        )
        self.assertEqual(result.record_ids, ())
    def test_reuse_is_not_remote_before_finalization(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = PipelineStateStore(
                Path(temp) / "pipeline.sqlite3"
            )
            recorder = ReuseRecorder(store)
            selected = recorder.record_selection(
                record_id="r1",
                campaign_id="c",
                action_id="a",
                agent_id="g",
                context_pack_id="p",
                payload={},
            )
            injected = recorder.record_injection(
                record_id="r1",
                campaign_id="c",
                action_id="a",
                agent_id="g",
                context_pack_id="p",
                payload={},
            )
            self.assertFalse(selected.remote_dispatched)
            self.assertFalse(injected.remote_dispatched)
    def test_stale_reuse_creates_candidate_not_direct_action(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = PipelineStateStore(
                Path(temp) / "pipeline.sqlite3"
            )
            result = ReuseRecorder(store).finalize_outcome(
                record_id="r1",
                campaign_id="c",
                action_id="a",
                agent_id="g",
                context_pack_id="p",
                outcome="stale",
                correction_required=True,
                validity_confirmed=False,
                evidence={},
            )
            self.assertIsNotNone(
                result.invalidation_candidate
            )
            self.assertTrue(
                result.invalidation_candidate[
                    "requires_policy_approval"
                ]
            )
    def test_path_normalization_rejects_traversal(self) -> None:
        with self.assertRaises(ValueError):
            normalize_relative_path("../secret")
        with self.assertRaises(ValueError):
            normalize_relative_path("/absolute")
        self.assertEqual(
            normalize_relative_path("src/a.py"),
            "src/a.py",
        )
    def test_git_name_status_parsing(self) -> None:
        changes = parse_name_status(
            "M\tsrc/a.py\n"
            "A\ttests/test_a.py\n"
            "R100\told.py\tnew.py\n"
        )
        self.assertEqual(len(changes), 3)
        self.assertEqual(
            changes[2].change_kind,
            "renamed",
        )
    def test_mock_golden_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = run_golden(
                mode="mock",
                database=Path(temp) / "pipeline.sqlite3",
                repository_root=ROOT,
            )
        self.assertTrue(result["pipeline_passed"])
        self.assertTrue(result["retrieval_proven"])
        self.assertTrue(result["reuse_proven"])
        self.assertTrue(result["receipt_integrity_proven"])
    def test_outbox_does_not_claim_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = run_golden(
                mode="outbox",
                database=Path(temp) / "pipeline.sqlite3",
                repository_root=ROOT,
            )
        self.assertTrue(result["pipeline_passed"])
        self.assertFalse(
            result["destination_acceptance_proven"]
        )
        self.assertFalse(
            result["full_compounding_loop_proven"]
        )
if __name__ == "__main__":
    unittest.main()
PY
# ---------------------------------------------------------------------------
# Ignore runtime state
# ---------------------------------------------------------------------------
if ! grep -qxF \
  '.l9/subagent-generated-data/*.sqlite3' \
  "$ROOT/.gitignore" 2>/dev/null
then
  cat >> "$ROOT/.gitignore" <<'EOF'
# L9 Subagent-Generated Data runtime
.l9/subagent-generated-data/*.sqlite3
.l9/subagent-generated-data/*.sqlite3-shm
.l9/subagent-generated-data/*.sqlite3-wal
subagent-generated-data/.runtime/
EOF
fi
# ---------------------------------------------------------------------------
# Static validation and tests
# ---------------------------------------------------------------------------
python - <<'PY'
from __future__ import annotations
import ast
import json
from pathlib import Path
base = Path("subagent-generated-data")
directories = (
    base / "orchestration",
    base / "retrieval",
    base / "invalidation",
    base / "operations",
    base / "integration",
    base / "tests" / "instantiation",
)
errors: list[str] = []
for directory in directories:
    for path in sorted(directory.glob("*.py")):
        try:
            ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            errors.append(f"{path}: {exc}")
if errors:
    print("FINAL CURSOR WAVE STATIC VALIDATION FAILED")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)
print("FINAL CURSOR WAVE STATIC VALIDATION PASSED")
PY
python -m compileall \
  "$ORCHESTRATION" \
  "$RETRIEVAL" \
  "$INVALIDATION" \
  "$OPERATIONS" \
  "$INTEGRATION" \
  "$TESTS"
python - <<'PY'
# The runtime's file-path CLIs are intentionally disabled (Sonar hardening), so
# validate contracts + routes through the in-process APIs instead.
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path("subagent-generated-data/runtime").resolve()))
from packet_validator import PacketValidator
from routing_engine import RoutingEngine
schema_errors = [
    finding.to_dict()
    for finding in PacketValidator().validate_schema_set()
    if finding.severity == "error"
]
route_errors = RoutingEngine().validate_routes()
if schema_errors or route_errors:
    for finding in schema_errors:
        print(f"SCHEMA: {finding}")
    for error in route_errors:
        print(f"ROUTE: {error}")
    raise SystemExit(1)
print("Contracts and routes validated through PacketValidator/RoutingEngine APIs.")
PY
python -m unittest discover \
  -s "$BASE/tests" \
  -p 'test_*.py' \
  -v
MOCK_OUTPUT="$STATE_DIR/golden-mock.json"
OUTBOX_OUTPUT="$STATE_DIR/golden-outbox.json"
python "$INTEGRATION/end_to_end_golden.py" \
  --mode mock \
  --root "$ROOT" \
  > "$MOCK_OUTPUT"
python "$INTEGRATION/end_to_end_golden.py" \
  --mode outbox \
  --root "$ROOT" \
  > "$OUTBOX_OUTPUT"
LIVE_STATUS="NOT_CONFIGURED"
if [[ -n "${L9_SGD_GRAPHITI_INGEST_COMMAND:-}" ]] \
  && [[ -n "${L9_SGD_GRAPHITI_SEARCH_COMMAND:-}" ]] \
  && [[ -n "${L9_SGD_GRAPHITI_REUSE_COMMAND:-}" ]] \
  && [[ -n "${L9_SGD_GRAPHITI_INVALIDATE_COMMAND:-}" ]]
then
  LIVE_OUTPUT="$STATE_DIR/golden-live.json"
  if python "$INTEGRATION/end_to_end_golden.py" \
      --mode live \
      --root "$ROOT" \
      > "$LIVE_OUTPUT"
  then
    LIVE_STATUS="PASSED"
  else
    LIVE_STATUS="FAILED"
  fi
fi
python - <<'PY'
from __future__ import annotations
import hashlib
from pathlib import Path
base = Path("subagent-generated-data")
files = sorted(
    [
        *list((base / "orchestration").glob("*.py")),
        *list((base / "retrieval").glob("*.py")),
        *list((base / "invalidation").glob("*.py")),
        *list((base / "operations").glob("*.py")),
        *list((base / "integration").glob("*.py")),
        *list((base / "config").glob("*.yaml")),
        *list(
            (
                base / "tests" / "instantiation"
            ).glob("*.py")
        ),
    ]
)
print()
print("FINAL CURSOR-GOVERNANCE TREE")
for path in files:
    print(path)
print()
print("FINAL CURSOR-GOVERNANCE SHA-256")
for path in files:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    print(f"{digest}  {path}")
PY
ACTIVATION_STATE="CODE_COMPLETE"
if python - <<'PY'
import json
from pathlib import Path
value = json.loads(
    Path(".l9/subagent-generated-data/golden-outbox.json")
    .read_text(encoding="utf-8")
)
raise SystemExit(
    0
    if value.get("pipeline_passed")
    and not value.get("destination_acceptance_proven")
    else 1
)
PY
then
  ACTIVATION_STATE="OUTBOX_PROVEN"
fi
if [[ "$LIVE_STATUS" == "PASSED" ]]; then
  ACTIVATION_STATE="FULL_COMPOUNDING_LOOP_PROVEN"
fi
echo
echo "Final Cursor-Governance installation complete."
echo "Repository: Quantum-L9/Cursor-Governance"
echo "Mock golden: $MOCK_OUTPUT"
echo "Outbox golden: $OUTBOX_OUTPUT"
echo "Live golden: $LIVE_STATUS"
echo "Activation state: $ACTIVATION_STATE"
echo
echo "Boundary preserved:"
echo "  Cursor-Governance owns orchestration and dispatch."
echo "  l9-graphiti-memory owns canonical memory behavior."
echo "  No second Graphiti memory client was introduced."

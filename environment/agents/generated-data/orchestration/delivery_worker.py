from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from module_loader import PriorWaveModuleLoader
from receipts import ProcessingReceiptChain
from retry_policy import RetryClass, RetryPolicy
from state_store import (
    PipelineState,
    PipelineStateStore,
    ProcessingJob,
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
    memory_outbox: str = "environment/agents/generated-data/.runtime/memory-outbox"
    route_outbox_root: str = "environment/agents/generated-data/.runtime"
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
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            raise DeliveryError(
                f"Command failed with exit {completed.returncode}: {completed.stderr.strip()}"
            )
        try:
            response = json.loads(completed.stdout or "{}")
        except json.JSONDecodeError as exc:
            raise DeliveryError("Destination command returned invalid JSON") from exc
        if not isinstance(response, Mapping):
            raise DeliveryError("Destination command response must be an object")
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
        encoded = (
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
            ).encode("utf-8")
            + b"\n"
        )
        if target.exists():
            if target.read_bytes() != encoded:
                raise DeliveryError(f"Outbox collision for {delivery_id}")
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
                raise ValueError("memory_endpoint is required for http mode")
            transport = HttpJsonTransport(
                endpoint,
                bearer_token=os.environ.get("L9_GRAPHITI_MEMORY_TOKEN"),
                timeout_seconds=timeout_seconds,
            )
        elif mode == "command":
            if not command:
                raise ValueError("memory_command is required for command mode")
            transport = CommandTransport(
                list(command),
                timeout_seconds=timeout_seconds,
            )
        else:
            raise ValueError(f"Unsupported memory transport mode: {mode}")
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
        payload["destination_acceptance_proven"] = result.status not in {
            "enqueued",
            "already_enqueued",
        }
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
        self.store = store or PipelineStateStore(configuration.database_path)
        self.retry_policy = retry_policy or RetryPolicy()
        self.receipts = receipts or ProcessingReceiptChain(self.store)

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
                idempotency_key=str(delivery["idempotency_key"]),
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
                    raise DestinationRejected(f"Destination rejected delivery: {response}")
                else:
                    raise DeliveryError(f"Unsupported destination status: {status}")
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
                        next_attempt_at=str(decision.next_attempt_at),
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
                        event_identity=(f"retry:{unit_id}:{route}:{attempt_number}"),
                    )
                    return DeliveryExecutionResult(
                        job_id=job.job_id,
                        attempted=len(details) + 1,
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
                    attempted=len(details) + 1,
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
        destination_acceptance_proven = accepted == len(deliveries) and len(deliveries) > 0
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
                "destination_acceptance_proven": (destination_acceptance_proven),
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
                "destination_acceptance_proven": (destination_acceptance_proven),
            },
            event_identity=(f"delivery-batch:{current.version}"),
        )
        self.store.recalculate_campaign_state(current.campaign_id)
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
        return RouteOutboxTransport(self.configuration.route_outbox_root)

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
    parser = argparse.ArgumentParser(description="Process generated-data delivery jobs.")
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
    runtime_root = root / "environment" / "agents" / "generated-data" / ".runtime"
    configuration = DeliveryWorkerConfiguration(
        repository_root=str(root),
        database_path=(
            args.database or str(root / ".l9" / "subagent-generated-data" / "pipeline.sqlite3")
        ),
        memory_mode=args.memory_mode,
        memory_endpoint=args.memory_endpoint,
        memory_command=tuple(args.memory_command),
        memory_outbox=str(runtime_root / "memory-outbox"),
        route_outbox_root=str(runtime_root),
    )
    worker = DeliveryWorker(configuration)
    if args.job_id:
        result = worker.run_once(
            actor=args.actor,
            job_id=args.job_id,
        )
        payload: Any = result.to_dict() if result is not None else {"processed": False}
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

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
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
    deduplicated: int
    quarantined: int
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
            "deduplicated": self.deduplicated,
            "quarantined": self.quarantined,
            "rejected": self.rejected,
            "retried": self.retried,
            "dead_lettered": self.dead_lettered,
            "final_state": self.final_state,
            "details": [dict(item) for item in self.details],
        }


class JsonCommandTransport:
    """Delegate a delivery envelope to an existing JSON command."""

    def __init__(self, command: tuple[str, ...], timeout_seconds: int) -> None:
        if not command:
            raise ValueError("Command transport requires a command")
        self.command = command
        self.timeout_seconds = timeout_seconds

    def deliver(
        self,
        delivery: Mapping[str, Any],
        packet: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        payload = {"delivery": dict(delivery), "packet": dict(packet)}
        completed = subprocess.run(
            list(self.command),
            input=json.dumps(payload, sort_keys=True, separators=(",", ":")),
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        try:
            response = json.loads(completed.stdout or "{}")
        except json.JSONDecodeError as exc:
            raise DeliveryError("Destination command returned invalid JSON") from exc
        if not isinstance(response, Mapping):
            raise DeliveryError("Destination command response must be an object")
        status = str(response.get("status", "unknown")).lower()
        if completed.returncode != 0 and status not in {
            "rejected",
            "denied",
            "quarantined",
        }:
            raise DeliveryError(
                f"Command failed with exit {completed.returncode}: {completed.stderr.strip()}"
            )
        return {
            **dict(response),
            "exit_code": completed.returncode,
            "stderr": completed.stderr.strip(),
        }


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
        encoded = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + b"\n"
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
    """Reuse the governed Graphiti candidate adapter."""

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
        GraphitiMemoryAdapter = getattr(module, "GraphitiMemoryAdapter")
        FileOutboxTransport = getattr(module, "FileOutboxTransport")
        HttpJsonTransport = getattr(module, "HttpJsonTransport")
        CommandTransport = getattr(module, "CommandTransport")
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
            transport = CommandTransport(list(command), timeout_seconds=timeout_seconds)
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
        payload["destination_acceptance_proven"] = result.status in {
            "accepted",
            "deduplicated",
            "quarantined",
            "contested",
            "merged",
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
                stage=PipelineState.DELIVERY_PENDING.value,
            )
        ]
        if not deliveries:
            closed = self.store.transition(
                job_id=job.job_id,
                expected_state=PipelineState.DELIVERING,
                target_state=PipelineState.LEARNING_CLOSED,
                actor=actor,
                payload={"reason": "no deliveries"},
            )
            self.store.recalculate_campaign_state(closed.campaign_id)
            return DeliveryExecutionResult(
                job_id=job.job_id,
                attempted=0,
                accepted=0,
                enqueued=0,
                deduplicated=0,
                quarantined=0,
                rejected=0,
                retried=0,
                dead_lettered=0,
                final_state=PipelineState.LEARNING_CLOSED.value,
                details=(),
            )
        packet = self.store.load_packet(job.job_id)
        details: list[Mapping[str, Any]] = []
        accepted = 0
        enqueued = 0
        deduplicated = 0
        quarantined = 0
        rejected = 0
        for delivery in deliveries:
            route = str(delivery["route"])
            unit_id = str(delivery["unit_id"])
            attempt_number = self._next_attempt_number(job.job_id, unit_id, route)
            attempt = self.store.record_delivery_attempt(
                job_id=job.job_id,
                unit_id=unit_id,
                route=route,
                attempt_number=attempt_number,
                idempotency_key=str(delivery["idempotency_key"]),
            )
            try:
                response = self._transport_for(route).deliver(delivery, packet)
                status = str(response.get("status", "unknown")).lower()
                if status in {"accepted", "admitted", "merged"}:
                    accepted += 1
                elif status in {"duplicate", "deduplicated", "already_exists"}:
                    deduplicated += 1
                elif status in {"quarantined", "contested"}:
                    quarantined += 1
                elif status in {"enqueued", "already_enqueued", "submitted"}:
                    enqueued += 1
                elif status in {"rejected", "denied"}:
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
                                "record_id",
                                response.get(
                                    "memory_id",
                                    response.get("path", ""),
                                ),
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
                        stage=PipelineState.RETRY_WAIT.value,
                        event_type="delivery_retry_scheduled",
                        actor=actor,
                        payload=decision.to_dict(),
                        event_identity=f"retry:{unit_id}:{route}:{attempt_number}",
                    )
                    return DeliveryExecutionResult(
                        job_id=job.job_id,
                        attempted=len(details) + 1,
                        accepted=accepted,
                        enqueued=enqueued,
                        deduplicated=deduplicated,
                        quarantined=quarantined,
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
                    deduplicated=deduplicated,
                    quarantined=quarantined,
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
                "deduplicated": deduplicated,
                "quarantined": quarantined,
                "rejected": rejected,
            },
        )
        accepted_or_existing = accepted + deduplicated
        destination_acceptance_proven = accepted_or_existing == len(deliveries)
        if enqueued and not rejected:
            target = PipelineState.DESTINATION_SUBMITTED
        elif quarantined and not rejected and not enqueued:
            target = PipelineState.DESTINATION_DEFERRED
        elif destination_acceptance_proven:
            target = PipelineState.DESTINATION_ACCEPTED
        else:
            target = PipelineState.DESTINATION_REJECTED
        current = self.store.transition(
            job_id=job.job_id,
            expected_state=current.state,
            target_state=target,
            actor=actor,
            payload={
                "destination_acceptance_proven": destination_acceptance_proven,
                "accepted": accepted,
                "enqueued": enqueued,
                "deduplicated": deduplicated,
                "quarantined": quarantined,
                "rejected": rejected,
            },
        )
        self.receipts.append_receipt(
            job_id=job.job_id,
            stage=target.value,
            event_type=(
                "delivery_batch_submitted"
                if target is PipelineState.DESTINATION_SUBMITTED
                else "delivery_batch_deferred"
                if target is PipelineState.DESTINATION_DEFERRED
                else "delivery_batch_completed"
            ),
            actor=actor,
            payload={
                "accepted": accepted,
                "enqueued": enqueued,
                "deduplicated": deduplicated,
                "quarantined": quarantined,
                "rejected": rejected,
                "destination_acceptance_proven": destination_acceptance_proven,
            },
            event_identity=f"delivery-batch:{current.version}",
        )
        self.store.recalculate_campaign_state(current.campaign_id)
        return DeliveryExecutionResult(
            job_id=job.job_id,
            attempted=len(deliveries),
            accepted=accepted,
            enqueued=enqueued,
            deduplicated=deduplicated,
            quarantined=quarantined,
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
        # Fail-soft: the opportunistic pre-drain must not stop the deliveries
        # this call exists to run.
        # nosemgrep: l9.baseline.python.broad-except
        try:
            self.drain_memory_outbox(actor=actor, limit=min(5, max(0, limit)))
        except Exception:
            pass
        results: list[DeliveryExecutionResult] = []
        for _ in range(max(0, limit)):
            result = self.run_once(actor=actor)
            if result is None:
                break
            results.append(result)
        return results

    def _memory_outbox_dir(self) -> Path:
        configured = Path(self.configuration.memory_outbox)
        default_rel = "environment/agents/generated-data/.runtime/memory-outbox"
        if not str(self.configuration.memory_outbox) or str(configured) == default_rel:
            agents_root = Path(__file__).resolve().parents[2]
            if str(agents_root) not in sys.path:
                sys.path.insert(0, str(agents_root))
            try:
                from runtime_paths import memory_outbox_root

                return memory_outbox_root()
            except ImportError:
                return Path(self.configuration.repository_root) / default_rel
        return configured

    def _legacy_memory_outbox_dir(self) -> Path:
        return (
            Path(self.configuration.repository_root)
            / "environment"
            / "agents"
            / "generated-data"
            / ".runtime"
            / "memory-outbox"
        )

    def _adopt_legacy_outbox(self) -> list[Path]:
        canonical = self._memory_outbox_dir()
        canonical.mkdir(parents=True, exist_ok=True)
        legacy = self._legacy_memory_outbox_dir()
        adopted: list[Path] = []
        if not legacy.is_dir() or legacy.resolve() == canonical.resolve():
            return adopted
        for source in sorted(legacy.glob("memcand-*.json")):
            destination = canonical / source.name
            if destination.exists():
                continue
            destination.write_bytes(source.read_bytes())
            source.unlink()
            adopted.append(destination)
        return adopted

    def _packet_has_pending_candidates(self, packet_id: str, current: Path) -> bool:
        if not packet_id:
            return False
        outbox = self._memory_outbox_dir()
        for path in outbox.glob("memcand-*.json"):
            if path.resolve() == current.resolve():
                continue
            try:
                other = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if str((other.get("source") or {}).get("packet_id") or "") == packet_id:
                return True
        return False

    def _job_for_packet(self, packet_id: str) -> Any | None:
        if not packet_id:
            return None
        with self.store.connect() as connection:
            row = connection.execute(
                "SELECT job_id FROM processing_jobs WHERE packet_id = ? ORDER BY created_at",
                (packet_id,),
            ).fetchone()
        if row is None:
            return None
        return self.store.get_job(str(row["job_id"]))

    def _drain_transport(self) -> Any | None:
        loader = PriorWaveModuleLoader(self.configuration.repository_root)
        module = loader.load_adapter_module("graphiti_memory.py")
        HttpJsonTransport = getattr(module, "HttpJsonTransport")
        CommandTransport = getattr(module, "CommandTransport")
        command = list(self.configuration.memory_command)
        if self.configuration.memory_mode == "http" and self.configuration.memory_endpoint:
            return HttpJsonTransport(
                self.configuration.memory_endpoint,
                bearer_token=os.environ.get("L9_GRAPHITI_MEMORY_TOKEN"),
                timeout_seconds=self.configuration.timeout_seconds,
            )
        if command:
            return CommandTransport(command, timeout_seconds=self.configuration.timeout_seconds)
        if self.configuration.memory_mode == "command":
            script = (
                Path(self.configuration.repository_root)
                / "environment"
                / "agents"
                / "generated-data"
                / "adapters"
                / "ingest_memory_candidate.py"
            )
            if script.is_file():
                return CommandTransport(
                    [sys.executable, str(script)],
                    timeout_seconds=self.configuration.timeout_seconds,
                )
        return None

    def drain_memory_outbox(self, actor: str, limit: int = 20) -> list[dict[str, Any]]:
        """Deliver enqueued memory candidates. Never uses FileOutboxTransport."""
        from state_store import PipelineState

        self._adopt_legacy_outbox()
        outbox = self._memory_outbox_dir()
        results: list[dict[str, Any]] = []
        transport = self._drain_transport()
        files = sorted(outbox.glob("memcand-*.json"))[: max(0, limit)]
        for path in files:
            candidate = json.loads(path.read_text(encoding="utf-8"))
            packet_id = str((candidate.get("source") or {}).get("packet_id") or "")
            unit_id = str((candidate.get("knowledge") or {}).get("unit_id") or "")
            job = self._job_for_packet(packet_id)
            if job is None:
                results.append({"path": str(path), "status": "no_job", "packet_id": packet_id})
                continue
            if job.state is PipelineState.DESTINATION_ACCEPTED:
                path.unlink(missing_ok=True)
                results.append(
                    {
                        "path": str(path),
                        "status": "already_delivered",
                        "job_id": job.job_id,
                    }
                )
                continue
            if job.state is not PipelineState.DESTINATION_SUBMITTED:
                results.append(
                    {
                        "path": str(path),
                        "status": "skip",
                        "state": job.state.value,
                        "job_id": job.job_id,
                    }
                )
                continue
            snapshots = self.store.list_stage_snapshots(
                job_id=job.job_id,
                stage=PipelineState.DELIVERY_PENDING.value,
            )
            delivery = {}
            for item in snapshots:
                payload = item.get("payload") if isinstance(item, Mapping) else None
                if isinstance(payload, Mapping) and str(payload.get("unit_id")) == unit_id:
                    delivery = dict(payload)
                    break
            idempotency_key = str(
                delivery.get("idempotency_key") or candidate.get("candidate_id") or path.stem
            )
            attempt_number = self._next_attempt_number(job.job_id, unit_id or path.stem, "memory")
            attempt = self.store.record_delivery_attempt(
                job_id=job.job_id,
                unit_id=unit_id or path.stem,
                route="memory",
                attempt_number=attempt_number,
                idempotency_key=idempotency_key,
            )
            if transport is None:
                self.store.complete_delivery_attempt(
                    attempt_id=attempt.attempt_id,
                    status="FAILED",
                    error_class="unconfigured_transport",
                    error_message="drain has no Command or HTTP transport",
                )
                results.append(
                    {
                        "path": str(path),
                        "status": "unconfigured",
                        "job_id": job.job_id,
                        "state": PipelineState.DESTINATION_SUBMITTED.value,
                    }
                )
                continue
            try:
                response = transport.deliver(candidate)
                status = str(response.get("status", "unknown")).lower()
                if status in {"duplicate", "already_exists"}:
                    status = "deduplicated"
                if status not in {
                    "accepted",
                    "admitted",
                    "merged",
                    "deduplicated",
                    "rejected",
                    "denied",
                    "quarantined",
                }:
                    raise DeliveryError(f"Unsupported drain status: {status}")
                if status in {"rejected", "denied"}:
                    raise DestinationRejected(f"Destination rejected drain: {response}")
                self.store.complete_delivery_attempt(
                    attempt_id=attempt.attempt_id,
                    status="SUCCEEDED",
                    response_code=status,
                    response_payload=response,
                )
                self.store.record_delivery_receipt(
                    job_id=job.job_id,
                    unit_id=unit_id or path.stem,
                    route="memory",
                    destination_status=status,
                    destination_reference=str(
                        response.get(
                            "memory_id",
                            response.get("write_receipt_id", response.get("path", "")),
                        )
                    )
                    or None,
                    payload=response,
                )
                remaining = self._packet_has_pending_candidates(packet_id, path)
                target = (
                    PipelineState.DESTINATION_DEFERRED
                    if status == "quarantined"
                    else (
                        PipelineState.DESTINATION_SUBMITTED
                        if remaining
                        else PipelineState.DESTINATION_ACCEPTED
                    )
                )
                if target is not PipelineState.DESTINATION_SUBMITTED:
                    self.store.transition(
                        job_id=job.job_id,
                        expected_state=PipelineState.DESTINATION_SUBMITTED,
                        target_state=target,
                        actor=actor,
                        payload={"drain": True, "status": status},
                    )
                path.unlink()
                self.store.recalculate_campaign_state(job.campaign_id)
                results.append(
                    {
                        "path": str(path),
                        "status": status,
                        "job_id": job.job_id,
                        "state": target.value,
                    }
                )
            except DestinationRejected as exc:
                self.store.complete_delivery_attempt(
                    attempt_id=attempt.attempt_id,
                    status="FAILED",
                    error_class=RetryClass.PERMANENT_REJECTION.value,
                    error_message=str(exc),
                )
                self.store.transition(
                    job_id=job.job_id,
                    expected_state=PipelineState.DESTINATION_SUBMITTED,
                    target_state=PipelineState.DESTINATION_REJECTED,
                    actor=actor,
                    payload={"drain": True, "error": str(exc)},
                )
                path.unlink()
                self.store.recalculate_campaign_state(job.campaign_id)
                results.append({"path": str(path), "status": "rejected", "job_id": job.job_id})
            except Exception as exc:
                failure_class = self.retry_policy.classify_exception(exc)
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
                current = self.store.get_job(job.job_id)
                if decision.retry:
                    self.store.schedule_retry(
                        job_id=job.job_id,
                        expected_state=current.state,
                        actor=actor,
                        next_attempt_at=str(decision.next_attempt_at),
                        error_code=failure_class.value,
                        error_message=str(exc),
                        payload={"drain": True, "path": str(path)},
                    )
                    results.append(
                        {
                            "path": str(path),
                            "status": "retry",
                            "job_id": job.job_id,
                            "state": PipelineState.RETRY_WAIT.value,
                        }
                    )
                else:
                    self.store.dead_letter(
                        job_id=job.job_id,
                        expected_state=current.state,
                        actor=actor,
                        failure_class=failure_class.value,
                        reason=str(exc),
                        payload={"drain": True, "path": str(path)},
                        unit_id=unit_id or path.stem,
                        route="memory",
                    )
                    results.append(
                        {
                            "path": str(path),
                            "status": "dead_lettered",
                            "job_id": job.job_id,
                        }
                    )
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

    def _select_job(self, job_id: str | None) -> ProcessingJob | None:
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
                        AND (next_attempt_at IS NULL OR next_attempt_at <= ?)
                    )
                ORDER BY created_at
                LIMIT 1
                """,
                (utc_now_text(),),
            ).fetchone()
        return None if row is None else self.store.get_job(row["job_id"])

    def _next_attempt_number(self, job_id: str, unit_id: str, route: str) -> int:
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
    parser.add_argument("--memory-command", nargs="+", default=[])
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--drain", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    runtime_root = root / "environment" / "agents" / "generated-data" / ".runtime"
    agents_root = root / "environment" / "agents"
    if str(agents_root) not in sys.path:
        sys.path.insert(0, str(agents_root))
    try:
        from runtime_paths import generated_data_outbox_root, memory_outbox_root

        memory_outbox = str(memory_outbox_root())
        route_outbox = str(generated_data_outbox_root())
    except ImportError:
        memory_outbox = str(runtime_root / "memory-outbox")
        route_outbox = str(runtime_root)
    configuration = DeliveryWorkerConfiguration(
        repository_root=str(root),
        database_path=(
            args.database or str(root / ".l9" / "subagent-generated-data" / "pipeline.sqlite3")
        ),
        memory_mode=args.memory_mode,
        memory_endpoint=args.memory_endpoint,
        memory_command=tuple(args.memory_command),
        memory_outbox=memory_outbox,
        route_outbox_root=route_outbox,
    )
    worker = DeliveryWorker(configuration)
    if args.drain:
        payload = worker.drain_memory_outbox(actor=args.actor, limit=args.limit)
    elif args.job_id:
        result = worker.run_once(actor=args.actor, job_id=args.job_id)
        payload: Any = result.to_dict() if result is not None else {"processed": False}
    else:
        payload = [item.to_dict() for item in worker.run_batch(actor=args.actor, limit=args.limit)]
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

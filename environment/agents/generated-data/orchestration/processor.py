"""Persisted generated-data processing with resumable stage snapshots.

The processor owns validate -> harvest/classify -> route -> promotion -> delivery
queueing. The raw packet is committed by ``PipelineStateStore.create_job`` before
validation. Every lossy stage stores its complete output before advancing state,
so a retry resumes from durable data rather than silently treating an incomplete
job as finished.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from module_loader import PriorWaveModuleLoader
from receipts import ProcessingReceiptChain
from state_store import (
    PipelineState,
    PipelineStateStore,
    ProcessingJob,
    deterministic_id,
)


class ProcessingError(RuntimeError):
    """Raised when a packet cannot be processed safely."""


@dataclass(frozen=True)
class ProcessingConfiguration:
    repository_root: str
    database_path: str
    maximum_units_per_packet: int = 250
    maximum_packet_bytes: int = 2_000_000


@dataclass(frozen=True)
class ProcessingResult:
    job: ProcessingJob
    delivery_count: int
    promotions: tuple[Mapping[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "job": self.job.to_dict(),
            "delivery_count": self.delivery_count,
            "promotions": [dict(item) for item in self.promotions],
        }


class GeneratedDataProcessor:
    """Deterministic, persisted and resumable generated-data pipeline."""

    TERMINAL_STATES = {
        PipelineState.DELIVERY_PENDING,
        PipelineState.DESTINATION_SUBMITTED,
        PipelineState.DESTINATION_DEFERRED,
        PipelineState.DELIVERING,
        PipelineState.DELIVERED,
        PipelineState.DESTINATION_ACCEPTED,
        PipelineState.DESTINATION_REJECTED,
        PipelineState.RETRY_WAIT,
        PipelineState.DEAD_LETTERED,
        PipelineState.LEARNING_CLOSED,
    }

    def __init__(
        self,
        configuration: ProcessingConfiguration,
        *,
        store: PipelineStateStore | None = None,
    ) -> None:
        self.configuration = configuration
        self.store = store or PipelineStateStore(configuration.database_path)
        self.receipts = ProcessingReceiptChain(self.store)
        self.loader = PriorWaveModuleLoader(configuration.repository_root)

    @staticmethod
    def job_id_for_packet(packet: Mapping[str, Any]) -> str:
        identity = packet.get("identity")
        if not isinstance(identity, Mapping):
            raise ProcessingError("packet.identity must be an object")
        packet_id = str(packet.get("packet_id", "")).strip()
        if not packet_id:
            raise ProcessingError("packet.packet_id is required")
        campaign_id = str(identity.get("campaign_id") or "").strip()
        if not campaign_id:
            raise ProcessingError("packet.identity.campaign_id is required")
        return deterministic_id(
            "job",
            {
                "campaign_id": campaign_id,
                "action_id": identity.get("action_id"),
                "packet_id": packet_id,
                "base_sha": identity.get("base_sha"),
            },
        )

    def process_packet(
        self,
        packet: Mapping[str, Any],
        *,
        actor: str,
        independent_validation_present: bool = False,
        designated_authority_approval: bool = False,
        recurrence_counts: Mapping[str, int] | None = None,
    ) -> ProcessingResult:
        identity = packet.get("identity")
        if not isinstance(identity, Mapping):
            raise ProcessingError("packet.identity must be an object")
        packet_id = str(packet.get("packet_id", "")).strip()
        if not packet_id:
            raise ProcessingError("packet.packet_id is required")
        units = packet.get("generated_data_units", [])
        if isinstance(units, list) and len(units) > self.configuration.maximum_units_per_packet:
            raise ProcessingError("packet exceeds maximum_units_per_packet")
        packet_bytes = len(json.dumps(packet, separators=(",", ":"), default=str).encode("utf-8"))
        if packet_bytes > self.configuration.maximum_packet_bytes:
            raise ProcessingError(
                f"packet exceeds maximum_packet_bytes ({packet_bytes} > "
                f"{self.configuration.maximum_packet_bytes})"
            )

        campaign_id = str(identity["campaign_id"])
        job_id = self.job_id_for_packet(packet)
        self.store.create_job(
            job_id=job_id,
            campaign_id=campaign_id,
            graph_id=identity.get("graph_id"),
            packet_id=packet_id,
            packet=packet,
        )
        runtime = self._load_runtime()
        recurrence = dict(recurrence_counts or {})

        while True:
            job = self.store.get_job(job_id)
            if job.state is PipelineState.REJECTED:
                raise ProcessingError(f"packet {job_id} is rejected")
            if job.state in self.TERMINAL_STATES:
                return self._existing_result(job)

            if job.state is PipelineState.RECEIVED:
                self._validate(runtime, packet, job_id, actor)
                continue
            if job.state is PipelineState.VALIDATED:
                self._harvest(runtime, packet, job_id, actor)
                continue
            if job.state is PipelineState.HARVESTED:
                harvested = self._stage_payloads(job_id, PipelineState.HARVESTED)
                self._transition(
                    job_id,
                    PipelineState.HARVESTED,
                    PipelineState.CLASSIFIED,
                    actor,
                    payload={"classified": len(harvested)},
                )
                continue
            if job.state is PipelineState.CLASSIFIED:
                harvested = self._stage_payloads(job_id, PipelineState.HARVESTED)
                self._route(runtime, harvested, job_id, actor)
                continue
            if job.state is PipelineState.ROUTED:
                harvested = self._stage_payloads(job_id, PipelineState.HARVESTED)
                routing = self._stage_payloads(job_id, PipelineState.ROUTED)
                self._promote(
                    runtime,
                    harvested,
                    routing,
                    job_id,
                    actor,
                    independent_validation_present=independent_validation_present,
                    designated_authority_approval=designated_authority_approval,
                    recurrence_counts=recurrence,
                )
                continue
            if job.state is PipelineState.PROMOTION_DECIDED:
                harvested = self._stage_payloads(job_id, PipelineState.HARVESTED)
                routing = self._stage_payloads(job_id, PipelineState.ROUTED)
                promotions = self._stage_payloads(job_id, PipelineState.PROMOTION_DECIDED)
                delivery_count = self._queue_deliveries(
                    job_id=job_id,
                    packet_id=packet_id,
                    harvested_dicts=harvested,
                    routing_dicts=routing,
                    promotions=promotions,
                )
                target = (
                    PipelineState.DELIVERY_PENDING
                    if delivery_count
                    else PipelineState.LEARNING_CLOSED
                )
                self._transition(
                    job_id,
                    PipelineState.PROMOTION_DECIDED,
                    target,
                    actor,
                    payload={
                        "delivery_count": delivery_count,
                        "reason": (
                            "promoted deliveries queued"
                            if delivery_count
                            else "no promoted delivery; learning lifecycle closed"
                        ),
                    },
                )
                self.store.recalculate_campaign_state(campaign_id)
                return ProcessingResult(
                    job=self.store.get_job(job_id),
                    delivery_count=delivery_count,
                    promotions=tuple(promotions),
                )
            raise ProcessingError(f"unsupported processing state: {job.state.value}")

    def _existing_result(self, job: ProcessingJob) -> ProcessingResult:
        deliveries = self.store.list_stage_snapshots(
            job_id=job.job_id,
            stage=PipelineState.DELIVERY_PENDING.value,
        )
        promotions = self._stage_payloads(job.job_id, PipelineState.PROMOTION_DECIDED)
        return ProcessingResult(
            job=job,
            delivery_count=len(deliveries),
            promotions=tuple(promotions),
        )

    def _stage_payloads(self, job_id: str, stage: PipelineState) -> list[Mapping[str, Any]]:
        return [
            item["payload"]
            for item in self.store.list_stage_snapshots(job_id=job_id, stage=stage.value)
        ]

    def _load_runtime(self) -> dict[str, Any]:
        return {
            "PacketValidator": self.loader.load_runtime_module("packet_validator").PacketValidator,
            "SubagentDataHarvester": self.loader.load_runtime_module(
                "harvester"
            ).SubagentDataHarvester,
            "RoutingEngine": self.loader.load_runtime_module("routing_engine").RoutingEngine,
            "PromotionGate": self.loader.load_runtime_module("promotion_gate").PromotionGate,
        }

    def _validate(
        self,
        runtime: Mapping[str, Any],
        packet: Mapping[str, Any],
        job_id: str,
        actor: str,
    ) -> None:
        report = runtime["PacketValidator"]().validate(packet)
        if not report.valid:
            findings = [finding.to_dict() for finding in report.findings]
            self._transition(
                job_id,
                PipelineState.RECEIVED,
                PipelineState.REJECTED,
                actor,
                payload={"findings": findings},
            )
            raise ProcessingError(f"packet {job_id} failed validation")
        self._transition(
            job_id,
            PipelineState.RECEIVED,
            PipelineState.VALIDATED,
            actor,
            payload={"packet_hash": report.packet_hash},
        )

    def _harvest(
        self,
        runtime: Mapping[str, Any],
        packet: Mapping[str, Any],
        job_id: str,
        actor: str,
    ) -> None:
        result = runtime["SubagentDataHarvester"]().harvest(packet)
        harvested = [unit.to_dict() for unit in result.harvested_units]
        for unit in harvested:
            self.store.add_stage_snapshot(
                job_id=job_id,
                stage=PipelineState.HARVESTED.value,
                payload=unit,
            )
        self._transition(
            job_id,
            PipelineState.VALIDATED,
            PipelineState.HARVESTED,
            actor,
            payload={
                "harvested": len(harvested),
                "duplicates": len(result.duplicate_unit_ids),
                "rejected": len(result.rejected_units),
            },
        )

    def _route(
        self,
        runtime: Mapping[str, Any],
        harvested_dicts: list[Mapping[str, Any]],
        job_id: str,
        actor: str,
    ) -> None:
        decisions = runtime["RoutingEngine"]().route_many(harvested_dicts)
        routing_dicts = [decision.to_dict() for decision in decisions]
        for decision in routing_dicts:
            self.store.add_stage_snapshot(
                job_id=job_id,
                stage=PipelineState.ROUTED.value,
                payload=decision,
            )
        self._transition(
            job_id,
            PipelineState.CLASSIFIED,
            PipelineState.ROUTED,
            actor,
            payload={"decisions": len(routing_dicts)},
        )

    def _promote(
        self,
        runtime: Mapping[str, Any],
        harvested_dicts: list[Mapping[str, Any]],
        routing_dicts: list[Mapping[str, Any]],
        job_id: str,
        actor: str,
        *,
        independent_validation_present: bool,
        designated_authority_approval: bool,
        recurrence_counts: Mapping[str, int],
    ) -> None:
        results = runtime["PromotionGate"]().evaluate_many(
            harvested_units=harvested_dicts,
            routing_decisions=routing_dicts,
            independent_validation_present=independent_validation_present,
            designated_authority_approval=designated_authority_approval,
            recurrence_counts=recurrence_counts,
        )
        promotions = [result.to_dict() for result in results]
        for promotion in promotions:
            self.store.add_stage_snapshot(
                job_id=job_id,
                stage=PipelineState.PROMOTION_DECIDED.value,
                payload=promotion,
            )
        self._transition(
            job_id,
            PipelineState.ROUTED,
            PipelineState.PROMOTION_DECIDED,
            actor,
            payload={
                "promoted": sum(1 for item in promotions if item["decision"] == "promote"),
                "deferred": sum(1 for item in promotions if item["decision"] == "defer"),
                "retained": sum(1 for item in promotions if item["decision"] == "retain"),
                "rejected": sum(1 for item in promotions if item["decision"] == "reject"),
                "total": len(promotions),
            },
        )

    def _queue_deliveries(
        self,
        *,
        job_id: str,
        packet_id: str,
        harvested_dicts: list[Mapping[str, Any]],
        routing_dicts: list[Mapping[str, Any]],
        promotions: list[Mapping[str, Any]],
    ) -> int:
        harvested_by_id = {str(unit["unit_id"]): unit for unit in harvested_dicts}
        routing_by_key = {
            (str(decision["unit_id"]), str(decision["route"])): decision
            for decision in routing_dicts
        }
        delivery_count = 0
        for promotion in promotions:
            if promotion.get("decision") != "promote":
                continue
            unit_id = str(promotion["unit_id"])
            route = str(promotion["route"])
            routing_decision = routing_by_key.get((unit_id, route))
            harvested_unit = harvested_by_id.get(unit_id)
            if routing_decision is None or harvested_unit is None:
                raise ProcessingError(
                    f"promotion references missing route or harvested unit: {unit_id}/{route}"
                )
            delivery = {
                "delivery_id": deterministic_id(
                    "delivery",
                    {"job_id": job_id, "unit_id": unit_id, "route": route},
                ),
                "idempotency_key": deterministic_id(
                    "idem",
                    {
                        "job_id": job_id,
                        "unit_id": unit_id,
                        "route": route,
                        "packet_id": packet_id,
                    },
                ),
                "route": route,
                "unit_id": unit_id,
                "harvested_unit": harvested_unit,
                "routing_decision": routing_decision,
                "promotion_result": promotion,
            }
            self.store.add_stage_snapshot(
                job_id=job_id,
                stage=PipelineState.DELIVERY_PENDING.value,
                payload=delivery,
            )
            delivery_count += 1
        return delivery_count

    def _transition(
        self,
        job_id: str,
        expected: PipelineState,
        target: PipelineState,
        actor: str,
        payload: Mapping[str, Any] | None = None,
    ) -> None:
        job = self.store.transition(
            job_id=job_id,
            expected_state=expected,
            target_state=target,
            actor=actor,
            payload=dict(payload or {}),
        )
        self.receipts.append_receipt(
            job_id=job_id,
            stage=target.value,
            event_type="pipeline_stage",
            actor=actor,
            payload=dict(payload or {}),
            event_identity=f"stage:{target.value}:{job.replay_generation}",
        )

"""Persisted processing of one subagent data packet through the runtime pipeline.

Runs validate -> harvest -> classify -> route -> promotion-gate against the
Wave 1-3 runtime, persisting each stage as an explicit state transition and a
hash-chained receipt, then queues one delivery per promoted unit. Delivery
itself is performed asynchronously by the delivery worker; this processor stops
at DELIVERY_PENDING so dispatch stays a separate, independently retryable step.
"""

from __future__ import annotations

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
    """Deterministic, persisted execution of the generated-data pipeline."""

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

        campaign_id = str(identity["campaign_id"])
        job_id = deterministic_id(
            "job",
            {
                "campaign_id": campaign_id,
                "action_id": identity.get("action_id"),
                "packet_id": packet_id,
                "base_sha": identity.get("base_sha"),
            },
        )
        self.store.create_job(
            job_id=job_id,
            campaign_id=campaign_id,
            graph_id=identity.get("graph_id"),
            packet_id=packet_id,
            packet=packet,
        )

        runtime = self._load_runtime()
        self._validate(runtime, packet, job_id, actor)
        harvested = self._harvest(runtime, packet, job_id, actor)
        harvested_dicts = [unit.to_dict() for unit in harvested]
        self._transition(job_id, PipelineState.HARVESTED, PipelineState.CLASSIFIED, actor)
        routing_dicts = self._route(runtime, harvested_dicts, job_id, actor)
        promotions = self._promote(
            runtime,
            harvested_dicts,
            routing_dicts,
            job_id,
            actor,
            independent_validation_present=independent_validation_present,
            designated_authority_approval=designated_authority_approval,
            recurrence_counts=dict(recurrence_counts or {}),
        )
        delivery_count = self._queue_deliveries(
            job_id=job_id,
            packet_id=packet_id,
            harvested_dicts=harvested_dicts,
            routing_dicts=routing_dicts,
            promotions=promotions,
        )
        self._transition(
            job_id,
            PipelineState.PROMOTION_DECIDED,
            PipelineState.DELIVERY_PENDING,
            actor,
            payload={"delivery_count": delivery_count},
        )
        self.store.recalculate_campaign_state(campaign_id)
        return ProcessingResult(
            job=self.store.get_job(job_id),
            delivery_count=delivery_count,
            promotions=tuple(promotions),
        )

    # ---- pipeline stages -------------------------------------------------
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
            self._transition(
                job_id,
                PipelineState.RECEIVED,
                PipelineState.REJECTED,
                actor,
                payload={"findings": [finding.to_dict() for finding in report.findings]},
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
    ) -> list[Any]:
        result = runtime["SubagentDataHarvester"]().harvest(packet)
        self._transition(
            job_id,
            PipelineState.VALIDATED,
            PipelineState.HARVESTED,
            actor,
            payload={"harvested": len(result.harvested_units)},
        )
        return list(result.harvested_units)

    def _route(
        self,
        runtime: Mapping[str, Any],
        harvested_dicts: list[Mapping[str, Any]],
        job_id: str,
        actor: str,
    ) -> list[Mapping[str, Any]]:
        engine = runtime["RoutingEngine"]()
        decisions = engine.route_many(harvested_dicts)
        routing_dicts = [decision.to_dict() for decision in decisions]
        self._transition(
            job_id,
            PipelineState.CLASSIFIED,
            PipelineState.ROUTED,
            actor,
            payload={"decisions": len(routing_dicts)},
        )
        return routing_dicts

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
    ) -> list[Mapping[str, Any]]:
        gate = runtime["PromotionGate"]()
        results = gate.evaluate_many(
            harvested_units=harvested_dicts,
            routing_decisions=routing_dicts,
            independent_validation_present=independent_validation_present,
            designated_authority_approval=designated_authority_approval,
            recurrence_counts=recurrence_counts,
        )
        promotions = [result.to_dict() for result in results]
        self._transition(
            job_id,
            PipelineState.ROUTED,
            PipelineState.PROMOTION_DECIDED,
            actor,
            payload={
                "promoted": sum(1 for item in promotions if item["decision"] == "promote"),
                "total": len(promotions),
            },
        )
        return promotions

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
                continue
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

    # ---- helpers ---------------------------------------------------------
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

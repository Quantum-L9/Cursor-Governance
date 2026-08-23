from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
ADAPTER = ROOT / "environment/agents/generated-data/adapters/graphiti_memory.py"
ORCHESTRATION = ROOT / "environment/agents/generated-data/orchestration"
if str(ORCHESTRATION) not in sys.path:
    sys.path.insert(0, str(ORCHESTRATION))
from delivery_worker import DeliveryWorker, DeliveryWorkerConfiguration
from state_store import PipelineState, PipelineStateStore


def load_adapter():
    spec = importlib.util.spec_from_file_location("sgd_graphiti_adapter", ADAPTER)
    if spec is None or spec.loader is None:
        raise RuntimeError(ADAPTER)
    module = importlib.util.module_from_spec(spec)
    # Register before executing: the adapter declares @dataclass types, and
    # dataclasses resolves annotations through sys.modules[cls.__module__].
    # Executing an unregistered module makes that lookup return None.
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(spec.name, None)
        raise
    return module


class StaticTransport:
    def __init__(self, response: dict[str, Any]) -> None:
        self.response = response

    def deliver(self, candidate):
        return dict(self.response)


class StaticDeliveryTransport:
    def __init__(self, response: dict[str, Any]) -> None:
        self.response = response

    def deliver(self, delivery, packet):
        return dict(self.response)


class MemoryDeliveryProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_adapter()

    def _inputs(self):
        unit = {
            "unit_id": "unit-1",
            "statement_hash": "a" * 64,
            "original_unit": {
                "statement": "Stable knowledge.",
                "primary_class": "repository_fact",
                "epistemic_status": "observed",
                "scope": {"paths": ["src"]},
                "confidence": 1.0,
                "freshness": {
                    "observed_at": "2026-08-23T12:00:00Z",
                    "base_sha": "b" * 40,
                    "expires_at": None,
                },
                "expected_reuse": {"cross_task": True},
                "invalidation_conditions": [
                    {"condition_type": "relevant_path_changed", "selector": "src"}
                ],
                "source_evidence": [{"source_id": "src-1", "source_type": "repository_path"}],
                "visibility": "repository_local",
            },
        }
        routing = {
            "decision_id": "route-1",
            "unit_id": "unit-1",
            "route": "memory",
            "status": "eligible",
        }
        promotion = {
            "promotion_id": "promotion-1",
            "unit_id": "unit-1",
            "route": "memory",
            "decision": "promote",
            "risk_class": "medium",
        }
        packet = {
            "packet_id": "packet-1",
            "generated_at": "2026-08-23T12:00:00Z",
            "identity": {
                "campaign_id": "campaign-1",
                "graph_id": "graph-1",
                "action_id": "action-1",
                "agent_id": "agent-1",
                "role": "recon",
                "lease_id": "lease-1",
                "repository": "Quantum-L9/example",
                "repository_class": "l9_python",
                "base_sha": "b" * 40,
            },
            "primary_result": {"artifact_id": "artifact-1"},
            "provenance": {"generated_at": "2026-08-23T12:00:00Z"},
        }
        return unit, routing, promotion, packet

    def test_candidate_is_byte_stable_across_recompile(self) -> None:
        adapter = self.module.GraphitiMemoryAdapter(StaticTransport({"status": "admitted"}))
        args = self._inputs()
        first = adapter.compile_candidate(
            harvested_unit=args[0],
            routing_decision=args[1],
            promotion_result=args[2],
            packet=args[3],
        )
        second = adapter.compile_candidate(
            harvested_unit=args[0],
            routing_decision=args[1],
            promotion_result=args[2],
            packet=args[3],
        )
        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(first.candidate_id, second.candidate_id)

    def test_downstream_statuses_are_normalized_truthfully(self) -> None:
        args = self._inputs()
        cases = {
            "admitted": "accepted",
            "duplicate": "deduplicated",
            "quarantined": "quarantined",
            "rejected": "rejected",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                adapter = self.module.GraphitiMemoryAdapter(
                    StaticTransport({"status": raw, "record_id": "record-1"})
                )
                candidate = adapter.compile_candidate(
                    harvested_unit=args[0],
                    routing_decision=args[1],
                    promotion_result=args[2],
                    packet=args[3],
                )
                result = adapter.deliver(candidate)
                self.assertEqual(result.status, expected)
                self.assertEqual(result.response["destination_status"], raw)

    def _worker_result(self, response: dict[str, Any]):
        with tempfile.TemporaryDirectory() as temp:
            database = Path(temp) / "pipeline.sqlite3"
            store = PipelineStateStore(database)
            job = store.create_job(
                job_id="job-1",
                campaign_id="campaign-1",
                graph_id="graph-1",
                packet_id="packet-1",
                packet={"packet_id": "packet-1"},
                state=PipelineState.DELIVERY_PENDING,
            )
            store.add_stage_snapshot(
                job_id=job.job_id,
                stage=PipelineState.DELIVERY_PENDING.value,
                payload={
                    "delivery_id": "delivery-1",
                    "idempotency_key": "idempotency-1",
                    "route": "memory",
                    "unit_id": "unit-1",
                    "harvested_unit": {},
                    "routing_decision": {},
                    "promotion_result": {},
                },
            )
            worker = DeliveryWorker(
                DeliveryWorkerConfiguration(
                    repository_root=str(ROOT),
                    database_path=str(database),
                ),
                store=store,
            )
            worker._transport_for = lambda route: StaticDeliveryTransport(response)
            result = worker.run_once(actor="test", job_id=job.job_id)
            self.assertIsNotNone(result)
            return result

    def test_outbox_submission_is_not_reported_as_acceptance(self) -> None:
        result = self._worker_result({"status": "enqueued", "path": "outbox/item.json"})
        self.assertEqual(result.final_state, PipelineState.DESTINATION_SUBMITTED.value)
        self.assertEqual(result.enqueued, 1)
        self.assertEqual(result.accepted, 0)

    def test_quarantine_is_deferred_not_accepted(self) -> None:
        result = self._worker_result({"status": "quarantined", "record_id": "record-1"})
        self.assertEqual(result.final_state, PipelineState.DESTINATION_DEFERRED.value)
        self.assertEqual(result.quarantined, 1)
        self.assertEqual(result.accepted, 0)

    def test_admitted_is_accepted_after_protocol_normalization(self) -> None:
        result = self._worker_result({"status": "admitted", "record_id": "record-1"})
        self.assertEqual(result.final_state, PipelineState.DESTINATION_ACCEPTED.value)
        self.assertEqual(result.accepted, 1)


if __name__ == "__main__":
    unittest.main()

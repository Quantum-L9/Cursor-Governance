from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shlex
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))


def _load_ingress_receipts():
    """Load this directory's `receipts.py` under a name only it can own.

    `generated-data` contains a hyphen, so it cannot be a Python package and
    these modules are imported by bare name off a flat `sys.path`. Two different
    modules are named `receipts` — this one and `orchestration/receipts.py` —
    so `sys.modules["receipts"]` belongs to whichever loads first. That was
    harmless only while ingress stopped at CAPTURED; now that accepted ingress
    invokes the orchestration processor, both live in one process and a bare
    `import receipts` here silently wins or loses the race. Six modules import
    the orchestration one by bare name, so ingress takes the unique key.
    """
    spec = importlib.util.spec_from_file_location(
        "generated_data_ingress_receipts", _HERE / "receipts.py"
    )
    if spec is None or spec.loader is None:  # pragma: no cover - packaging error
        raise ImportError("cannot load generated-data ingress receipts module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ingress_receipts = _load_ingress_receipts()

import security_gate  # noqa: E402

_REPO = _HERE.parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from environment.agents.runtime_paths import (  # noqa: E402
    generated_data_database,
    generated_data_outbox_root,
)

_ORCHESTRATION = _HERE.parent / "orchestration"


def _load_pipeline():
    if str(_ORCHESTRATION) not in sys.path:
        sys.path.insert(0, str(_ORCHESTRATION))
    from delivery_worker import (  # type: ignore[import-not-found]
        DeliveryWorker,
        DeliveryWorkerConfiguration,
    )
    from processor import (  # type: ignore[import-not-found]
        GeneratedDataProcessor,
        ProcessingConfiguration,
    )
    from state_store import PipelineStateStore  # type: ignore[import-not-found]

    return (
        GeneratedDataProcessor,
        ProcessingConfiguration,
        PipelineStateStore,
        DeliveryWorker,
        DeliveryWorkerConfiguration,
    )


def _canonical_digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _delivery_configuration(
    *,
    repository_root: Path,
    database_path: Path,
):
    raw_command = os.environ.get("L9_SGD_GRAPHITI_INGEST_COMMAND", "").strip()
    endpoint = os.environ.get("L9_SGD_GRAPHITI_INGEST_ENDPOINT", "").strip()
    if raw_command:
        return {
            "memory_mode": "command",
            "memory_command": tuple(shlex.split(raw_command)),
            "memory_endpoint": None,
        }
    if endpoint:
        return {
            "memory_mode": "http",
            "memory_command": (),
            "memory_endpoint": endpoint,
        }
    # A missing live transport does not mean "do nothing". Submit to the
    # canonical durable outbox and report DESTINATION_SUBMITTED without
    # pretending the downstream memory service accepted or persisted it.
    return {
        "memory_mode": "outbox",
        "memory_command": (),
        "memory_endpoint": None,
    }


def _run_delivery_if_configured(
    *,
    repository_root: Path,
    database_path: Path,
    job_id: str,
    actor: str,
) -> dict[str, Any] | None:
    configured = _delivery_configuration(
        repository_root=repository_root,
        database_path=database_path,
    )
    (
        _processor,
        _configuration,
        PipelineStateStore,
        DeliveryWorker,
        DeliveryWorkerConfiguration,
    ) = _load_pipeline()
    worker = DeliveryWorker(
        DeliveryWorkerConfiguration(
            repository_root=str(repository_root),
            database_path=str(database_path),
            memory_mode=configured["memory_mode"],
            memory_endpoint=configured["memory_endpoint"],
            memory_command=configured["memory_command"],
            memory_outbox=str(generated_data_outbox_root() / "memory"),
            route_outbox_root=str(generated_data_outbox_root()),
        ),
        store=PipelineStateStore(database_path),
    )
    result = worker.run_once(actor=actor, job_id=job_id)
    return result.to_dict() if result is not None else None


def ingest_packet(
    *,
    generated_data_packet: dict[str, Any] | None,
    source_receipt_digest: str,
    source_kind: str,
    actor: str,
    repository_root: str | Path | None = None,
    database_path: str | Path | None = None,
    independent_validation_present: bool = False,
    designated_authority_approval: bool = False,
    recurrence_counts: Mapping[str, int] | None = None,
    deliver_when_configured: bool = True,
) -> dict[str, Any]:
    """Durably capture and process a canonical generated-data packet.

    Raw packet evidence is written before validation. ``CAPTURED`` describes
    durable ingress only; ``processing_status`` reports the actual downstream
    state and never turns enqueueing into acceptance.
    """

    if not generated_data_packet:
        return ingress_receipts.write_ingress(
            {
                "acceptance_receipt_digest": source_receipt_digest,
                "source_kind": source_kind,
                "outcome": "NO_REUSABLE_DATA",
                "reason": "no generated-data packet",
                "processor_job_id": None,
                "processing_status": "NOT_STARTED",
            }
        )

    packet_digest = _canonical_digest(generated_data_packet)
    packet_path = ingress_receipts.write_packet_evidence(
        generated_data_packet,
        packet_digest,
    )
    decision = security_gate.preflight(generated_data_packet)
    if not decision["safe"]:
        ingress_receipts.quarantine_meta(
            {
                "packet_digest": packet_digest,
                "packet_evidence_path": str(packet_path),
                "classification": decision["classification"],
                "finding_types": decision["finding_types"],
                "acceptance_receipt_digest": source_receipt_digest,
                "source_kind": source_kind,
            }
        )
        return ingress_receipts.write_ingress(
            {
                "acceptance_receipt_digest": source_receipt_digest,
                "source_kind": source_kind,
                "outcome": "QUARANTINED",
                "reason": decision["classification"],
                "processor_job_id": None,
                "processing_status": "NOT_STARTED",
                "packet_digest": packet_digest,
                "packet_evidence_path": str(packet_path),
            }
        )

    root = Path(repository_root or _REPO).resolve()
    database = Path(database_path or generated_data_database()).resolve()
    (
        GeneratedDataProcessor,
        ProcessingConfiguration,
        PipelineStateStore,
        _DeliveryWorker,
        _DeliveryWorkerConfiguration,
    ) = _load_pipeline()
    processor = GeneratedDataProcessor(
        ProcessingConfiguration(
            repository_root=str(root),
            database_path=str(database),
        )
    )
    try:
        job_id = processor.job_id_for_packet(generated_data_packet)
    except Exception as exc:  # noqa: BLE001 - ingress answers with a receipt, never a raise
        # A packet the processor cannot even identify is not CAPTURED. Ingress is
        # a boundary: every path returns a receipt so the caller's evidence chain
        # stays intact and readiness can see the explicit failure.
        return ingress_receipts.write_ingress(
            {
                "acceptance_receipt_digest": source_receipt_digest,
                "source_kind": source_kind,
                "outcome": "FAILED",
                "reason": f"packet is not processable: {exc}",
                "processor_job_id": None,
                "processing_status": "FAILED",
                "packet_digest": packet_digest,
                "packet_evidence_path": str(packet_path),
                "database_path": str(database),
            }
        )
    pending = ingress_receipts.write_ingress(
        {
            "acceptance_receipt_digest": source_receipt_digest,
            "source_kind": source_kind,
            "outcome": "CAPTURED",
            "reason": "raw packet persisted; processing started",
            "processor_job_id": job_id,
            "processing_status": "PENDING",
            "packet_digest": packet_digest,
            "packet_evidence_path": str(packet_path),
            "database_path": str(database),
        }
    )
    try:
        processing = processor.process_packet(
            generated_data_packet,
            actor=actor,
            independent_validation_present=independent_validation_present,
            designated_authority_approval=designated_authority_approval,
            recurrence_counts=dict(recurrence_counts or {}),
        )
        delivery = None
        if deliver_when_configured and processing.job.state.value == "DELIVERY_PENDING":
            delivery = _run_delivery_if_configured(
                repository_root=root,
                database_path=database,
                job_id=processing.job.job_id,
                actor=actor,
            )
        final_job = PipelineStateStore(database).get_job(processing.job.job_id)
        return ingress_receipts.write_ingress(
            {
                **{
                    key: value
                    for key, value in pending.items()
                    if key not in {"schema", "observed_at", "receipt_digest"}
                },
                "outcome": "CAPTURED",
                "reason": "packet processed through canonical generated-data pipeline",
                "processor_job_id": final_job.job_id,
                "processing_status": final_job.state.value,
                "delivery_count": processing.delivery_count,
                "delivery": delivery,
            }
        )
    except Exception as exc:
        store = PipelineStateStore(database)
        try:
            job = store.get_job(job_id)
            state = job.state.value
        except Exception:
            state = "FAILED"
        outcome = "REJECTED" if state == "REJECTED" else "FAILED"
        return ingress_receipts.write_ingress(
            {
                **{
                    key: value
                    for key, value in pending.items()
                    if key not in {"schema", "observed_at", "receipt_digest"}
                },
                "outcome": outcome,
                "reason": str(exc),
                "processor_job_id": job_id,
                "processing_status": state if state != "FAILED" else "FAILED",
                "processing_error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                },
            }
        )


#: Ingress states from which no further work will happen on its own. Anything
#: else describes a run still in flight, which a repeat call may resume.
_UNSETTLED_PROCESSING = frozenset({"PENDING", "UNKNOWN"})


def _is_settled(receipt: Mapping[str, Any]) -> bool:
    """True when a recorded ingress receipt is a final answer for its input."""
    if str(receipt.get("outcome") or "") != "CAPTURED":
        # NO_REUSABLE_DATA, QUARANTINED, REJECTED and FAILED are all terminal.
        return True
    return str(receipt.get("processing_status") or "UNKNOWN") not in _UNSETTLED_PROCESSING


def ingest_accepted_result(
    *,
    accepted_result: dict[str, Any],
    generated_data_packet: dict[str, Any] | None,
    acceptance_receipt: dict[str, Any],
    actor: str = "result-gateway",
    repository_root: str | Path | None = None,
    database_path: str | Path | None = None,
    independent_validation_present: bool = False,
    designated_authority_approval: bool = False,
    recurrence_counts: Mapping[str, int] | None = None,
    deliver_when_configured: bool = True,
) -> dict[str, Any]:
    del accepted_result
    if acceptance_receipt.get("status") != "ACCEPTED":
        return ingress_receipts.write_ingress(
            {
                "acceptance_receipt_digest": acceptance_receipt.get("receipt_digest") or "none",
                "source_kind": "accepted_subagent_result",
                "outcome": "REJECTED",
                "reason": "result not accepted",
                "processor_job_id": None,
                "processing_status": "NOT_STARTED",
            }
        )
    acceptance_digest = str(acceptance_receipt["receipt_digest"])
    existing = ingress_receipts.load_ingress(acceptance_digest)
    if existing is not None and _is_settled(existing):
        # Re-ingesting one accepted result is a no-op that returns the receipt
        # already on record. Without this the pipeline re-runs and writes a
        # second receipt whose digest differs only by `observed_at`, so the
        # same input yields two identities. A non-settled receipt is not
        # returned: a run that stopped mid-pipeline must be allowed to finish
        # rather than being certified from its own PENDING record.
        return existing
    return ingest_packet(
        generated_data_packet=generated_data_packet,
        source_receipt_digest=acceptance_digest,
        source_kind="accepted_subagent_result",
        actor=actor,
        repository_root=repository_root,
        database_path=database_path,
        independent_validation_present=independent_validation_present,
        designated_authority_approval=designated_authority_approval,
        recurrence_counts=recurrence_counts,
        deliver_when_configured=deliver_when_configured,
    )


def ingest(*args, **kwargs):
    return ingest_accepted_result(*args, **kwargs)

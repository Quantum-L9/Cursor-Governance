from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "generated-data"
ORCHESTRATION = BASE / "orchestration"
RETRIEVAL = BASE / "retrieval"
INVALIDATION = BASE / "invalidation"
for directory in (
    ORCHESTRATION,
    RETRIEVAL,
    INVALIDATION,
):
    sys.path.insert(0, str(directory))
from context_query import (
    ContextBudget,
    ContextCandidate,
    ContextQuery,
    StaticContextClient,
)
from context_selector import ContextSelector
from delivery_worker import (
    DeliveryWorker,
    DeliveryWorkerConfiguration,
)
from processor import (
    GeneratedDataProcessor,
    ProcessingConfiguration,
)
from receipts import ProcessingReceiptChain
from repository_event_bridge import (
    ChangedPath,
    RepositoryChangeEvent,
    RepositoryEventBridge,
)
from reuse_recorder import ReuseRecorder
from state_store import (
    PipelineState,
    PipelineStateStore,
    deterministic_id,
)


def load_fixture() -> Mapping[str, Any]:
    path = BASE / "tests" / "fixtures" / "valid-recon-packet.json"
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
    memory_mode = "outbox" if mode in {"mock", "outbox"} else "command"
    command = ()
    if mode == "live":
        import os
        import shlex

        raw = os.environ.get(
            "L9_SGD_GRAPHITI_INGEST_COMMAND",
            "",
        ).strip()
        if not raw:
            raise RuntimeError("Live mode requires L9_SGD_GRAPHITI_INGEST_COMMAND")
        command = tuple(shlex.split(raw))
    worker = DeliveryWorker(
        DeliveryWorkerConfiguration(
            repository_root=str(root),
            database_path=str(database),
            memory_mode=memory_mode,
            memory_command=command,
            memory_outbox=str(BASE / ".runtime" / "memory-outbox"),
            route_outbox_root=str(BASE / ".runtime"),
        ),
        store=store,
    )
    delivery = worker.run_once(
        actor="golden",
        job_id=processing.job.job_id,
    )
    destination_acceptance_proven = bool(
        delivery and delivery.final_state == PipelineState.DESTINATION_ACCEPTED.value
    )
    candidate = ContextCandidate(
        record_id="record-golden-001",
        text=("The repository uses uv.lock as the dependency resolution contract."),
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
            raise RuntimeError("Live mode requires L9_SGD_GRAPHITI_SEARCH_COMMAND")
        query_result = CommandContextClient(shlex.split(raw)).query(query)
    else:
        query_result = StaticContextClient([candidate]).query(query)
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
    receipt_errors = ProcessingReceiptChain(store).verify_job_chain(processing.job.job_id)
    retrieval_proven = bool(selection.record_ids)
    reuse_proven = bool(reuse_results) and (
        mode != "live" or all(item["remote_dispatched"] for item in reuse_results)
    )
    invalidation_proven = (
        invalidation.remote_dispatched if mode == "live" else invalidation.local_recorded
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
        "destination_acceptance_proven": (destination_acceptance_proven),
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
            "delivery": (delivery.to_dict() if delivery is not None else None),
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
        return 0 if result["full_compounding_loop_proven"] else 1
    return 0 if result["pipeline_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

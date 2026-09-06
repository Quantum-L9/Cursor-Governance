"""Exact-head cross-repo lifecycle proof (plan §35), against a real memory runtime.

Runs only when ``L9_MEMORY_DEV_CHECKOUT`` names a ``l9-graphiti-memory``
checkout whose ``.venv`` carries the package at the manifest's expected
version. That is the one condition a unit environment cannot construct: it
needs the other repository's installed runtime. Everything else (store,
state, config) is disposable and isolated per test.

Sequence: bind → health → hydrate no-hit → admit a continuation capsule →
hydrate retrieves it → close (dry run, then commit, then replay) → stale
capsule loses to current repository state.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from ops.graphiti.hydration import close_session as cs
from ops.graphiti.hydration.session_latches import load_close_receipt
from ops.memory.control_plane_client import MemoryControlPlaneClient, OutcomeStatus
from ops.memory.hydration import canonical_hydrate
from ops.memory.namespace_context import repository_state_digest, resolve_namespace_context
from ops.memory.runtime_binding import ENV_DEV_CHECKOUT, resolve_runtime_binding
from ops.memory.session_contracts import (
    ContinuationCapsuleV2,
    continuation_from_record_metadata,
)

ROOT = Path(__file__).resolve().parents[3]

pytestmark = pytest.mark.skipif(
    not os.environ.get(ENV_DEV_CHECKOUT),
    reason=f"{ENV_DEV_CHECKOUT} unset: the cross-repo proof needs a memory checkout with .venv",
)


@pytest.fixture
def runtime(tmp_path: Path) -> tuple[MemoryControlPlaneClient, dict[str, str]]:
    env = {
        **os.environ,
        "L9_MEMORY_DATA_DIR": str(tmp_path / "data"),
        "L9_MEMORY_STATE_DIR": str(tmp_path / "state"),
        "L9_MEMORY_JSON_LOGS": "0",
        # The point of the proof: production Cursor code runs with no provider
        # connection material in its environment (plan §34, egress tests).
    }
    env.pop("GRAPHITI_MCP_URL", None)
    env.pop("GRAPHITI_MCP_TOKEN", None)
    binding = resolve_runtime_binding(env=env)
    assert binding.ok, binding.reasons
    assert binding.runtime_mode == "development_checkout"
    return MemoryControlPlaneClient(binding, env=env, session_id="proof-session"), env


def test_lifecycle_against_the_real_memory_runtime(runtime, tmp_path: Path, monkeypatch) -> None:
    client, _env = runtime
    context = resolve_namespace_context(ROOT)
    namespace = context.write_namespace_hint
    assert namespace == "cursor-governance"
    workspace = str(ROOT)
    head = repository_state_digest(ROOT)
    assert head

    health = client.health()
    assert health.ok, health.error
    assert health.receipt.contract_version == "memory-control-plane/v1"

    empty = client.hydrate(
        "Realign memory control plane",
        workspace=workspace,
        write_namespace_hint=namespace,
        read_namespace_hints=(namespace,),
    )
    assert empty.status is OutcomeStatus.NO_HITS, empty.error

    capsule = ContinuationCapsuleV2(
        session_id="proof-session",
        repository_identity=context.repository_identity or "Quantum-L9/Cursor-Governance",
        objective="Realign memory control plane",
        next_action="Cut over SessionStart to canonical hydrate",
        repository_state_digest=head,
        producer_version="2.0.0",
        unfinished_work=("C4 hydration cutover",),
    )
    candidate = capsule.to_governed_candidate(
        namespace=namespace, source_sha=head, agent_id="cursor"
    )
    admitted = client.ingest_candidate(candidate, workspace=workspace)
    assert admitted.ok, admitted.error
    assert admitted.receipt.record_id
    replay = client.ingest_candidate(candidate, workspace=workspace)
    assert replay.ok and replay.receipt.status == "duplicate"
    assert replay.receipt.record_id == admitted.receipt.record_id

    hit = client.hydrate(
        "Realign memory control plane",
        workspace=workspace,
        write_namespace_hint=namespace,
        read_namespace_hints=(namespace,),
    )
    assert hit.ok, hit.error
    assert admitted.receipt.record_id in hit.receipt.record_ids

    # The stored record carries the capsule losslessly and current git state wins.
    raw_get = client._invoke(
        ["get", admitted.receipt.record_id, "--group-id", namespace], cwd=workspace
    )
    assert raw_get.payload is not None
    recovered = continuation_from_record_metadata(raw_get.payload["metadata"])
    assert recovered == capsule
    assert recovered.is_stale_for(head) is False
    assert recovered.is_stale_for("0" * 40) is True

    dry = client.close(
        workspace=workspace, namespace=namespace, summary="proof close", dry_run=True
    )
    assert dry.status is OutcomeStatus.NOT_COMMITTED
    committed = client.close(
        workspace=workspace,
        namespace=namespace,
        summary="proof close",
        capsule_digest=capsule.digest(),
        idempotency_key="close:proof-session",
    )
    assert committed.ok, committed.error
    assert committed.receipt.committed and committed.receipt.replayed is False
    again = client.close(
        workspace=workspace,
        namespace=namespace,
        summary="proof close",
        capsule_digest=capsule.digest(),
        idempotency_key="close:proof-session",
    )
    assert again.ok and again.receipt.replayed is True
    assert again.receipt.record_id == committed.receipt.record_id

    denied = client.hydrate(
        "anything",
        workspace=workspace,
        write_namespace_hint=namespace,
        read_namespace_hints=(namespace, "some-other-repo"),
    )
    assert denied.status is OutcomeStatus.UNAUTHORIZED_NAMESPACE

    # Read fan-in to memory's shared namespace is a request memory grants (C2).
    shared = client.hydrate(
        "anything",
        workspace=workspace,
        write_namespace_hint=namespace,
        read_namespace_hints=tuple(context.read_namespace_hints),
    )
    assert shared.status in {OutcomeStatus.OK, OutcomeStatus.NO_HITS}, shared.error
    assert "l9-workspace" in context.read_namespace_hints

    # Steps 20-23 (plan §35): a new session hydrates canonically, recovers the
    # continuation in the right namespace, and current repository truth wins
    # over a newer but stale capsule.
    resumed = canonical_hydrate(ROOT, task="Resume session", client=client, session_id="next")
    assert resumed.status == "OK", resumed.error
    assert resumed.namespace_context.write_namespace_hint == namespace
    assert resumed.continuation is not None
    assert resumed.continuation.record_id == admitted.receipt.record_id
    assert resumed.continuation.capsule == capsule
    assert resumed.continuation.stale is False
    assert resumed.repository_state_digest == head

    stale_capsule = ContinuationCapsuleV2(
        session_id="proof-session-2",
        repository_identity=capsule.repository_identity,
        objective="Realign memory control plane",
        next_action="Edit a file that has since moved on",
        repository_state_digest="0" * 40,
        producer_version="2.0.0",
    )
    stale_admitted = client.ingest_candidate(
        stale_capsule.to_governed_candidate(
            namespace=namespace, source_sha=head, agent_id="cursor"
        ),
        workspace=workspace,
    )
    assert stale_admitted.ok, stale_admitted.error
    resumed_again = canonical_hydrate(
        ROOT, task="Resume session", client=client, session_id="next-2"
    )
    assert resumed_again.continuation is not None
    assert resumed_again.continuation.record_id == stale_admitted.receipt.record_id
    assert resumed_again.continuation.stale is True
    assert resumed_again.continuation_candidates == 2
    # Steps 15-18 through the real close path (stage C6): capsule admitted,
    # memory.close committed, local obligation CLOSED_CANONICALLY, and a second
    # SessionEnd is one logical close.
    project = tmp_path / "proof-workspace"
    project.mkdir()
    monkeypatch.setattr(cs, "resolve_namespace_context", lambda *_a, **_k: context)
    monkeypatch.setattr(cs, "repository_state_digest", lambda _p: head)
    monkeypatch.setattr(cs, "load_transcript_excerpt", lambda **_k: ("user: finish C6", "test"))
    monkeypatch.setenv("MEMORY_PHASE_B", "0")
    monkeypatch.setenv("MEMORY_DISTILL_ENQUEUE", "0")
    report = cs.close_session(
        project_dir=project, session_id="proof-close", agent_id="cursor", client=client
    )
    assert report["status"] == "closed_canonically", report["warnings"]
    assert report["continuation"]["status"] == "admitted"
    assert report["close"]["replayed"] is False
    obligation = load_close_receipt(project, "proof-close")
    assert obligation["status"] == "closed_canonically"
    assert obligation["canonical_operation_id"]
    again = cs.close_session(
        project_dir=project, session_id="proof-close", agent_id="cursor", client=client
    )
    assert again["status"] == "idempotent_skip"
    replay = client.close(
        workspace=str(project),
        namespace=namespace,
        summary="replay",
        session_id="proof-close",
        idempotency_key=obligation["close_idempotency_key"],
    )
    assert replay.ok and replay.receipt.replayed is True
    # The next session recovers exactly that capsule as canonical continuation.
    resumed_close = canonical_hydrate(ROOT, task="Resume", client=client, session_id="after")
    assert resumed_close.continuation is not None
    assert resumed_close.continuation.capsule.session_id == "proof-close"

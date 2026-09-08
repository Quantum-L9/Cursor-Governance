"""ContinuationCapsuleV2: Cursor-owned schema, memory-owned storage."""

from __future__ import annotations

import json

import pytest

from ops.memory import session_contracts as sc

HEAD = "c" * 40


def capsule(**overrides: object) -> sc.ContinuationCapsuleV2:
    fields: dict[str, object] = {
        "session_id": "session-1",
        "repository_identity": "Quantum-L9/Cursor-Governance",
        "objective": "Realign memory control plane",
        "next_action": "Wire runtime binding",
        "repository_state_digest": HEAD,
        "producer_version": "2.0.0",
        "active_files": ("ops/memory/runtime_binding.py",),
        "unfinished_work": ("egress scanner",),
        "created_at": "2026-09-05T00:00:00+00:00",
    }
    fields.update(overrides)
    return sc.ContinuationCapsuleV2(**fields)  # type: ignore[arg-type]


def test_round_trip_is_lossless_and_digest_stable() -> None:
    original = capsule()
    payload = json.loads(original.canonical())
    restored = sc.ContinuationCapsuleV2.from_payload(payload)
    assert restored == original
    assert restored.digest() == original.digest()
    assert payload["schema"] == sc.CONTINUATION_SCHEMA


def test_task_signature_is_derived_from_objective_and_repository() -> None:
    first = capsule()
    same_task_other_session = capsule(session_id="session-2")
    assert first.task_signature == same_task_other_session.task_signature
    assert capsule(objective="something else").task_signature != first.task_signature


def test_current_repository_state_wins_over_a_stale_capsule() -> None:
    assert capsule().is_stale_for(HEAD) is False
    assert capsule().is_stale_for("d" * 40) is True


def test_governed_candidate_carries_the_capsule_losslessly() -> None:
    candidate = capsule().to_governed_candidate(
        namespace="cursor-governance", source_sha=HEAD, agent_id="cursor"
    )
    assert candidate["kind"] == "MemoryCandidate"
    assert candidate["source"]["visibility"] == "namespace_local"
    assert candidate["source"]["namespace"] == "cursor-governance"
    assert candidate["knowledge"]["primary_class"] == sc.CANDIDATE_CLASS
    assert candidate["knowledge"]["payload_schema"] == sc.CONTINUATION_SCHEMA
    assert candidate["knowledge"]["structured_payload"] == capsule().to_payload()
    assert candidate["governance"]["may_override_repository_state"] is False
    assert candidate["candidate_id"].startswith("cursor-continuation:Quantum-L9/Cursor-Governance:")
    # Idempotency: identical capsule -> identical candidate id; changed body -> new id.
    assert (
        candidate["candidate_id"]
        == capsule().to_governed_candidate(
            namespace="cursor-governance", source_sha=HEAD, agent_id="cursor"
        )["candidate_id"]
    )
    assert (
        capsule(next_action="other").to_governed_candidate(
            namespace="cursor-governance", source_sha=HEAD, agent_id="cursor"
        )["candidate_id"]
        != candidate["candidate_id"]
    )


def test_candidate_rejects_empty_namespace_request() -> None:
    with pytest.raises(sc.ContinuationContractError, match="namespace"):
        capsule().to_governed_candidate(namespace=" ", source_sha=HEAD, agent_id="cursor")


@pytest.mark.parametrize(
    "mutation",
    [
        {"schema": "cursor.continuation/v1"},
        {"objective": ""},
        {"next_action": None},
    ],
)
def test_malformed_payloads_are_refused(mutation: dict[str, object]) -> None:
    payload = capsule().to_payload()
    payload.update(mutation)
    if payload.get("next_action") is None:
        del payload["next_action"]
    with pytest.raises(sc.ContinuationContractError):
        sc.ContinuationCapsuleV2.from_payload(payload)


def test_record_metadata_recovery_ignores_non_continuation_records() -> None:
    assert sc.continuation_from_record_metadata({"payload_schema": "other"}) is None
    metadata = {
        "payload_schema": sc.CONTINUATION_SCHEMA,
        "structured_payload": capsule().to_payload(),
    }
    assert sc.continuation_from_record_metadata(metadata) == capsule()


def test_no_provider_vocabulary_in_the_session_contract() -> None:
    from pathlib import Path

    text = Path(sc.__file__).read_text(encoding="utf-8")
    for token in ("add_memory", "search_memory_facts", "GRAPHITI_MCP", "PICKUP|"):
        assert token not in text

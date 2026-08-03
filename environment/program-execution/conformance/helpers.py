from __future__ import annotations

from typing import Any

from adapters.common.digests import digest_object

PROGRAM_DIGEST = "sha256:" + "1" * 64
BASE_SHA = "2" * 40
CANDIDATE_SHA = "3" * 40
WORKTREE_PATH = "worktrees/program-task-001"
ATTEMPT_RECEIPT_PATH = "artifacts/attempt-receipt.json"


def valid_contract(
    *,
    task_id: str = "TASK-001",
    requested_actions: list[str] | None = None,
    allowed_actions: list[str] | None = None,
) -> dict[str, Any]:
    requested = requested_actions or ["inspect"]
    allowed = allowed_actions or list(requested)
    body: dict[str, Any] = {
        "schema": "program-execution-controller.task-contract.v2",
        "task_id": task_id,
        "target_id": "TARGET-001",
        "repository_id": "Quantum-L9/example",
        "objective": "Exercise the adapter contract.",
        "requested_actions": requested,
        "allowed_actions": allowed,
        "authorization_ceiling": dict.fromkeys(allowed, True),
        "acceptance_obligation_ids": [],
        "writable_paths": ["src/**"],
        "validation_commands": [["python3", "-V"]],
        "required_gate_ids": [],
        "required_evidence_ids": [],
        "risk_tier": "T1",
        "remote_mutation": False,
        "stop_conditions": ["program_lock_drift"],
        "rollback": {"strategy": "discard_worktree"},
        "program_digest": PROGRAM_DIGEST,
        "source_contract_digest": "sha256:" + "4" * 64,
        "base_sha": BASE_SHA,
        "branch": "program/task-001",
        "worktree": WORKTREE_PATH,
        "lease_id": "LEASE-001",
        "attempt_number": 1,
        "attempt_receipt_path": ATTEMPT_RECEIPT_PATH,
        "action_class": "read_only_architecture_or_artifact_work",
        "target_kind": "git_repository",
    }
    body["contract_digest"] = digest_object(body)
    return body

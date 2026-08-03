from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def generated_data_packet(
    receipt: Mapping[str, Any],
    *,
    repository: str,
    base_sha: str,
    agent_id: str,
) -> dict[str, Any]:
    task_id = str(receipt.get("task_id") or "unknown-task")
    return {
        "schema_version": "1.0.0",
        "identity": {
            "packet_id": f"pes-{task_id}",
            "graph_id": f"pes-{task_id}-graph",
            "repository": repository,
            "repository_class": "governed_repository",
            "campaign_id": f"pes-{task_id}",
            "action_id": task_id,
            "agent_id": agent_id,
            "lease_id": str(receipt.get("lease_id") or "program-controller"),
            "role": "executor",
        },
        "provenance": {
            "repository": repository,
            "base_sha": base_sha,
            "generated_at": receipt.get("verified_at") or receipt.get("created_at"),
        },
        "primary_result": {
            "artifact_id": str(receipt.get("evidence_id") or task_id),
            "artifact_kind": str(receipt.get("schema") or "execution_receipt"),
            "status": str(receipt.get("verdict") or receipt.get("claimed_status") or "UNKNOWN"),
        },
        "generated_units": [],
        "reuse_assessment": {
            "reusable_data_found": False,
            "candidate_count": 0,
            "promoted_count": 0,
        },
        "unresolved_unknowns": [],
    }

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9-]+", "-", value).strip("-").lower()
    return cleaned or "task"


def deterministic_ids(
    program_id: str,
    task_id: str,
    attempt_number: int,
    adapter_id: str,
) -> dict[str, str]:
    campaign_id = f"pes-{_slug(program_id)}-{_slug(task_id)}-attempt-{attempt_number}"
    return {
        "campaign_id": campaign_id,
        "graph_id": campaign_id + "-graph",
        "action_id": _slug(task_id),
        "agent_id": f"{_slug(adapter_id)}-attempt-{attempt_number}",
    }


def map_program_contract(
    contract: Mapping[str, Any],
    *,
    adapter_id: str,
    attempt_number: int,
) -> dict[str, Any]:
    ids = deterministic_ids(
        str(contract.get("program_id") or "program"),
        str(contract.get("task_id") or contract.get("id")),
        attempt_number,
        adapter_id,
    )
    requested = list(contract.get("requested_actions") or [])
    mutation = any(item in {"local_write", "destructive_change"} for item in requested)
    return {
        "ids": ids,
        "campaign": {
            "campaign_id": ids["campaign_id"],
            "objective": str(contract.get("objective") or "Execute Program task"),
            "base_state": {"commit_sha": str(contract.get("base_sha") or "0" * 40)},
            "authority_profile": "program_controller_bound",
            "program_lock_digest": contract.get("program_lock_digest")
            or contract.get("program_digest"),
            "program_task_id": contract.get("task_id") or contract.get("id"),
        },
        "deployment": {
            "deployment_id": ids["campaign_id"] + "-deployment",
            "graph_id": ids["graph_id"],
            "adapter_id": adapter_id,
        },
        "graph": {
            "campaign_id": ids["campaign_id"],
            "graph_id": ids["graph_id"],
            "actions": [
                {
                    "action_id": ids["action_id"],
                    "role": "executor" if mutation else "recon",
                    "objective": str(contract.get("objective") or "Execute Program task"),
                    "mutation": mutation,
                    "dependencies": [],
                    "resource_class": "repository_mutation" if mutation else "repository_read",
                    "claims": list(contract.get("resource_claims") or []),
                    "completion": {
                        "artifact_kind": "program_task_result",
                        "required_fields": [
                            "program_lock_digest",
                            "contract_digest",
                            "candidate_sha",
                            "changed_files",
                        ],
                    },
                }
            ],
        },
    }

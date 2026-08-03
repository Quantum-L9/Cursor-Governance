from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def map_campaign(contract: Mapping[str, Any], dispatch_id: str) -> dict[str, Any]:
    task_id = str(contract.get("task_id") or contract.get("id"))
    return {
        "schema_version": "1.0.0",
        "campaign_id": f"pes-{task_id}-{dispatch_id[-8:]}",
        "objective": str(contract.get("objective") or "Execute Program task"),
        "authority_profile": "program_deploy_max_autonomy",
        "base_sha": str(contract.get("base_sha") or "0" * 40),
        "operations": list(contract.get("bounded_operations") or [task_id]),
        "dependencies": {},
        "mutation_operations": [
            task_id for action in contract.get("requested_actions") or [] if action == "local_write"
        ],
        "autonomous_merge": False,
        "program_lock_digest": contract.get("program_lock_digest")
        or contract.get("program_digest"),
        "contract_digest": contract.get("contract_digest")
        or contract.get("rendered_contract_digest"),
    }

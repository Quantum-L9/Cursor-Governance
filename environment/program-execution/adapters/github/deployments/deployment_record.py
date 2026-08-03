from __future__ import annotations

from typing import Any


def create_record(transport, contract: dict[str, Any]) -> dict[str, Any]:
    return transport.api(
        f"repos/{contract['repository']}/deployments",
        method="POST",
        json_body={
            "ref": str(contract["candidate_sha"]),
            "environment": str(contract["environment"]),
            "auto_merge": False,
            "required_contexts": [],
            "description": str(
                contract.get("description") or "Program Execution deployment record"
            ),
        },
    )

from __future__ import annotations

from typing import Any


def publish_check(transport, contract: dict[str, Any]) -> dict[str, Any]:
    fields = {
        "name": str(contract["check_name"]),
        "head_sha": str(contract["candidate_sha"]),
        "status": str(contract.get("check_status") or "completed"),
        "conclusion": str(contract["check_conclusion"]),
        "output[title]": str(contract.get("check_title") or contract["check_name"]),
        "output[summary]": str(contract.get("check_summary") or ""),
    }
    return transport.api(
        f"repos/{contract['repository']}/check-runs",
        method="POST",
        fields=fields,
    )

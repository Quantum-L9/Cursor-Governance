from __future__ import annotations

import time
from typing import Any


def find_run(transport, contract: dict[str, Any]) -> dict[str, Any] | None:
    rows = transport.json(
        [
            "run",
            "list",
            "--repo",
            str(contract["repository"]),
            "--workflow",
            str(contract["workflow"]),
            "--json",
            "databaseId,headSha,status,conclusion,url",
            "--limit",
            "20",
        ]
    )
    for row in rows or []:
        if row.get("headSha") == contract.get("candidate_sha"):
            return dict(row)
    return None


def wait_for_run(
    transport,
    contract: dict[str, Any],
    *,
    timeout_seconds: int,
    interval_seconds: int = 10,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        row = find_run(transport, contract)
        if row and row.get("status") == "completed":
            return row
        time.sleep(interval_seconds)
    raise TimeoutError("GitHub Actions verification timed out")

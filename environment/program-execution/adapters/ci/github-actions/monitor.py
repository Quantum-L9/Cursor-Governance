from __future__ import annotations

import time
from typing import Any


def find_run(
    transport, contract: dict[str, Any], state: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    """The run THIS dispatch produced, never merely a run at the same SHA.

    Matching on `headSha` alone adopted whatever earlier run existed at the
    candidate commit -- a push-triggered run, a prior attempt, another
    operator's dispatch -- and reported its conclusion as this verification's
    verdict. Once a run has been matched its id is pinned in `state`; until
    then only a `workflow_dispatch` run created at or after our dispatch time
    qualifies.
    """
    state = dict(state or {})
    pinned = state.get("host_run_id")
    evidence = state.get("dispatch_evidence") or {}
    dispatched_at = str(evidence.get("dispatched_at") or "")
    rows = transport.json(
        [
            "run",
            "list",
            "--repo",
            str(contract["repository"]),
            "--workflow",
            str(contract["workflow"]),
            "--json",
            "databaseId,headSha,status,conclusion,url,event,createdAt",
            "--limit",
            "20",
        ]
    )
    for row in rows or []:
        if pinned is not None:
            if row.get("databaseId") == pinned:
                return dict(row)
            continue
        if row.get("headSha") != contract.get("candidate_sha"):
            continue
        if row.get("event") != "workflow_dispatch":
            continue
        created = str(row.get("createdAt") or "")
        if dispatched_at and created and created < dispatched_at:
            continue
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
        row = find_run(transport, contract, state=None)
        if row and row.get("status") == "completed":
            return row
        time.sleep(interval_seconds)
    raise TimeoutError("GitHub Actions verification timed out")

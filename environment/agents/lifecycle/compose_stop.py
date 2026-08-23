from __future__ import annotations

import json
import re
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from environment.agents.lifecycle import receipts

_GITHUB_RE = re.compile(
    r"(?:https://github\.com/|git@github\.com:)(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$"
)


def _repository_from_workspace(workspace: str) -> str | None:
    if not workspace:
        return None
    root = Path(workspace).expanduser()
    if not root.exists():
        return None
    completed = subprocess.run(
        ["git", "-C", str(root), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    if completed.returncode == 0:
        match = _GITHUB_RE.search(completed.stdout.strip())
        if match:
            return f"{match.group('owner')}/{match.group('repo')}"
    return f"local/{root.resolve().name}"


def _pipeline_result(
    *,
    return_receipt: dict[str, Any],
    raw_result: Any,
    dispatch: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(raw_result, dict):
        return {
            "status": "REJECTED",
            "reason": "subagent output is not a structured result document",
            "acceptance_receipt": None,
            "ingress_receipt": None,
        }
    from environment.agents.results import gateway

    repository = str(
        payload.get("repository")
        or dispatch.get("repository")
        or _repository_from_workspace(str(dispatch.get("workspace") or ""))
        or "local/unknown"
    )
    repository_class = str(
        payload.get("repository_class") or dispatch.get("repository_class") or "governed_repository"
    )
    try:
        return gateway.accept_and_ingest(
            return_receipt=return_receipt,
            surface_result=raw_result,
            repository=repository,
            repository_class=repository_class,
            independent_validation_present=bool(
                payload.get("independent_validation_present", False)
            ),
            designated_authority_approval=bool(payload.get("designated_authority_approval", False)),
            recurrence_counts=(
                payload.get("recurrence_counts")
                if isinstance(payload.get("recurrence_counts"), Mapping)
                else None
            ),
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "FAILED",
            "reason": str(exc),
            "error_type": type(exc).__name__,
            "acceptance_receipt": None,
            "ingress_receipt": None,
        }


def compose_subagent_stop(payload: dict[str, Any]) -> dict[str, Any]:
    assignment_id = payload.get("assignment_id")
    if not assignment_id:
        return {"status": "QUARANTINED", "reason": "orphan subagentStop: missing assignment_id"}

    dispatch = receipts.load_dispatch(str(assignment_id))
    if dispatch is None:
        return {"status": "QUARANTINED", "reason": "orphan subagentStop: no DispatchReceipt"}

    raw_result = payload["output"] if "output" in payload else payload.get("result", "")
    raw_capture = receipts.write_raw_result(str(assignment_id), raw_result)
    existing = receipts.load_return(str(assignment_id))
    if existing is None:
        body = receipts.write_return(
            {
                "assignment_id": assignment_id,
                "campaign_id": dispatch.get("campaign_id"),
                "graph_id": dispatch.get("graph_id"),
                "action_id": dispatch.get("action_id"),
                "agent_id": dispatch.get("agent_id"),
                "parent_agent_id": dispatch.get("parent_agent_id"),
                "subagent_role": dispatch.get("subagent_role"),
                "result_role": dispatch.get("result_role"),
                "lease_id": dispatch.get("lease_id"),
                "base_sha": dispatch.get("base_sha"),
                "workspace": dispatch.get("workspace"),
                "repository": dispatch.get("repository"),
                "repository_class": dispatch.get("repository_class"),
                "surface": dispatch.get("surface"),
                "dispatch_receipt_digest": dispatch.get("receipt_digest"),
                "output_digest": raw_capture["result_digest"],
                "raw_result_digest": raw_capture["result_digest"],
                "raw_result_path": raw_capture["path"],
            }
        )
        idempotent = False
    else:
        body = existing
        idempotent = True
        persisted = receipts.load_raw_result(str(assignment_id))
        if persisted is not None:
            raw_result = persisted.get("result")

    pipeline = _pipeline_result(
        return_receipt=body,
        raw_result=raw_result,
        dispatch=dispatch,
        payload=payload,
    )
    return {
        "status": "RETURNED",
        "idempotent": idempotent,
        "return_receipt": body,
        "raw_result": {
            "path": raw_capture["path"],
            "digest": raw_capture["result_digest"],
        },
        "generated_data": pipeline,
    }


def main() -> int:
    payload = json.load(sys.stdin)
    try:
        result = compose_subagent_stop(payload)
    except Exception as exc:  # noqa: BLE001
        result = {
            "status": "FAILED",
            "reason": str(exc),
            "error_type": type(exc).__name__,
        }
    json.dump(result, sys.stdout)
    print()
    if result.get("status") != "RETURNED":
        return 2
    generated = result.get("generated_data") or {}
    return 0 if generated.get("status") == "ACCEPTED" else 2


if __name__ == "__main__":
    raise SystemExit(main())

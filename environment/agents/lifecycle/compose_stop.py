from __future__ import annotations

import hashlib
import json
import sys
from typing import Any

from environment.agents.lifecycle import receipts


def compose_subagent_stop(payload: dict[str, Any]) -> dict[str, Any]:
    assignment_id = payload.get("assignment_id")
    if not assignment_id:
        return {"status": "QUARANTINED", "reason": "orphan subagentStop: missing assignment_id"}

    dispatch = receipts.load_dispatch(assignment_id)
    if dispatch is None:
        return {"status": "QUARANTINED", "reason": "orphan subagentStop: no DispatchReceipt"}

    existing = receipts.load_return(assignment_id)
    if existing is not None:
        return {"status": "RETURNED", "idempotent": True, "return_receipt": existing}

    output = payload.get("output") or payload.get("result") or ""
    if isinstance(output, (dict, list)):
        raw = json.dumps(output, sort_keys=True).encode()
    else:
        raw = str(output).encode()
    output_digest = hashlib.sha256(raw).hexdigest()

    body = receipts.write_return(
        {
            "assignment_id": assignment_id,
            "campaign_id": dispatch.get("campaign_id"),
            "graph_id": dispatch.get("graph_id"),
            "action_id": dispatch.get("action_id"),
            "parent_agent_id": dispatch.get("parent_agent_id"),
            "subagent_role": dispatch.get("subagent_role"),
            "lease_id": dispatch.get("lease_id"),
            "base_sha": dispatch.get("base_sha"),
            "workspace": dispatch.get("workspace"),
            "surface": dispatch.get("surface"),
            "dispatch_receipt_digest": dispatch.get("receipt_digest"),
            "output_digest": output_digest,
        }
    )
    return {"status": "RETURNED", "idempotent": False, "return_receipt": body}


def main() -> int:
    payload = json.load(sys.stdin)
    result = compose_subagent_stop(payload)
    json.dump(result, sys.stdout)
    print()
    return 0 if result.get("status") in {"RETURNED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())

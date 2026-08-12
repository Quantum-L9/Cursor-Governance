from __future__ import annotations

ASSIGNMENT_SCHEMA = "l9.assignment-receipt.v1"
DISPATCH_SCHEMA = "l9.subagent-dispatch-receipt.v1"
RETURN_SCHEMA = "l9.subagent-return-receipt.v1"
PR_ASSIGNMENT_SCHEMA = "l9.pr-remediation-assignment.v1"

CORRELATION_FIELDS = (
    "assignment_id",
    "campaign_id",
    "graph_id",
    "action_id",
    "parent_agent_id",
    "subagent_role",
    "lease_id",
    "base_sha",
    "workspace",
    "surface",
)

from __future__ import annotations

ASSIGNMENT_SCHEMA = "l9.assignment-receipt.v1"
DISPATCH_SCHEMA = "l9.subagent-dispatch-receipt.v1"
RETURN_SCHEMA = "l9.subagent-return-receipt.v1"
PR_ASSIGNMENT_SCHEMA = "l9.pr-remediation-assignment.v1"
HOST_CORRELATION_SCHEMA = "l9.cursor-subagent.host-correlation.v1"
HOST_RAW_STOP_SCHEMA = "l9.cursor-subagent.host-stop.v1"

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

HOST_CORRELATION_FIELDS = (
    "tool_use_id",
    "tool_call_id",
    "subagent_id",
    "parent_conversation_id",
    "model",
    "is_parallel_worker",
    "git_branch",
)

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from autonomy.adapters.protocol import AdapterConfig

CURSOR_REQUIRED_TASK_FIELDS = (
    "agent_id",
    "action_id",
    "lease_id",
    "role",
    "prompt",
    "run_in_background",
    "mutation",
)

# Exact autonomy-role -> Cursor-subagent result-kind mapping. Roles absent here
# (synthesis, poller, coordinator, ...) carry no result-document contract.
CURSOR_ROLE_TO_RESULT_KIND = {
    "recon": "ReconReport",
    "remediator": "PRRemediationReport",
    "executor": "TestReport",
    "test": "TestReport",
    "evidence_writer": "DocumentationReport",
    "documentation": "DocumentationReport",
    "reviewer": "VerificationReviewReport",
    "verifier": "VerificationReviewReport",
    "verifier_reviewer": "VerificationReviewReport",
}
CURSOR_SUBAGENT_RESULT_SCHEMA = "l9.cursor-subagent.result.v1"
CURSOR_SUBAGENT_RESULT_SCHEMA_PATH = (
    "environment/agents/cursor-subagents/schemas/cursor-subagent-result.schema.json"
)


def _result_contract(role: str) -> dict[str, Any] | None:
    """Result-document contract the subagent must return, or None if the role
    has no Cursor-subagent result kind."""
    result_kind = CURSOR_ROLE_TO_RESULT_KIND.get(role)
    if result_kind is None:
        return None
    return {
        "schema": CURSOR_SUBAGENT_RESULT_SCHEMA,
        "schema_path": CURSOR_SUBAGENT_RESULT_SCHEMA_PATH,
        "result_kind": result_kind,
        "required_output": "one_structured_document",
        "narrative_only_completion_allowed": False,
    }


def load_cursor_config(payload: Mapping[str, Any]) -> AdapterConfig:
    config = AdapterConfig.from_dict(payload)
    if config.surface != "cursor-ide":
        raise ValueError("Cursor adapter requires adapter_type='cursor'")
    return config


def build_cursor_task(deployment: Mapping[str, Any]) -> dict[str, Any]:
    contract = deployment["agent_contract"]
    lease = deployment["lease"]
    role = contract["role"]
    background_roles = {
        "recon",
        "verifier",
        "poller",
        "sentinel",
    }
    task = {
        "agent_id": contract["agent_id"],
        "action_id": contract["action_id"],
        "lease_id": lease["lease_id"],
        "role": role,
        "mutation": contract["mutation"],
        "run_in_background": role in background_roles,
        "subagent_type": _cursor_subagent_type(role),
        "prompt": _render_prompt(contract),
        "environment": {
            "L9_AUTONOMY_REQUIRED": "1",
            "L9_CAMPAIGN_ID": contract["campaign_id"],
            "L9_GRAPH_ID": contract["graph_id"],
            "L9_ACTION_ID": contract["action_id"],
            "L9_AGENT_ID": contract["agent_id"],
            "L9_LEASE_ID": contract["lease_id"],
            "L9_CAPABILITY_ID": contract["capability_id"],
            "L9_BASE_SHA": contract["base_sha"],
            "L9_DIRECT_TOOL_ACCESS": "0",
            "L9_AUTONOMOUS_MERGE": "0",
        },
    }
    missing = [field for field in CURSOR_REQUIRED_TASK_FIELDS if field not in task]
    if missing:
        raise ValueError("Cursor task missing required fields: " + ", ".join(missing))
    result_contract = _result_contract(role)
    if result_contract is not None:
        task["result_contract"] = result_contract
    return task


def cursor_task_json(deployment: Mapping[str, Any]) -> str:
    import json

    return json.dumps(build_cursor_task(deployment), indent=2, sort_keys=True) + "\n"


def _cursor_subagent_type(role: str) -> str:
    mapping = {
        "recon": "explore",
        "synthesis": "generalPurpose",
        "executor": "generalPurpose",
        "verifier": "generalPurpose",
        "reviewer": "generalPurpose",
        "poller": "generalPurpose",
        "failure_classifier": "generalPurpose",
        "remediator": "generalPurpose",
        "context_compiler": "explore",
        "sentinel": "explore",
        "evidence_writer": "generalPurpose",
        "coordinator": "generalPurpose",
    }
    try:
        return mapping[role]
    except KeyError as exc:
        raise ValueError(f"Unsupported Cursor role: {role}") from exc


def _render_prompt(contract: Mapping[str, Any]) -> str:
    authority = contract["authority"]
    completion = contract["completion"]
    scope = contract["scope"]
    lines = [
        "# L9 Enforced Agent Contract",
        "",
        f"Campaign: {contract['campaign_id']}",
        f"Graph: {contract['graph_id']}",
        f"Action: {contract['action_id']}",
        f"Agent: {contract['agent_id']}",
        f"Lease: {contract['lease_id']}",
        f"Role: {contract['role']}",
        f"Mutation: {str(contract['mutation']).lower()}",
        f"Base SHA: {contract['base_sha']}",
        "",
        "## Objective",
        contract["objective"],
        "",
        "## Mandatory runtime protocol",
        "1. Acknowledge the exact capability set before any tool use.",
        "2. Include the lease ID in every mediated tool request.",
        "3. Send heartbeats while running.",
        "4. Stop immediately if the lease is revoked or the base SHA drifts.",
        "5. Complete only by submitting the required typed artifact.",
        "6. Natural-language claims of completion are invalid.",
        "",
        "## Allowed capabilities",
    ]
    lines.extend(f"- {capability}" for capability in authority["allowed_capabilities"])
    lines.extend(["", "## Globally forbidden capabilities"])
    lines.extend(f"- {capability}" for capability in authority["globally_forbidden_capabilities"])
    lines.extend(["", "## Resource claims"])
    for claim in scope["claims"]:
        lines.append(
            f"- {claim['mode']} {claim['key']} (exclusive={claim.get('exclusive', False)})"
        )
    lines.extend(
        [
            "",
            "## Required completion artifact",
            f"Kind: {completion['artifact_kind']}",
            "Required payload fields:",
        ]
    )
    lines.extend(f"- {field}" for field in completion["required_fields"])
    lines.extend(["", "## Stop conditions"])
    lines.extend(f"- {condition}" for condition in contract["stop_conditions"])
    return "\n".join(lines)

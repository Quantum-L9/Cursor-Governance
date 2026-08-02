from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

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


def load_cursor_config(payload: Mapping[str, Any]) -> AdapterConfig:
    config = AdapterConfig.from_dict(payload)
    if config.adapter_type.value != "cursor":
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
        raise ValueError(
            "Cursor task missing required fields: " + ", ".join(missing)
        )
    return task


def write_cursor_task(deployment: Mapping[str, Any], path: str | Path) -> None:
    import json

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(build_cursor_task(deployment), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


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
    lines.extend(
        f"- {capability}" for capability in authority["allowed_capabilities"]
    )
    lines.extend(["", "## Globally forbidden capabilities"])
    lines.extend(
        f"- {capability}"
        for capability in authority["globally_forbidden_capabilities"]
    )
    lines.extend(["", "## Resource claims"])
    for claim in scope["claims"]:
        lines.append(
            f"- {claim['mode']} {claim['key']} "
            f"(exclusive={claim.get('exclusive', False)})"
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

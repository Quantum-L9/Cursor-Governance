from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from autonomy.adapters.protocol import AdapterConfig

# Every parallel-safe analytical role runs in the background so a swarm is not
# serialized by the foreground task slot.
BACKGROUND_ROLES = frozenset(
    {
        "context_compiler",
        "recon",
        "synthesis",
        "verifier",
        "reviewer",
        "failure_classifier",
        "poller",
        "sentinel",
        "evidence_writer",
    }
)

# Mutation roles are foreground by default. They are already admitted
# concurrently by the scheduler (claim-limited, not count-limited); this flag
# only decides whether one orchestrating session also detaches them. Enable it
# per deployment once background tasks are confirmed to preserve lease
# propagation, mandatory hooks, and heartbeat for a writing worker — the
# enforcement itself is identical either way.
MUTATION_ROLES = frozenset({"executor", "remediator"})


def load_claude_code_config(payload: Mapping[str, Any]) -> AdapterConfig:
    config = AdapterConfig.from_dict(payload)
    if config.surface not in {"claude-cli", "claude-web", "claude-mobile"}:
        raise ValueError("Claude Code adapter requires adapter_type='claude-code'")
    return config


def build_claude_task(
    deployment: Mapping[str, Any],
    *,
    background_mutation_roles: bool = False,
) -> dict[str, Any]:
    contract = deployment["agent_contract"]
    lease = deployment["lease"]
    return {
        "name": f"l9-{contract['action_id']}",
        "description": contract["objective"],
        "subagent_type": _claude_subagent_type(contract["role"]),
        "run_in_background": _runs_in_background(
            contract["role"],
            background_mutation_roles=background_mutation_roles,
        ),
        "prompt": _render_prompt(contract),
        "environment": {
            "L9_AUTONOMY_REQUIRED": "1",
            "L9_CAMPAIGN_ID": contract["campaign_id"],
            "L9_GRAPH_ID": contract["graph_id"],
            "L9_ACTION_ID": contract["action_id"],
            "L9_AGENT_ID": contract["agent_id"],
            "L9_LEASE_ID": lease["lease_id"],
            "L9_CAPABILITY_ID": contract["capability_id"],
            "L9_BASE_SHA": contract["base_sha"],
            "L9_DIRECT_TOOL_ACCESS": "0",
            "L9_AUTONOMOUS_MERGE": "0",
        },
        "hooks": {
            "pre_tool_use": {
                "command": "python -m autonomy.adapters.tool_hook --phase pre",
                "required": True,
                "fail_closed": True,
            },
            "post_tool_use": {
                "command": "python -m autonomy.adapters.tool_hook --phase post",
                "required": True,
                "fail_closed": True,
            },
            "heartbeat": {
                "command": "python -m autonomy.adapters.heartbeat_hook",
                "required": True,
            },
        },
    }


def claude_task_json(
    deployment: Mapping[str, Any],
    *,
    background_mutation_roles: bool = False,
) -> str:
    import json

    task = build_claude_task(
        deployment,
        background_mutation_roles=background_mutation_roles,
    )
    return json.dumps(task, indent=2, sort_keys=True) + "\n"


def _runs_in_background(
    role: str,
    *,
    background_mutation_roles: bool,
) -> bool:
    if role in BACKGROUND_ROLES:
        return True
    return background_mutation_roles and role in MUTATION_ROLES


def _claude_subagent_type(role: str) -> str:
    mapping = {
        "recon": "Explore",
        "context_compiler": "Explore",
        "sentinel": "Explore",
        "coordinator": "general-purpose",
        "synthesis": "general-purpose",
        "executor": "general-purpose",
        "verifier": "general-purpose",
        "reviewer": "general-purpose",
        "poller": "general-purpose",
        "failure_classifier": "general-purpose",
        "remediator": "general-purpose",
        "evidence_writer": "general-purpose",
    }
    try:
        return mapping[role]
    except KeyError as exc:
        raise ValueError(f"Unsupported Claude Code role: {role}") from exc


def _render_prompt(contract: Mapping[str, Any]) -> str:
    return "\n".join(
        [
            "# L9 Enforced Claude Code Subagent",
            "",
            f"Campaign: {contract['campaign_id']}",
            f"Action: {contract['action_id']}",
            f"Role: {contract['role']}",
            f"Lease: {contract['lease_id']}",
            f"Base SHA: {contract['base_sha']}",
            "",
            contract["objective"],
            "",
            "All tool calls are fail-closed through the L9 pre-tool hook.",
            "Do not invoke a tool unless the lease is active.",
            "Do not mutate unless the role and lease grant mutation.",
            "Do not merge, force-push, weaken tests, or expand scope.",
            "Send heartbeats and submit the required typed artifact.",
            "",
            "Required artifact kind: " + contract["completion"]["artifact_kind"],
            "Required payload fields:",
            *[f"- {field}" for field in contract["completion"]["required_fields"]],
        ]
    )

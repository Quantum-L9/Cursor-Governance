from __future__ import annotations

from typing import Any, Mapping


def render_agent_contract(
    *,
    campaign: Mapping[str, Any],
    graph_id: str,
    action: Mapping[str, Any],
    lease: Mapping[str, Any],
    capabilities: list[str],
    globally_forbidden: list[str],
    dependency_artifacts: list[str],
) -> dict[str, Any]:
    completion = action["completion"]
    return {
        "schema_version": "1.0.0",
        "campaign_id": campaign["campaign_id"],
        "graph_id": graph_id,
        "action_id": action["id"],
        "agent_id": lease["agent_id"],
        "lease_id": lease["lease_id"],
        "capability_id": lease["capability_id"],
        "role": action["role"],
        "mutation": bool(action["mutation"]),
        "base_sha": lease["base_sha"],
        "expires_at": lease["expires_at"],
        "objective": action.get("metadata", {}).get(
            "objective",
            f"Complete action {action['id']}",
        ),
        "authority": {
            "allowed_capabilities": sorted(capabilities),
            "globally_forbidden_capabilities": sorted(globally_forbidden),
            "allowed_operations": campaign["scope"]["allowed_operations"],
            "forbidden_operations": campaign["scope"]["forbidden_operations"],
        },
        "scope": {
            "campaign_allowed_paths": campaign["scope"]["allowed_paths"],
            "campaign_forbidden_paths": campaign["scope"]["forbidden_paths"],
            "action_allowed_paths": action.get("metadata", {}).get(
                "allowed_paths", []
            ),
            "claims": action.get("claims", []),
            "resource_class": action["resource_class"],
        },
        "dependencies": {
            "action_ids": action.get("depends_on", []),
            "artifact_ids": dependency_artifacts,
        },
        "completion": {
            "artifact_kind": completion["artifact_kind"],
            "required_fields": completion.get("required_fields", []),
            "require_base_sha_match": completion.get(
                "require_base_sha_match", True
            ),
            "require_empty_blockers": completion.get(
                "require_empty_blockers", False
            ),
        },
        "runtime_protocol": {
            "acknowledge_before_tools": True,
            "mediate_every_tool_call": True,
            "heartbeat_required": True,
            "submit_typed_artifact": True,
            "natural_language_completion_is_invalid": True,
            "lease_transfer_forbidden": True,
        },
        "stop_conditions": [
            "lease revoked or expired",
            "base SHA drift",
            "scope expansion",
            "policy conflict",
            "forbidden path required",
            "human gate reached",
            "evidence cannot be produced honestly",
        ],
    }

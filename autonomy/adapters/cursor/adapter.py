from __future__ import annotations

import importlib.util
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from autonomy.adapters.protocol import AdapterConfig

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ROLES_PATH = _REPO_ROOT / "environment/agents/cursor-subagents/CURSOR_SUBAGENT_ROLES.yaml"
_BRIDGE_PATH = _REPO_ROOT / "environment/agents/cursor-subagents/result_bridge.py"
_BRIDGE_MODULE = "cursor_result_bridge"
# Roles with no Cursor-subagent definition (poller, sentinel, ...) keep the
# adapter's own background policy; everything defined in ROLES.yaml is
# governed by that file's ``default_background``.
_UNDEFINED_BACKGROUND_ROLES = frozenset({"poller", "sentinel"})
_roles_cache: dict[str, Any] | None = None


def _result_bridge():
    """The result bridge owns the autonomy-role -> Cursor-role vocabulary.

    Loaded under the same module name the result adapter uses so there is one
    module object, not a second copy of the mapping.
    """
    cached = sys.modules.get(_BRIDGE_MODULE)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(_BRIDGE_MODULE, _BRIDGE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {_BRIDGE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[_BRIDGE_MODULE] = module
    spec.loader.exec_module(module)
    return module


def cursor_subagent_roles() -> dict[str, Any]:
    """Role definitions from CURSOR_SUBAGENT_ROLES.yaml, keyed by Cursor role."""
    global _roles_cache
    if _roles_cache is None:
        import yaml  # noqa: PLC0415

        document = yaml.safe_load(_ROLES_PATH.read_text(encoding="utf-8")) or {}
        roles = document.get("roles") if isinstance(document, dict) else None
        if not isinstance(roles, dict):
            raise ValueError(f"{_ROLES_PATH} has no roles mapping")
        _roles_cache = roles
    return _roles_cache


def runs_in_background(role: str) -> bool:
    """Background policy for one autonomy role, owned by ROLES.yaml.

    The role is resolved to its Cursor role through the bridge's single
    mapping and the definition's ``default_background`` decides; roles with no
    Cursor definition fall back to the adapter's own set.
    """
    cursor_role = _result_bridge().canonical_cursor_role(role)
    definition = cursor_subagent_roles().get(cursor_role)
    if isinstance(definition, Mapping):
        return bool(definition.get("default_background", True))
    return role in _UNDEFINED_BACKGROUND_ROLES


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
    "pr_remediation": "PRRemediationReport",
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
        raise ValueError(f"Cursor renderer requires surface 'cursor-ide'; got {config.surface!r}")
    return config


def build_cursor_task(deployment: Mapping[str, Any]) -> dict[str, Any]:
    contract = deployment["agent_contract"]
    lease = deployment["lease"]
    role = contract["role"]
    task = {
        "agent_id": contract["agent_id"],
        "action_id": contract["action_id"],
        "lease_id": lease["lease_id"],
        "role": role,
        "mutation": contract["mutation"],
        "run_in_background": runs_in_background(role),
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
    # Managed Task types are the ~/.cursor/agents filename stems. YAML
    # cursor_subagent_type is the built-in Cursor category, not this field.
    mapping = {
        "recon": "l9-recon",
        "remediator": "l9-pr-remediation",
        "pr_remediation": "l9-pr-remediation",
        "executor": "l9-test",
        "test": "l9-test",
        "evidence_writer": "l9-documentation",
        "documentation": "l9-documentation",
        "reviewer": "l9-verifier-reviewer",
        "verifier": "l9-verifier-reviewer",
        "verifier_reviewer": "l9-verifier-reviewer",
        "synthesis": "generalPurpose",
        "poller": "generalPurpose",
        "failure_classifier": "generalPurpose",
        "context_compiler": "explore",
        "sentinel": "explore",
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

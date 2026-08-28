from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

LOCAL_WRITE_OPERATIONS = (
    "read",
    "search",
    "create_worktree",
    "edit_scoped",
    "run_tests",
)
COMMIT_OPERATIONS = ("commit_local",)
INSPECT_OPERATIONS = ("read", "search")
FORBIDDEN_OPERATIONS = (
    "merge",
    "merge_pull_request",
    "admin_merge",
    "force_push",
    "modify_secrets",
    "weaken_tests_for_green",
    "push_non_force_declared_branch",
    "open_pull_request",
)
FAIL_CLOSED = {
    "missing_required_agent": True,
    "invalid_agent_output": True,
    "executor_without_synthesis": True,
    "self_review": True,
    "unverified_completion": True,
}


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9-]+", "-", value).strip("-").lower()
    return cleaned or "task"


def deterministic_ids(
    program_id: str,
    task_id: str,
    attempt_number: int,
    adapter_id: str,
) -> dict[str, str]:
    campaign_id = f"pes-{_slug(program_id)}-{_slug(task_id)}-attempt-{attempt_number}"
    action_id = _slug(task_id)
    return {
        "campaign_id": campaign_id,
        "graph_id": campaign_id + "-graph",
        "action_id": action_id,
        "synthesis_id": f"synthesize-{action_id}",
        "agent_id": f"{_slug(adapter_id)}-attempt-{attempt_number}",
    }


def _iso_now() -> datetime:
    return datetime.now(tz=UTC)


def _iso_text(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def requested_actions(contract: Mapping[str, Any]) -> set[str]:
    return {str(item) for item in (contract.get("requested_actions") or [])}


def _mutation_requested(contract: Mapping[str, Any]) -> bool:
    return bool(requested_actions(contract) & {"local_write", "destructive_change", "commit"})


def allowed_operations(contract: Mapping[str, Any]) -> list[str]:
    """Operations derived from the actions actually requested.

    "Mutation" is not one permission. A contract requesting local_write without
    commit used to receive the whole local-mutation set, including
    `commit_local`, because a single boolean stood in for both -- root autonomy
    inferred an authority the Program contract never asked for. Each operation
    now traces to the action that justifies it.
    """
    requested = requested_actions(contract)
    if not requested & {"local_write", "destructive_change", "commit"}:
        return list(INSPECT_OPERATIONS)
    operations = list(LOCAL_WRITE_OPERATIONS)
    if "commit" in requested:
        operations.extend(COMMIT_OPERATIONS)
    return operations


def _write_claims(contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    seen: set[str] = set()
    raw_claims = contract.get("resource_claims") or []
    if isinstance(raw_claims, list):
        for item in raw_claims:
            if not isinstance(item, Mapping):
                continue
            key = str(item.get("key") or "").strip()
            mode = str(item.get("mode") or "").strip()
            if not key or mode not in {"read", "write", "observe"}:
                continue
            exclusive = bool(item.get("exclusive", mode == "write"))
            if mode == "write" and not exclusive:
                exclusive = True
            if key in seen:
                continue
            seen.add(key)
            claims.append({"key": key, "mode": mode, "exclusive": exclusive})
    for path in contract.get("writable_paths") or []:
        key = str(path).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        claims.append({"key": key, "mode": "write", "exclusive": True})
    if not claims:
        claims.append({"key": "repository:declared", "mode": "write", "exclusive": True})
    return claims


def _allowed_paths(contract: Mapping[str, Any], *, mutation: bool) -> list[str]:
    paths = [str(path) for path in (contract.get("writable_paths") or []) if str(path).strip()]
    if paths:
        return paths
    return ["**"] if not mutation else ["repository:declared"]


def map_program_contract(
    contract: Mapping[str, Any],
    *,
    adapter_id: str,
    attempt_number: int,
) -> dict[str, Any]:
    ids = deterministic_ids(
        str(contract.get("program_id") or contract.get("program_digest") or "program"),
        str(contract.get("task_id") or contract.get("id")),
        attempt_number,
        adapter_id,
    )
    mutation = _mutation_requested(contract)
    now = _iso_now()
    base_sha = str(contract.get("base_sha") or "").strip()
    objective = str(contract.get("objective") or "Execute Program task")
    repository = str(contract.get("repository_id") or contract.get("repository") or "local")
    branch = str(contract.get("branch") or "HEAD")
    campaign = {
        "schema_version": "1.0.0",
        "campaign_id": ids["campaign_id"],
        "objective": objective,
        "authority": {
            "issuer": "program_controller",
            "issued_at": _iso_text(now),
            "expires_at": _iso_text(now + timedelta(minutes=15)),
        },
        "scope": {
            "repositories": [repository],
            "allowed_paths": _allowed_paths(contract, mutation=mutation),
            "forbidden_paths": [
                "ops/secrets/**",
                ".env",
                "**/*.pem",
                "**/*.key",
            ],
            "allowed_operations": allowed_operations(contract),
            "forbidden_operations": list(FORBIDDEN_OPERATIONS),
        },
        "budgets": {
            "max_files_changed": 80,
            "max_lines_changed": 6000,
            "max_mutation_agents": 1,
            "max_read_agents": 8,
            "max_poll_agents": 0,
            "max_runtime_minutes": 15,
            "max_tool_failures": 8,
        },
        "validation": {
            "required_checks": ["schema_validation", "scope_lock"],
            "independent_review_required": True,
            "human_merge_required": True,
        },
        "base_state": {
            "repository": repository,
            "branch": branch,
            "commit_sha": base_sha or "0" * 40,
        },
        "revocation": {
            "kill_switch_file": ".l9/autonomy/revoke",
            "revoke_on_scope_drift": True,
            "revoke_on_policy_conflict": True,
            "revoke_on_base_sha_drift": True,
        },
        "authority_profile": "program_controller_bound",
        "program_lock_digest": contract.get("program_lock_digest")
        or contract.get("program_digest"),
        "campaign_task_id": contract.get("task_id") or contract.get("id"),
    }
    if mutation:
        roles = {
            "synthesis": {"min": 1, "max": 1, "mutation": False},
            "executor": {"min": 1, "max": 1, "mutation": True},
        }
        actions = [
            {
                "id": ids["synthesis_id"],
                "role": "synthesis",
                "kind": "synthesis",
                "depends_on": [],
                "mutation": False,
                "resource_class": "synthesis",
                "claims": [],
                "completion": {
                    "artifact_kind": "ExecutionBrief",
                    "required_fields": ["objective", "base_sha", "contract_digest"],
                    "require_base_sha_match": True,
                    "require_empty_blockers": False,
                },
            },
            {
                "id": ids["action_id"],
                "role": "executor",
                "kind": "work",
                "depends_on": [ids["synthesis_id"]],
                "mutation": True,
                "resource_class": "repository_mutation",
                "claims": _write_claims(contract),
                "completion": {
                    "artifact_kind": "ExecutionResult",
                    "required_fields": [
                        "candidate_sha",
                        "changed_files",
                        "contract_digest",
                    ],
                    "require_base_sha_match": True,
                    "require_empty_blockers": False,
                },
            },
        ]
    else:
        roles = {"recon": {"min": 1, "max": 1, "mutation": False}}
        actions = [
            {
                "id": ids["action_id"],
                "role": "recon",
                "kind": "work",
                "depends_on": [],
                "mutation": False,
                "resource_class": "repository_recon",
                "claims": [],
                "completion": {
                    "artifact_kind": "ReconReport",
                    "required_fields": ["status", "evidence"],
                    "require_base_sha_match": True,
                    "require_empty_blockers": False,
                },
            }
        ]
    return {
        "ids": ids,
        "mutation": mutation,
        "campaign": campaign,
        "deployment": {
            "schema_version": "1.0.0",
            "deployment_id": ids["campaign_id"] + "-deployment",
            "campaign_id": ids["campaign_id"],
            "graph_id": "AUTO",
            "adapter_id": adapter_id,
            "required_roles": roles,
            "fail_closed": dict(FAIL_CLOSED),
        },
        "graph": {
            "campaign_id": ids["campaign_id"],
            "graph_id": ids["graph_id"],
            "actions": actions,
        },
    }

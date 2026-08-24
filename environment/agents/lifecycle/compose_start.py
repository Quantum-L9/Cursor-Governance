from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

_GOV_ROOT = Path(__file__).resolve().parents[3]
if str(_GOV_ROOT) not in sys.path:
    sys.path.insert(0, str(_GOV_ROOT))

from environment.agents.lifecycle import receipts  # noqa: E402

_TOKEN_PATTERN = re.compile(r"L9_ADMISSION_TOKEN=([A-Za-z0-9-]+)")


def _deny(reason: str) -> dict[str, Any]:
    return {"permission": "deny", "reason": reason}


def _allow(dispatch: dict[str, Any]) -> dict[str, Any]:
    return {"permission": "allow", "dispatch_receipt": dispatch.get("receipt_digest")}


def _result_role(value: Any) -> str:
    raw = str(value or "").strip().lower().replace("-", "_")
    aliases = {
        "l9_recon": "recon",
        "recon": "recon",
        "l9_pr_remediation": "pr_remediation",
        "pr_remediation": "pr_remediation",
        "l9_test": "test",
        "test": "test",
        "l9_documentation": "documentation",
        "documentation": "documentation",
        "l9_verifier": "verifier_reviewer",
        "l9_reviewer": "verifier_reviewer",
        "verifier_reviewer": "verifier_reviewer",
    }
    return aliases.get(raw, raw)


def compose_subagent_start(
    payload: dict[str, Any], *, repo_root: Path | None = None
) -> dict[str, Any]:
    """Composed subagentStart gate with durable correlation identity."""

    assignment = payload.get("assignment") or {}
    assignment_id = assignment.get("assignment_id") or payload.get("assignment_id")
    if not assignment_id:
        return _deny("missing assignment_id")

    role = assignment.get("subagent_role") or payload.get("subagent_role") or ""
    if not role:
        return _deny("missing subagent_role")

    if not payload.get("skip_deployment_check"):
        dep = payload.get("deployment_receipt")
        if not isinstance(dep, dict) or dep.get("status") not in {"DEPLOYMENT_READY", "READY"}:
            return _deny("stale or missing deployment receipt")

    lease = payload.get("lease") or assignment.get("lease") or {}
    if payload.get("require_lease", True):
        if not lease.get("lease_id"):
            return _deny("stale or missing lease")
        if lease.get("status") not in {None, "ACTIVE", "active", "GRANTED"}:
            return _deny("stale lease")

    base_sha = assignment.get("base_sha") or payload.get("base_sha")
    if payload.get("require_base_sha", False) and not base_sha:
        return _deny("missing base_sha")

    workspace = str(assignment.get("workspace") or payload.get("workspace") or "")
    explicit_repo = assignment.get("repository") or payload.get("repository")
    if explicit_repo is None and repo_root is not None:
        explicit_repo = repo_root.name

    fields = {
        "assignment_id": assignment_id,
        "campaign_id": assignment.get("campaign_id") or payload.get("campaign_id"),
        "graph_id": assignment.get("graph_id") or payload.get("graph_id"),
        "action_id": assignment.get("action_id") or payload.get("action_id"),
        "agent_id": assignment.get("agent_id") or payload.get("agent_id") or str(assignment_id),
        "parent_agent_id": assignment.get("parent_agent_id")
        or payload.get("parent_agent_id")
        or "cursor",
        "subagent_role": role,
        "result_role": _result_role(
            assignment.get("result_role") or payload.get("result_role") or role
        ),
        "objective": assignment.get("objective") or payload.get("objective"),
        "input_artifact_ids": list(
            assignment.get("input_artifact_ids") or payload.get("input_artifact_ids") or []
        ),
        "allowed_paths": list(
            assignment.get("allowed_paths") or payload.get("allowed_paths") or []
        ),
        "forbidden_paths": list(
            assignment.get("forbidden_paths") or payload.get("forbidden_paths") or []
        ),
        "subject_agent_id": assignment.get("subject_agent_id") or payload.get("subject_agent_id"),
        "lease_id": lease.get("lease_id"),
        "base_sha": base_sha,
        "workspace": workspace,
        "repository": explicit_repo,
        "repository_class": assignment.get("repository_class")
        or payload.get("repository_class")
        or "governed_repository",
        "surface": assignment.get("surface") or payload.get("surface") or "cursor-ide",
    }
    if not receipts.assignment_path(str(assignment_id)).is_file():
        receipts.write_assignment(fields)
    dispatch = receipts.write_dispatch(fields)
    return _allow(dispatch)


def _resolve_runtime_database(payload: dict[str, Any]) -> Path | None:
    """Locate the root Autonomy runtime database for this workspace.

    Resolution order: explicit ``L9_AUTONOMY_RUNTIME_DB``, workspace roots the
    host payload names, then the hook process working directory. No database
    means no persisted root authority — the caller must fail closed.
    """
    override = os.environ.get("L9_AUTONOMY_RUNTIME_DB", "").strip()
    if override:
        path = Path(override).expanduser()
        return path if path.is_file() else None
    candidates: list[Path] = []
    for key in ("workspace_root", "workspace", "cwd"):
        value = str(payload.get(key) or "").strip()
        if value:
            candidates.append(Path(value))
    roots = payload.get("workspace_roots")
    if isinstance(roots, list):
        candidates.extend(Path(str(item)) for item in roots if str(item).strip())
    candidates.append(Path.cwd())
    for root in candidates:
        database = root / ".l9" / "autonomy" / "runtime.sqlite3"
        if database.is_file():
            return database
    return None


def _extract_admission_token(payload: dict[str, Any]) -> str | None:
    """Extract only the opaque admission token from the Task input.

    The token is a lookup key for authority already persisted in root
    Autonomy; nothing else in the Task text participates in admission.
    """
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        token = str(tool_input.get("l9_admission_token") or "").strip()
        if token:
            return token
        haystack = json.dumps(tool_input)
    else:
        haystack = str(tool_input or "")
    match = _TOKEN_PATTERN.search(haystack)
    return match.group(1) if match else None


def _host_bridge():
    from autonomy.adapters.cursor import host_bridge  # noqa: PLC0415

    return host_bridge


def compose_host_pre_tool_use(payload: dict[str, Any]) -> dict[str, Any]:
    """Admit a native Task launch only against pre-existing root authority.

    The canonical producer (`autonomy/adapters/cursor/host_bridge.py`) must
    have created a pending admission — root lease and rendered contract
    included — before the Task fires. The prompt may carry the opaque
    admission token, but the token only identifies persisted authority;
    identity and scope are never inferred from Task prose. Everything
    uncorrelated stays denied, exactly as PR #287's fail-closed floor.
    """
    if str(payload.get("tool_name") or "") != "Task":
        return _deny("native lifecycle preToolUse only accepts Task")
    tool_use_id = str(payload.get("tool_use_id") or "").strip()
    if not tool_use_id:
        return _deny("native Task missing tool_use_id")
    database = _resolve_runtime_database(payload)
    if database is None:
        return _deny(
            "no root Autonomy runtime database for this workspace; "
            "native Task admission stays fail-closed"
        )
    token = _extract_admission_token(payload)
    if not token:
        return _deny(
            "native Task carries no admission token; root authority must exist "
            "before launch and is never inferred from Task prose"
        )
    decision = _host_bridge().host_bind_pre_tool_use(database, token, tool_use_id)
    if not decision.get("allowed"):
        return _deny(str(decision.get("reason") or "admission denied"))
    admission = decision["admission"]
    return {
        "permission": "allow",
        "admission_token": admission["admission_token"],
        "lease_id": admission["lease_id"],
        "action_id": admission["action_id"],
    }


def compose_host_subagent_start(payload: dict[str, Any]) -> dict[str, Any]:
    """Correlate a host child to its bound admission; never manufacture identity."""
    subagent_id = str(payload.get("subagent_id") or "").strip()
    tool_call_id = str(payload.get("tool_call_id") or "").strip()
    if not subagent_id or not tool_call_id:
        return _deny("native subagentStart missing subagent_id or tool_call_id")
    database = _resolve_runtime_database(payload)
    if database is None:
        return _deny(
            "no root Autonomy runtime database for this workspace; "
            "native subagentStart stays fail-closed"
        )
    decision = _host_bridge().host_bind_subagent_start(
        database,
        tool_call_id=tool_call_id,
        subagent_id=subagent_id,
        parent_conversation_id=str(payload.get("parent_conversation_id") or "") or None,
        model=str(payload.get("model") or "") or None,
        is_parallel_worker=payload.get("is_parallel_worker"),
        git_branch=str(payload.get("git_branch") or "") or None,
    )
    if not decision.get("allowed"):
        return _deny(str(decision.get("reason") or "subagentStart correlation denied"))
    admission = decision["admission"]
    assignment_id = str(admission["admission_token"])
    fields = {
        "assignment_id": assignment_id,
        "campaign_id": admission["campaign_id"],
        "graph_id": admission["graph_id"],
        "action_id": admission["action_id"],
        "agent_id": admission["agent_id"],
        "parent_agent_id": "cursor",
        "subagent_role": admission["role"],
        "result_role": _result_role(admission["role"]),
        "objective": None,
        "input_artifact_ids": [],
        "allowed_paths": list(admission.get("allowed_paths") or []),
        "forbidden_paths": list(admission.get("forbidden_paths") or []),
        "subject_agent_id": None,
        "lease_id": admission["lease_id"],
        "base_sha": admission["base_sha"],
        "workspace": str(payload.get("workspace_root") or payload.get("workspace") or ""),
        "repository": None,
        "repository_class": "governed_repository",
        "surface": "cursor-ide",
    }
    if not receipts.assignment_path(assignment_id).is_file():
        receipts.write_assignment(fields)
    dispatch = receipts.write_dispatch(fields)
    receipts.write_host_correlation(
        {
            "subagent_id": subagent_id,
            "assignment_id": assignment_id,
            "tool_use_id": admission["tool_use_id"],
            "tool_call_id": tool_call_id,
            "parent_conversation_id": admission.get("parent_conversation_id"),
            "model": admission.get("model"),
            "is_parallel_worker": admission.get("is_parallel_worker"),
            "git_branch": admission.get("git_branch"),
            "lease_id": admission["lease_id"],
            "campaign_id": admission["campaign_id"],
            "action_id": admission["action_id"],
        }
    )
    return _allow(dispatch)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=("synthetic", "pre_tool_use", "subagent_start"),
        default="synthetic",
    )
    args = parser.parse_args()
    payload = json.load(sys.stdin)
    if args.mode == "pre_tool_use":
        result = compose_host_pre_tool_use(payload)
    elif args.mode == "subagent_start":
        result = compose_host_subagent_start(payload)
    else:
        result = compose_subagent_start(payload)
    json.dump(result, sys.stdout)
    print()
    return 0 if result.get("permission") == "allow" else 1


if __name__ == "__main__":
    raise SystemExit(main())

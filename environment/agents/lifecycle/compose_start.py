from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from environment.agents.lifecycle import receipts


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


def compose_host_pre_tool_use(payload: dict[str, Any]) -> dict[str, Any]:
    """Fail closed until a canonical parent admission producer is verified.

    Cursor supplies ``tool_use_id`` at preToolUse, but current repository code has
    no canonical owner that can bind that host id to a root-Autonomy lease without
    inferring identity from task prose. The audit explicitly forbids that inference.
    """
    if str(payload.get("tool_name") or "") != "Task":
        return _deny("native lifecycle preToolUse only accepts Task")
    tool_use_id = str(payload.get("tool_use_id") or "").strip()
    if not tool_use_id:
        return _deny("native Task missing tool_use_id")
    return _deny(
        "native Task admission is fail-closed until the canonical adapter-session "
        "producer binds tool_use_id to a root-Autonomy lease"
    )


def compose_host_subagent_start(payload: dict[str, Any]) -> dict[str, Any]:
    """Reject an uncorrelated host child rather than manufacturing L9 identity."""
    subagent_id = str(payload.get("subagent_id") or "").strip()
    tool_call_id = str(payload.get("tool_call_id") or "").strip()
    if not subagent_id or not tool_call_id:
        return _deny("native subagentStart missing subagent_id or tool_call_id")
    return _deny(
        "native subagentStart has no verified L9 assignment correlation; "
        "adapter-session activation remains blocked"
    )


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

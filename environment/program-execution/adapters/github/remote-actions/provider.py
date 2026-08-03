from __future__ import annotations

from pathlib import Path
from typing import Any

from adapters.common.approvals import require_exact_approval
from adapters.common.base import BaseExecutionAdapter
from adapters.common.imports import load_module


class GitHubRemoteActionsAdapter(BaseExecutionAdapter):
    adapter_id = "github-remote-actions"
    capabilities = ("create_branch", "push_branch", "create_draft_pr", "update_draft_pr")
    cancellation = "unsupported"

    def __init__(self, runtime_root: str | Path, repository_root: str | Path) -> None:
        super().__init__(runtime_root)
        self.repository_root = Path(repository_root).resolve()
        module = load_module(
            self.repository_root
            / "environment/program-execution/adapters/github/common/gh_transport.py",
            "pes_gh_transport_remote",
        )
        self.transport = module.GhTransport(self.repository_root)

    def _probe_status(self, context):
        module = load_module(
            self.repository_root
            / "environment/program-execution/adapters/github/common/auth_probe.py",
            "pes_gh_auth_probe_remote",
        )
        authentication = module.probe(self.repository_root)
        repository = context.metadata.get("repository")
        if authentication["status"] != "PASS":
            return "BLOCKED", authentication.get("reason"), [authentication]
        if not isinstance(repository, str) or not repository:
            return (
                "BLOCKED",
                "repository-specific permission probe is required",
                [authentication],
            )
        permission_module = load_module(
            self.repository_root
            / "environment/program-execution/adapters/github/common/permission_probe.py",
            "pes_gh_permission_probe_remote",
        )
        permissions = permission_module.repository_permissions(
            self.transport,
            repository,
        )
        can_push = bool(permissions.get("permissions", {}).get("push"))
        status = "PASS" if permissions["status"] == "PASS" and can_push else "BLOCKED"
        reason = None if status == "PASS" else "repository push permission is unproven"
        return status, reason, [authentication, permissions]

    def _dispatch_record(self, record: dict[str, Any]):
        contract = record["contract"]
        actions = list(contract.get("requested_actions") or [])
        if len(actions) != 1:
            raise ValueError("exactly one GitHub remote action is required")
        action = actions[0]
        approval = require_exact_approval(contract, action)
        if action == "create_branch":
            module = load_module(Path(__file__).with_name("branch.py"), "pes_remote_branch")
            result = module.create_branch(
                self.transport,
                str(contract["repository"]),
                str(contract["branch"]),
                str(contract["base_sha"]),
            )
        elif action == "push_branch":
            module = load_module(Path(__file__).with_name("push.py"), "pes_remote_push")
            result = module.push_branch(
                contract["repository_path"],
                remote=str(contract.get("remote") or "origin"),
                local_branch=str(contract["local_branch"]),
                remote_branch=str(contract["remote_branch"]),
            )
        elif action == "create_draft_pr":
            module = load_module(
                Path(__file__).with_name("pull_request.py"),
                "pes_remote_pull_request",
            )
            result = module.create_draft(self.transport, contract)
        elif action == "update_draft_pr":
            module = load_module(
                Path(__file__).with_name("pull_request.py"),
                "pes_remote_pull_request_update",
            )
            result = module.update_draft(self.transport, contract)
        else:
            raise ValueError(f"unsupported GitHub action: {action}")
        mapper = load_module(
            Path(__file__).with_name("receipt_mapper.py"),
            "pes_remote_receipt_mapper",
        )
        record["result"] = mapper.remote_receipt(
            contract,
            action=action,
            approval_id=approval.approval_id,
            result=result or {},
            evidence=[{"type": "exact_approval", "approved_by": approval.approved_by}],
        )
        return "PASS", [{"type": "github_remote_action", "action": action}]

from __future__ import annotations

from pathlib import Path
from typing import Any

from adapters.common.approvals import require_exact_approval
from adapters.common.base import BaseExecutionAdapter
from adapters.common.imports import load_module


class GitHubChecksAdapter(BaseExecutionAdapter):
    adapter_id = "github-checks"
    capabilities = ("read_checks", "publish_check")
    cancellation = "unsupported"

    def __init__(self, runtime_root: str | Path, repository_root: str | Path) -> None:
        super().__init__(runtime_root)
        self.repository_root = Path(repository_root).resolve()
        module = load_module(
            self.repository_root
            / "environment/program-execution/adapters/github/common/gh_transport.py",
            "pes_gh_transport_checks",
        )
        self.transport = module.GhTransport(self.repository_root)

    def _probe_status(self, context):
        module = load_module(
            self.repository_root
            / "environment/program-execution/adapters/github/common/auth_probe.py",
            "pes_gh_auth_probe_checks",
        )
        authentication = module.probe(self.repository_root)
        repository = context.metadata.get("repository")
        if authentication["status"] != "PASS":
            return "BLOCKED", authentication.get("reason"), [authentication]
        if not isinstance(repository, str) or not repository:
            return "BLOCKED", "repository is required for checks probe", [authentication]
        permission_module = load_module(
            self.repository_root
            / "environment/program-execution/adapters/github/common/permission_probe.py",
            "pes_gh_permission_probe_checks",
        )
        permissions = permission_module.repository_permissions(
            self.transport,
            repository,
        )
        readable = bool(permissions.get("permissions", {}).get("pull"))
        status = "PASS" if permissions["status"] == "PASS" and readable else "BLOCKED"
        reason = None if status == "PASS" else "checks read permission is unproven"
        return status, reason, [authentication, permissions]

    def _effective_capabilities(self, context, status, evidence):
        if status != "PASS":
            return ()
        capabilities = ["read_checks"]
        if context.metadata.get("checks_write_proven") is True:
            capabilities.append("publish_check")
        return tuple(capabilities)

    def _dispatch_record(self, record: dict[str, Any]):
        contract = record["contract"]
        actions = list(contract.get("requested_actions") or [])
        if len(actions) != 1:
            raise ValueError("exactly one checks action is required")
        action = actions[0]
        if action == "read_checks":
            module = load_module(
                Path(__file__).with_name("status_reader.py"),
                "pes_check_status_reader",
            )
            result = module.read_combined_status(
                self.transport,
                str(contract["repository"]),
                str(contract["candidate_sha"]),
            )
            approval_id = "READ_ONLY"
        elif action == "publish_check":
            approval = require_exact_approval(contract, "publish_check")
            module = load_module(
                Path(__file__).with_name("check_publisher.py"),
                "pes_check_publisher",
            )
            result = module.publish_check(self.transport, contract)
            approval_id = approval.approval_id
        else:
            raise ValueError("exactly one checks action is required")
        mapper = load_module(
            Path(__file__).with_name("receipt_mapper.py"),
            "pes_checks_receipt_mapper",
        )
        record["result"] = mapper.remote_receipt(
            contract,
            action=action,
            approval_id=approval_id,
            result=result or {},
            evidence=[{"type": "github_checks", "action": action}],
        )
        return "PASS", [{"type": "github_checks", "action": action}]

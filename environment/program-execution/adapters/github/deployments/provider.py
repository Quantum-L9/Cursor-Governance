from __future__ import annotations

from pathlib import Path
from typing import Any

from adapters.common.approvals import require_exact_approval
from adapters.common.base import BaseExecutionAdapter
from adapters.common.imports import load_module


class GitHubDeploymentsAdapter(BaseExecutionAdapter):
    adapter_id = "github-deployments"
    capabilities = ("read_environment", "create_deployment_record")
    cancellation = "unsupported"

    def __init__(self, runtime_root: str | Path, repository_root: str | Path) -> None:
        super().__init__(runtime_root)
        self.repository_root = Path(repository_root).resolve()
        module = load_module(
            self.repository_root
            / "environment/program-execution/adapters/github/common/gh_transport.py",
            "pes_gh_transport_deployments",
        )
        self.transport = module.GhTransport(self.repository_root)

    def _probe_status(self, context):
        module = load_module(
            self.repository_root
            / "environment/program-execution/adapters/github/common/auth_probe.py",
            "pes_gh_auth_probe_deployments",
        )
        authentication = module.probe(self.repository_root)
        repository = context.metadata.get("repository")
        if authentication["status"] != "PASS":
            return "BLOCKED", authentication.get("reason"), [authentication]
        if not isinstance(repository, str) or not repository:
            return (
                "BLOCKED",
                "repository is required for deployments probe",
                [authentication],
            )
        permission_module = load_module(
            self.repository_root
            / "environment/program-execution/adapters/github/common/permission_probe.py",
            "pes_gh_permission_probe_deployments",
        )
        permissions = permission_module.repository_permissions(
            self.transport,
            repository,
        )
        readable = bool(permissions.get("permissions", {}).get("pull"))
        status = "PASS" if permissions["status"] == "PASS" and readable else "BLOCKED"
        reason = None if status == "PASS" else "deployment read permission is unproven"
        return status, reason, [authentication, permissions]

    def _effective_capabilities(self, context, status, evidence):
        if status != "PASS":
            return ()
        capabilities = ["read_environment"]
        if context.metadata.get("deployments_write_proven") is True:
            capabilities.append("create_deployment_record")
        return tuple(capabilities)

    def _dispatch_record(self, record: dict[str, Any]):
        contract = record["contract"]
        actions = list(contract.get("requested_actions") or [])
        if actions == ["read_environment"]:
            module = load_module(
                Path(__file__).with_name("environment_gate.py"),
                "pes_environment_gate",
            )
            result = module.read_environment(
                self.transport,
                str(contract["repository"]),
                str(contract["environment"]),
            )
            mapper = load_module(
                Path(__file__).with_name("receipt_mapper.py"),
                "pes_environment_read_receipt_mapper",
            )
            record["result"] = mapper.environment_read_receipt(
                contract,
                result or {},
            )
            return "PASS", [{"type": "environment_read"}]
        if actions != ["create_deployment_record"]:
            raise ValueError("exactly one deployment-record action is required")
        approval = require_exact_approval(contract, "create_deployment_record")
        required = {"artifact_digest", "rollback_plan_digest"}
        missing = sorted(required - set(contract))
        if missing:
            raise ValueError(f"deployment record fields missing: {missing}")
        module = load_module(
            Path(__file__).with_name("deployment_record.py"),
            "pes_deployment_record",
        )
        result = module.create_record(self.transport, contract)
        mapper = load_module(
            Path(__file__).with_name("receipt_mapper.py"),
            "pes_deployment_receipt_mapper",
        )
        record["result"] = mapper.deployment_receipt(
            contract,
            result or {},
            approval.approval_id,
        )
        return "PASS", [{"type": "github_deployment_record"}]

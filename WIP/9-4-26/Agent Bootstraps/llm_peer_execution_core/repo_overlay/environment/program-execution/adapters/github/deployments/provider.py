from __future__ import annotations

from pathlib import Path

from peer_execution.driver_execution import DriverExecutionRequest, DriverInvocation
from peer_execution.imports import load_module
from peer_execution.provider import ProviderProbe


class GitHubDeploymentsDriver:
    provider_id = "github-deployments"

    def __init__(self, runtime_root: str | Path, repository_root: str | Path) -> None:
        self.repository_root = Path(repository_root).resolve()
        module = load_module(
            self.repository_root
            / "environment/program-execution/adapters/github/common/gh_transport.py",
            "pes_gh_transport_deployments",
        )
        self.transport = module.GhTransport(self.repository_root)

    def probe(self, context) -> ProviderProbe:
        auth = load_module(
            self.repository_root
            / "environment/program-execution/adapters/github/common/auth_probe.py",
            "pes_gh_auth_probe_deployments",
        ).probe(self.repository_root)
        repository = context.metadata.get("repository")
        if auth["status"] != "PASS" or not isinstance(repository, str) or not repository:
            return ProviderProbe(
                status="BLOCKED",
                blocked_reason=auth.get("reason") or "repository is required for deployments probe",
                evidence=(auth,),
            )
        permissions = load_module(
            self.repository_root
            / "environment/program-execution/adapters/github/common/permission_probe.py",
            "pes_gh_permission_probe_deployments",
        ).repository_permissions(self.transport, repository)
        readable = permissions["status"] == "PASS" and bool(
            permissions.get("permissions", {}).get("pull")
        )
        capabilities = ["read_environment"] if readable else []
        if readable and context.metadata.get("deployments_write_proven") is True:
            capabilities.append("create_deployment_record")
        return ProviderProbe(
            status="PASS" if readable else "BLOCKED",
            blocked_reason=None if readable else "deployment read permission is unproven",
            evidence=(auth, permissions),
            observed_capabilities=tuple(capabilities),
        )

    def invoke(self, request: DriverExecutionRequest) -> DriverInvocation:
        contract = request.contract
        actions = list(contract.get("requested_actions") or [])
        if actions == ["read_environment"]:
            result = load_module(
                Path(__file__).with_name("environment_gate.py"), "pes_environment_gate"
            ).read_environment(
                self.transport,
                str(contract["repository"]),
                str(contract["environment"]),
            )
            operation = "read_environment"
        elif actions == ["create_deployment_record"]:
            for key in ("artifact_digest", "rollback_plan_digest"):
                if not isinstance(contract.get(key), str) or not contract.get(key):
                    raise ValueError(f"deployment record field missing: {key}")
            result = load_module(
                Path(__file__).with_name("deployment_record.py"), "pes_deployment_record"
            ).create_record(self.transport, contract)
            operation = "create_deployment_record"
        else:
            raise ValueError("exactly one deployment-record action is required")
        return DriverInvocation(
            status="PASS",
            payload={"operation": operation, "result": result or {}},
            evidence=({"type": "github_deployment", "operation": operation},),
        )

    def poll(self, request, state) -> DriverInvocation:
        return DriverInvocation(status="UNSUPPORTED", state=state)

    def cancel(self, request, state) -> DriverInvocation:
        return DriverInvocation(status="UNSUPPORTED", state=state)


PROVIDER_CLASS = GitHubDeploymentsDriver

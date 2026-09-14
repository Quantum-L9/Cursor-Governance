from __future__ import annotations

from pathlib import Path

from peer_execution.driver_execution import DriverExecutionRequest, DriverInvocation
from peer_execution.imports import load_module
from peer_execution.provider import ProviderProbe


class GitHubChecksDriver:
    provider_id = "github-checks"

    def __init__(self, runtime_root: str | Path, repository_root: str | Path) -> None:
        self.repository_root = Path(repository_root).resolve()
        module = load_module(
            self.repository_root
            / "environment/program-execution/adapters/github/common/gh_transport.py",
            "pes_gh_transport_checks",
        )
        self.transport = module.GhTransport(self.repository_root)

    def probe(self, context) -> ProviderProbe:
        auth = load_module(
            self.repository_root
            / "environment/program-execution/adapters/github/common/auth_probe.py",
            "pes_gh_auth_probe_checks",
        ).probe(self.repository_root)
        repository = context.metadata.get("repository")
        if auth["status"] != "PASS" or not isinstance(repository, str) or not repository:
            return ProviderProbe(
                status="BLOCKED",
                blocked_reason=auth.get("reason") or "repository is required for checks probe",
                evidence=(auth,),
            )
        permissions = load_module(
            self.repository_root
            / "environment/program-execution/adapters/github/common/permission_probe.py",
            "pes_gh_permission_probe_checks",
        ).repository_permissions(self.transport, repository)
        readable = permissions["status"] == "PASS" and bool(
            permissions.get("permissions", {}).get("pull")
        )
        capabilities = ["read_checks"] if readable else []
        if readable and context.metadata.get("checks_write_proven") is True:
            capabilities.append("publish_check")
        return ProviderProbe(
            status="PASS" if readable else "BLOCKED",
            blocked_reason=None if readable else "checks read permission is unproven",
            evidence=(auth, permissions),
            observed_capabilities=tuple(capabilities),
        )

    def invoke(self, request: DriverExecutionRequest) -> DriverInvocation:
        contract = request.contract
        actions = list(contract.get("requested_actions") or [])
        if len(actions) != 1:
            raise ValueError("exactly one checks action is required")
        action = actions[0]
        if action == "read_checks":
            result = load_module(
                Path(__file__).with_name("status_reader.py"), "pes_check_status_reader"
            ).read_combined_status(
                self.transport,
                str(contract["repository"]),
                str(contract["candidate_sha"]),
            )
        elif action == "publish_check":
            result = load_module(
                Path(__file__).with_name("check_publisher.py"), "pes_check_publisher"
            ).publish_check(self.transport, contract)
        else:
            raise ValueError("unsupported checks action")
        return DriverInvocation(
            status="PASS",
            payload={"action": action, "result": result or {}},
            evidence=({"type": "github_checks", "action": action},),
        )

    def poll(self, request, state) -> DriverInvocation:
        return DriverInvocation(status="UNSUPPORTED", state=state)

    def cancel(self, request, state) -> DriverInvocation:
        return DriverInvocation(status="UNSUPPORTED", state=state)


PROVIDER_CLASS = GitHubChecksDriver

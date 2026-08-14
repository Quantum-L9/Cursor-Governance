from __future__ import annotations

from pathlib import Path

from peer_execution.driver_execution import DriverExecutionRequest, DriverInvocation
from peer_execution.imports import load_module
from peer_execution.provider import ProviderProbe


class GitHubRemoteActionsDriver:
    provider_id = "github-remote-actions"

    def __init__(self, runtime_root: str | Path, repository_root: str | Path) -> None:
        self.repository_root = Path(repository_root).resolve()
        module = load_module(
            self.repository_root
            / "environment/program-execution/adapters/github/common/gh_transport.py",
            "pes_gh_transport_remote",
        )
        self.transport = module.GhTransport(self.repository_root)

    def probe(self, context) -> ProviderProbe:
        auth = load_module(
            self.repository_root
            / "environment/program-execution/adapters/github/common/auth_probe.py",
            "pes_gh_auth_probe_remote",
        ).probe(self.repository_root)
        repository = context.metadata.get("repository")
        if auth["status"] != "PASS" or not isinstance(repository, str) or not repository:
            return ProviderProbe(
                status="BLOCKED",
                blocked_reason=(
                    auth.get("reason") or "repository-specific permission probe is required"
                ),
                evidence=(auth,),
            )
        permissions = load_module(
            self.repository_root
            / "environment/program-execution/adapters/github/common/permission_probe.py",
            "pes_gh_permission_probe_remote",
        ).repository_permissions(self.transport, repository)
        ready = permissions["status"] == "PASS" and bool(
            permissions.get("permissions", {}).get("push")
        )
        return ProviderProbe(
            status="PASS" if ready else "BLOCKED",
            blocked_reason=None if ready else "repository push permission is unproven",
            evidence=(auth, permissions),
            observed_capabilities=(
                "create_branch",
                "push_branch",
                "create_draft_pr",
                "update_draft_pr",
            )
            if ready
            else (),
        )

    def invoke(self, request: DriverExecutionRequest) -> DriverInvocation:
        contract = request.contract
        actions = list(contract.get("requested_actions") or [])
        if len(actions) != 1:
            raise ValueError("exactly one GitHub remote action is required")
        action = actions[0]
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
        elif action in {"create_draft_pr", "update_draft_pr"}:
            module = load_module(Path(__file__).with_name("pull_request.py"), "pes_remote_pr")
            result = (
                module.create_draft(self.transport, contract)
                if action == "create_draft_pr"
                else module.update_draft(self.transport, contract)
            )
        else:
            raise ValueError(f"unsupported GitHub action: {action}")
        return DriverInvocation(
            status="PASS",
            payload={"action": action, "result": result or {}},
            evidence=({"type": "github_remote_action", "action": action},),
        )

    def poll(self, request, state) -> DriverInvocation:
        return DriverInvocation(status="UNSUPPORTED", state=state)

    def cancel(self, request, state) -> DriverInvocation:
        return DriverInvocation(status="UNSUPPORTED", state=state)


PROVIDER_CLASS = GitHubRemoteActionsDriver

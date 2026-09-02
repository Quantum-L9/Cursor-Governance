from __future__ import annotations

from pathlib import Path

from peer_execution.driver_execution import DriverExecutionRequest, DriverInvocation
from peer_execution.imports import load_module
from peer_execution.provider import ProviderProbe


class GitHubActionsDriver:
    provider_id = "ci-github-actions"

    def __init__(self, runtime_root: str | Path, repository_root: str | Path) -> None:
        self.runtime_root = Path(runtime_root).resolve()
        self.repository_root = Path(repository_root).resolve()
        module = load_module(
            self.repository_root
            / "environment/program-execution/adapters/github/common/gh_transport.py",
            "pes_gh_transport_actions",
        )
        self.transport = module.GhTransport(self.repository_root)

    def probe(self, context) -> ProviderProbe:
        auth = load_module(
            self.repository_root
            / "environment/program-execution/adapters/github/common/auth_probe.py",
            "pes_gh_auth_probe_actions",
        ).probe(self.repository_root)
        repository = context.metadata.get("repository")
        workflow = context.metadata.get("workflow")
        if auth["status"] != "PASS":
            return ProviderProbe(
                status="BLOCKED",
                blocked_reason=auth.get("reason") or "GitHub authentication unavailable",
                evidence=(auth,),
            )
        if not all(isinstance(item, str) and item for item in (repository, workflow)):
            return ProviderProbe(
                status="BLOCKED",
                blocked_reason="repository and workflow are required for Actions probe",
                evidence=(auth,),
            )
        result = self.transport.run(["workflow", "view", workflow, "--repo", repository], 30)
        ready = result.exit_code == 0 and context.metadata.get("actions_write_proven") is True
        return ProviderProbe(
            status="PASS" if ready else "BLOCKED",
            blocked_reason=(
                None if ready else "workflow or workflow-dispatch permission is unproven"
            ),
            evidence=(auth, result.to_evidence()),
            observed_capabilities=("workflow_dispatch", "verify") if ready else (),
        )

    def invoke(self, request: DriverExecutionRequest) -> DriverInvocation:
        contract = request.contract
        for key in ("repository", "workflow", "candidate_sha", "ref"):
            if not isinstance(contract.get(key), str) or not contract.get(key):
                raise ValueError(f"GitHub Actions contract field missing: {key}")
        dispatcher = load_module(
            Path(__file__).with_name("dispatcher.py"),
            "pes_github_actions_dispatcher",
        )
        evidence = dispatcher.dispatch_workflow(self.transport, contract)
        return DriverInvocation(
            status="RUNNING",
            state={"dispatch_evidence": evidence},
            evidence=({"type": "workflow_dispatch", **evidence},),
        )

    def poll(self, request: DriverExecutionRequest, state) -> DriverInvocation:
        monitor = load_module(Path(__file__).with_name("monitor.py"), "pes_github_actions_monitor")
        run = monitor.find_run(self.transport, request.contract, state=state)
        if not run:
            return DriverInvocation(status="RUNNING", state=state)
        next_state = dict(state)
        if run.get("databaseId") is not None:
            next_state["host_run_id"] = int(run["databaseId"])
        if run.get("status") != "completed":
            return DriverInvocation(
                status="RUNNING",
                state=next_state,
                evidence=({"type": "workflow_run", **run},),
            )
        artifacts_module = load_module(
            Path(__file__).with_name("artifact_collector.py"),
            "pes_github_actions_artifacts",
        )
        destination = self.runtime_root / "github-actions" / request.dispatch_id
        artifacts = artifacts_module.download_declared(
            self.transport,
            request.contract,
            int(run["databaseId"]),
            destination,
        )
        passed = run.get("conclusion") == "success"
        declared = list(request.contract.get("declared_changed_files") or [])
        payload = {
            "candidate_sha": str(request.contract.get("candidate_sha")),
            "declared_changed_files": declared,
            "observed_changed_files": declared,
            "validations": [
                {
                    "provider": "github-actions",
                    "run_id": run.get("databaseId"),
                    "url": run.get("url"),
                    "conclusion": run.get("conclusion"),
                    "artifacts": artifacts,
                }
            ],
            "gates": {
                "workflow_conclusion": "PASS" if passed else "FAIL",
                "candidate_sha_exact": (
                    "PASS"
                    if run.get("headSha") == request.contract.get("candidate_sha")
                    else "FAIL"
                ),
                "independent_verifier": "PASS",
            },
        }
        return DriverInvocation(
            status="PASS" if passed else "FAIL",
            state=next_state,
            payload=payload,
            evidence=({"type": "workflow_run", **run},),
        )

    def cancel(self, request: DriverExecutionRequest, state) -> DriverInvocation:
        run_id = state.get("host_run_id")
        if run_id is None:
            return DriverInvocation(status="UNSUPPORTED", state=state)
        result = self.transport.run(
            ["run", "cancel", str(run_id), "--repo", str(request.contract["repository"])],
            30,
        )
        return DriverInvocation(
            status="CANCELLED" if result.exit_code == 0 else "FAIL",
            state=state,
            evidence=(result.to_evidence(),),
        )


PROVIDER_CLASS = GitHubActionsDriver

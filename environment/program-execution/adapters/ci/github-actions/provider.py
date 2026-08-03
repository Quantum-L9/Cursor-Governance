from __future__ import annotations

from pathlib import Path
from typing import Any

from adapters.common.base import BaseExecutionAdapter
from adapters.common.imports import load_module


class GitHubActionsVerifier(BaseExecutionAdapter):
    adapter_id = "ci-github-actions"
    capabilities = ("workflow_dispatch", "verify")
    cancellation = "conditional"

    def __init__(self, runtime_root: str | Path, repository_root: str | Path) -> None:
        super().__init__(runtime_root)
        self.repository_root = Path(repository_root).resolve()
        module = load_module(
            self.repository_root
            / "environment/program-execution/adapters/github/common/gh_transport.py",
            "pes_gh_transport_actions",
        )
        self.transport = module.GhTransport(self.repository_root)

    def _probe_status(self, context):
        module = load_module(
            self.repository_root
            / "environment/program-execution/adapters/github/common/auth_probe.py",
            "pes_gh_auth_probe_actions",
        )
        authentication = module.probe(self.repository_root)
        repository = context.metadata.get("repository")
        workflow = context.metadata.get("workflow")
        if authentication["status"] != "PASS":
            return "BLOCKED", authentication.get("reason"), [authentication]
        if not all(isinstance(item, str) and item for item in (repository, workflow)):
            return (
                "BLOCKED",
                "repository and workflow are required for Actions probe",
                [authentication],
            )
        result = self.transport.run(
            ["workflow", "view", workflow, "--repo", repository],
            30,
        )
        workflow_exists = result.exit_code == 0
        write_proven = context.metadata.get("actions_write_proven") is True
        status = "PASS" if workflow_exists and write_proven else "BLOCKED"
        reason = None
        if not workflow_exists:
            reason = "declared workflow is absent or inaccessible"
        elif not write_proven:
            reason = "Actions workflow-dispatch permission is unproven"
        evidence = [authentication, result.to_evidence()]
        return status, reason, evidence

    def _dispatch_record(self, record: dict[str, Any]):
        contract = record["contract"]
        required = {"repository", "workflow", "candidate_sha"}
        missing = sorted(required - set(contract))
        if missing:
            raise ValueError(f"GitHub Actions contract fields missing: {missing}")
        dispatcher = load_module(
            Path(__file__).with_name("dispatcher.py"),
            "pes_github_actions_dispatcher",
        )
        evidence = dispatcher.dispatch_workflow(self.transport, contract)
        return "RUNNING", [{"type": "workflow_dispatch", **evidence}]

    def status(self, dispatch_id: str):
        record = self.runtime.load(dispatch_id)
        monitor = load_module(
            Path(__file__).with_name("monitor.py"),
            "pes_github_actions_monitor",
        )
        run = monitor.find_run(self.transport, record["contract"])
        if run and run.get("status") == "completed":
            artifacts_module = load_module(
                Path(__file__).with_name("artifact_collector.py"),
                "pes_github_actions_artifacts",
            )
            destination = Path(self.runtime.root) / "github-actions" / dispatch_id
            artifacts = artifacts_module.download_declared(
                self.transport,
                record["contract"],
                int(run["databaseId"]),
                destination,
            )
            mapper = load_module(
                Path(__file__).with_name("receipt_mapper.py"),
                "pes_github_actions_receipt_mapper",
            )
            record["host_run_id"] = int(run["databaseId"])
            record["result"] = mapper.map_run(record["contract"], run, artifacts)
            record["status"] = "PASS" if run.get("conclusion") == "success" else "FAIL"
            record["evidence"] = [{"type": "workflow_run", **run}]
            self.runtime.save(dispatch_id, record)
        return super().status(dispatch_id)

    def cancel(self, dispatch_id: str):
        from adapters.common.contracts import validate_contract
        from adapters.common.errors import CanonicalErrorCode

        record = self.runtime.load(dispatch_id)
        binding = validate_contract(record["contract"])
        run_id = record.get("host_run_id")
        if run_id is None:
            return self._append(
                phase="cancel",
                binding=binding,
                status="UNSUPPORTED",
                dispatch_id=dispatch_id,
                canonical_error_code=(CanonicalErrorCode.CANCELLATION_UNSUPPORTED.value),
                adapter_error_code="GITHUB_RUN_ID_UNAVAILABLE",
            )
        result = self.transport.run(
            [
                "run",
                "cancel",
                str(run_id),
                "--repo",
                str(record["contract"]["repository"]),
            ]
        )
        status = "CANCELLED" if result.exit_code == 0 else "FAIL"
        if status == "CANCELLED":
            record["status"] = status
            self.runtime.save(dispatch_id, record)
        return self._append(
            phase="cancel",
            binding=binding,
            status=status,
            dispatch_id=dispatch_id,
            evidence=[result.to_evidence()],
            canonical_error_code=(
                None if status == "CANCELLED" else CanonicalErrorCode.VALIDATION_FAILURE.value
            ),
        )

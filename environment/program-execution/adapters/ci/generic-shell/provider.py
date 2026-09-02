from __future__ import annotations

from pathlib import Path

from peer_execution.driver_execution import DriverExecutionRequest, DriverInvocation
from peer_execution.imports import load_module
from peer_execution.provider import ProviderProbe
from peer_execution.subprocess_runner import run_argv


class GenericShellDriver:
    provider_id = "ci-generic-shell"

    def probe(self, context) -> ProviderProbe:
        return ProviderProbe(
            status="PASS",
            evidence=({"type": "generic_shell", "available": True},),
            observed_capabilities=("verify",),
        )

    def invoke(self, request: DriverExecutionRequest) -> DriverInvocation:
        contract = request.contract
        candidate_value = contract.get("candidate_directory") or contract.get("worktree")
        if not isinstance(candidate_value, str) or not candidate_value:
            raise ValueError("verification candidate directory is required")
        candidate = Path(candidate_value).expanduser().resolve()
        if not candidate.is_dir():
            raise ValueError("verification candidate directory does not exist")
        commands = contract.get("verification_commands") or contract.get("validation_commands")
        if not isinstance(commands, list) or not commands:
            raise ValueError("verification commands are required")
        collector = load_module(
            Path(__file__).with_name("evidence_collector.py"),
            "pes_generic_shell_evidence_collector",
        )
        before = collector.candidate_snapshot(candidate)
        validations = []
        for command in commands:
            if (
                not isinstance(command, list)
                or not command
                or not all(isinstance(item, str) and item for item in command)
            ):
                raise ValueError("verification commands must be non-empty argv arrays")
            result = run_argv(
                command,
                cwd=candidate,
                timeout_seconds=request.timeout_seconds,
                environment={"PYTHONDONTWRITEBYTECODE": "1"},
            )
            validations.append(collector.validation_evidence(command, result))
        after = collector.candidate_snapshot(candidate)
        mutation_free = before["digest"] == after["digest"]
        declared = list(
            contract.get("declared_changed_files") or contract.get("changed_files") or []
        )
        # `observed_changed_files` is an OBSERVATION the caller supplies. It
        # used to default to the declaration (and `[]`, "nothing changed", is
        # falsy and defaulted too), so the exactness gate could only pass.
        observed_raw = contract.get("observed_changed_files")
        observation_available = isinstance(observed_raw, list)
        observed = [str(item) for item in observed_raw] if observation_available else []
        gates = {
            "command_execution": (
                "PASS"
                if validations and all(item["status"] == "PASS" for item in validations)
                else "FAIL"
            ),
            "changed_files_exact": (
                "PASS" if observation_available and declared == observed else "FAIL"
            ),
            "candidate_immutable": "PASS" if mutation_free else "FAIL",
            "independent_verifier": "PASS",
        }
        payload = {
            "candidate_sha": contract.get("candidate_sha"),
            "declared_changed_files": declared,
            "observed_changed_files": observed,
            "validations": validations,
            "gates": gates,
        }
        passed = all(value == "PASS" for value in gates.values())
        return DriverInvocation(
            status="PASS" if passed else "FAIL",
            payload=payload,
            evidence=(
                {
                    "type": "verification_results",
                    "candidate_before": before["digest"],
                    "candidate_after": after["digest"],
                },
            ),
        )

    def poll(self, request, state) -> DriverInvocation:
        return DriverInvocation(status="UNSUPPORTED", state=state)

    def cancel(self, request, state) -> DriverInvocation:
        return DriverInvocation(status="UNSUPPORTED", state=state)


PROVIDER_CLASS = GenericShellDriver

from __future__ import annotations

from pathlib import Path
from typing import Any

from adapters.common.base import BaseExecutionAdapter
from adapters.common.imports import load_module
from adapters.common.subprocess_runner import run_argv


class GenericShellVerifier(BaseExecutionAdapter):
    adapter_id = "ci-generic-shell"
    capabilities = ("verify",)
    cancellation = "unsupported"

    def _dispatch_record(self, record: dict[str, Any]):
        contract = record["contract"]
        candidate_value = contract.get("candidate_directory") or contract.get("worktree")
        candidate = Path(str(candidate_value)).resolve()
        commands = (
            contract.get("verification_commands") or contract.get("validation_commands") or []
        )
        validations = []
        collector = load_module(
            Path(__file__).with_name("evidence_collector.py"),
            "pes_generic_shell_evidence_collector",
        )
        before = collector.candidate_snapshot(candidate)
        for command in commands:
            valid_argv = isinstance(command, list) and all(
                isinstance(item, str) for item in command
            )
            if not valid_argv:
                raise ValueError("verification commands must be argv arrays")
            result = run_argv(
                command,
                cwd=candidate,
                timeout_seconds=int(contract.get("timeout_seconds") or 900),
                environment={"PYTHONDONTWRITEBYTECODE": "1"},
            )
            validations.append(collector.validation_evidence(command, result))
        after = collector.candidate_snapshot(candidate)
        if before["digest"] != after["digest"]:
            validations.append(
                {
                    "command": "candidate-mutation-check",
                    "status": "FAIL",
                    "exit_code": None,
                    "evidence": str(after["digest"]),
                    "before": before,
                    "after": after,
                }
            )
        mapper = load_module(
            Path(__file__).with_name("receipt_mapper.py"),
            "pes_generic_shell_receipt_mapper",
        )
        record["result"] = mapper.map_results(contract, validations)
        all_passed = validations and all(item["status"] == "PASS" for item in validations)
        status = "PASS" if all_passed else "FAIL"
        return status, [
            {
                "type": "verification_results",
                "validations": validations,
                "candidate_before": before["digest"],
                "candidate_after": after["digest"],
            }
        ]

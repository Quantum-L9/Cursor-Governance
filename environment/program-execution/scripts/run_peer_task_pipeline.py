#!/usr/bin/env python3
"""Drive one Controller-admitted task through a bound thin provider and verification.

This is an operator facade, not a scheduler. Every Program-state transition is
performed by the canonical Program Execution Controller CLI.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

PE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PE_ROOT.parents[1]
_CONTROLLER_COMMAND_TIMEOUT_SECONDS = 300
if str(PE_ROOT) not in sys.path:
    sys.path.insert(0, str(PE_ROOT))

from peer_execution.bindings import resolve_peer_binding  # noqa: E402
from peer_execution.models import ProbeContext  # noqa: E402
from peer_execution.runner import run_to_terminal  # noqa: E402

from scripts.provider_loader import instantiate  # noqa: E402


def _run_json(argv: list[str], *, cwd: Path) -> dict[str, Any]:
    try:
        result = subprocess.run(
            argv,
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
            timeout=_CONTROLLER_COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            "controller command timed out after "
            f"{_CONTROLLER_COMMAND_TIMEOUT_SECONDS}s: {' '.join(argv)}"
        ) from exc
    if result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(argv)}\n"
            f"stdout={result.stdout[-4000:]}\nstderr={result.stderr[-4000:]}"
        )
    value = json.loads(result.stdout)
    if not isinstance(value, dict):
        raise ValueError(f"command did not return a JSON object: {' '.join(argv)}")
    return value


def _pec(workspace: Path, *args: str) -> dict[str, Any]:
    entrypoint = PE_ROOT / "core/program-execution-controller-template/scripts/pec.py"
    return _run_json(
        [sys.executable, str(entrypoint), *args, "--workspace", str(workspace)],
        cwd=REPO_ROOT,
    )


def _load_contract(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("rendered contract must be a JSON object")
    return value


def _resolve_provider(
    *,
    workspace: Path,
    agent_ref: str,
    surface: str,
    provider_ref: str | None,
) -> tuple[Any, Any, Path]:
    binding = resolve_peer_binding(REPO_ROOT, agent_ref, surface, provider_ref)
    runtime = workspace / "runtime" / "peer-execution"
    adapter = instantiate(
        binding.provider_ref,
        runtime,
        execution_profile_ref=binding.execution_profile_ref,
        binding_context=binding.to_dict(),
    )
    return binding, adapter, runtime


def _probe_provider(
    *,
    binding: Any,
    adapter: Any,
    runtime: Path,
    program_digest: str,
    requested_capabilities: tuple[str, ...] = (),
) -> Any:
    return adapter.probe(
        ProbeContext(
            repository_root=str(REPO_ROOT),
            runtime_root=str(runtime),
            program_lock_digest=program_digest,
            requested_capabilities=requested_capabilities,
            metadata=binding.to_dict(),
        )
    )


def _preflight_digest(task_id: str, binding: Any) -> str:
    payload = (
        f"peer-execution-preflight:{task_id}:{binding.agent_ref}:"
        f"{binding.surface}:{binding.provider_ref}"
    )
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _execute_provider(
    *,
    contract: dict[str, Any],
    binding: Any,
    adapter: Any,
    probe: Any,
) -> dict[str, Any]:
    if probe.status != "PASS":
        return {
            "status": "BLOCKED",
            "binding": binding.to_dict(),
            "probe": probe.to_dict(),
        }
    prepared = adapter.prepare(contract)
    dispatched = adapter.dispatch({"dispatch_id": prepared.dispatch_id})
    dispatch_id = str(prepared.dispatch_id)
    outcome = run_to_terminal(adapter, dispatch_id, dispatched.status)
    if outcome.status != "PASS":
        return {
            "status": outcome.status,
            "reason": "peer_execution_timeout" if outcome.timed_out else None,
            "binding": binding.to_dict(),
            "probe": probe.to_dict(),
            "prepare": prepared.to_dict(),
            "dispatch": dispatched.to_dict(),
            **outcome.to_dict(),
        }
    result = adapter.collect(dispatch_id)
    return {
        "status": "PASS",
        "binding": binding.to_dict(),
        "probe": probe.to_dict(),
        "prepare": prepared.to_dict(),
        "dispatch": dispatched.to_dict(),
        **outcome.to_dict(),
        "terminal_result": dict(result),
    }


def _failed_execution_status(provider_status: object) -> str:
    return "BLOCKED" if provider_status == "BLOCKED" else "FAILED_EXECUTION"


def _abort_controller(workspace: Path, task_id: str, actor: str, reason: str) -> dict[str, Any]:
    return {
        "status": "ABORT_NOT_REGISTERED",
        "task_id": task_id,
        "actor": actor,
        "reason": reason,
        "workspace": str(workspace),
        "note": (
            "pec abort-execution is not a controller command; "
            "make campaign execute uses pec via run_campaign only"
        ),
    }


def execute(args: argparse.Namespace) -> dict[str, Any]:
    workspace = args.workspace.expanduser().resolve()
    task_id = args.task_id
    binding, adapter, runtime = _resolve_provider(
        workspace=workspace,
        agent_ref=args.agent_ref,
        surface=args.surface,
        provider_ref=args.provider_ref,
    )
    preflight_probe = _probe_provider(
        binding=binding,
        adapter=adapter,
        runtime=runtime,
        program_digest=_preflight_digest(task_id, binding),
    )
    report: dict[str, Any] = {
        "schema": "l9.peer-execution.task-pipeline-receipt.v1",
        "task_id": task_id,
        "controller": {},
        "peer_execution": {
            "status": "BLOCKED" if preflight_probe.status != "PASS" else "PREFLIGHT_READY",
            "binding": binding.to_dict(),
            "preflight_probe": preflight_probe.to_dict(),
        },
        "completion_requested": bool(args.complete),
    }
    if preflight_probe.status != "PASS":
        report["status"] = "BLOCKED_PRE_ADMISSION"
        report["next_action"] = "restore_provider_readiness_before_controller_claim"
        return report

    claim = _pec(
        workspace,
        "claim",
        task_id,
        "--holder",
        args.holder,
        "--ttl-hours",
        str(args.ttl_hours),
    )
    report["controller"]["claim"] = claim
    try:
        prepared_worktree = _pec(workspace, "prepare", task_id)
        rendered = _pec(workspace, "render-contract", task_id)
        contract = _load_contract(rendered["contract"])
    except Exception as exc:
        report["controller"]["abort"] = _abort_controller(
            workspace, task_id, args.actor, "pre_execution_controller_failure"
        )
        report["status"] = "ERROR_ABORTED"
        report["error_type"] = type(exc).__name__
        report["message"] = str(exc)
        return report
    program_digest = contract.get("program_lock_digest") or contract.get("program_digest")
    if not isinstance(program_digest, str) or not program_digest:
        raise ValueError("rendered contract is missing Program Lock digest")
    requested = contract.get("requested_actions")
    if not isinstance(requested, list) or not all(isinstance(item, str) for item in requested):
        raise ValueError("rendered contract requested_actions must be an array of strings")
    probe = _probe_provider(
        binding=binding,
        adapter=adapter,
        runtime=runtime,
        program_digest=program_digest,
        requested_capabilities=tuple(requested),
    )
    report["controller"].update(
        {
            "prepare": prepared_worktree,
            "render": rendered,
        }
    )
    report["peer_execution"] = {
        "status": "BLOCKED" if probe.status != "PASS" else "READY",
        "binding": binding.to_dict(),
        "preflight_probe": preflight_probe.to_dict(),
        "probe": probe.to_dict(),
    }
    if probe.status != "PASS":
        report["controller"]["abort"] = _abort_controller(
            workspace, task_id, args.actor, "provider_probe_blocked_after_admission"
        )
        report["status"] = "BLOCKED_ABORTED"
        report["next_action"] = "restore_provider_readiness_then_retry"
        return report

    try:
        started = _pec(workspace, "start", task_id, "--actor", args.actor)
    except Exception as exc:
        report["controller"]["abort"] = _abort_controller(
            workspace, task_id, args.actor, "controller_start_failure"
        )
        report["status"] = "ERROR_ABORTED"
        report["error_type"] = type(exc).__name__
        report["message"] = str(exc)
        return report
    report["controller"]["start"] = started
    provider = _execute_provider(
        contract=contract,
        binding=binding,
        adapter=adapter,
        probe=probe,
    )
    report["peer_execution"] = provider
    if provider.get("status") != "PASS":
        report["controller"]["abort"] = _abort_controller(
            workspace, task_id, args.actor, "peer_execution_failure"
        )
        report["status"] = _failed_execution_status(provider.get("status")) + "_ABORTED"
        report["next_action"] = "inspect_recovery_artifact_then_retry"
        return report

    receipt_path = str(contract["attempt_receipt_path"])
    try:
        recorded = _pec(
            workspace,
            "record-attempt",
            task_id,
            "--receipt",
            receipt_path,
        )
        verification = _pec(workspace, "verify", task_id)
    except Exception as exc:
        report["controller"]["abort"] = _abort_controller(
            workspace, task_id, args.actor, "attempt_handoff_or_verification_failure"
        )
        report["status"] = "ERROR_ABORTED"
        report["error_type"] = type(exc).__name__
        report["message"] = str(exc)
        return report
    report["controller"]["record_attempt"] = recorded
    report["controller"]["verification"] = verification
    if verification.get("verdict") != "PASSED_LOCAL":
        report["controller"]["abort"] = _abort_controller(
            workspace, task_id, args.actor, "controller_verification_failed"
        )
        report["status"] = "FAILED_VERIFICATION_ABORTED"
        report["next_action"] = "inspect_verification_and_recovery_artifacts"
        return report
    report["status"] = "PASSED_LOCAL"
    report["next_action"] = "controller_completion_or_next_program_gate"
    if args.complete:
        completed = _pec(
            workspace,
            "complete",
            task_id,
            "--actor",
            args.actor,
            "--evidence-id",
            str(verification["evidence_id"]),
        )
        report["controller"]["complete"] = completed
        report["status"] = str(completed.get("status") or "COMPLETED")
        report["next_action"] = "controller_next"
    return report


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("task_id")
    value.add_argument("--workspace", required=True, type=Path)
    value.add_argument("--agent-ref", required=True)
    value.add_argument("--surface", required=True)
    value.add_argument("--provider-ref")
    value.add_argument("--holder", default="peer-execution-runner")
    value.add_argument("--actor", default="peer-execution-runner")
    value.add_argument("--ttl-hours", type=_positive_int, default=8)
    value.add_argument("--complete", action="store_true")
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        report = execute(args)
    except Exception as exc:
        report = {
            "schema": "l9.peer-execution.task-pipeline-receipt.v1",
            "status": "ERROR",
            "task_id": getattr(args, "task_id", None),
            "workspace": str(args.workspace) if getattr(args, "workspace", None) else None,
            "error_type": type(exc).__name__,
            "message": str(exc),
        }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("status") in {"PASSED_LOCAL", "COMPLETED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

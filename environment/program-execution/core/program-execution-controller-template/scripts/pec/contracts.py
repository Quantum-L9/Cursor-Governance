from __future__ import annotations

import fnmatch
import re
from pathlib import Path, PurePosixPath
from typing import Any

from .common import digest_object, load_json, write_json
from .ledger import EventLedger
from .state import StateDB

ACTIONS = {
    "inspect",
    "local_write",
    "commit",
    "push",
    "pull_request",
    "merge",
    "publish_or_release",
    "deploy_or_migrate",
    "destructive_change",
    "external_message",
}
RISK_ORDER = {"T0": 0, "T1": 1, "T2": 2, "T3": 3, "T4": 4}


class ContractError(RuntimeError):
    pass


def normalize_repo_path(value: Any, *, allow_glob: bool = True) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError("repository path must be a non-empty string")
    raw = value.strip().replace("\\", "/")
    if raw.startswith("/") or re.match(r"^[A-Za-z]:/", raw):
        raise ContractError(f"absolute path forbidden: {value}")
    if raw.startswith("~") or "\x00" in raw:
        raise ContractError(f"unsafe path forbidden: {value}")
    parts = [part for part in raw.split("/") if part not in {"", "."}]
    if ".." in parts:
        raise ContractError(f"path traversal forbidden: {value}")
    if not parts:
        raise ContractError("empty repository path")
    if parts[0] in {
        ".git",
        ".program-controller",
        ".pec",
        "runtime",
        "ledger",
        "receipts",
        "contracts",
    }:
        raise ContractError(f"controller or git internals forbidden: {value}")
    normalized = "/".join(parts)
    if not allow_glob and any(ch in normalized for ch in "*?["):
        raise ContractError(f"glob forbidden here: {value}")
    return normalized


def path_allowed(path: str, patterns: list[str]) -> bool:
    normalized = normalize_repo_path(path, allow_glob=False)
    for raw in patterns:
        directory_scope = isinstance(raw, str) and raw.strip().replace("\\", "/").endswith("/")
        pattern = normalize_repo_path(raw, allow_glob=True)
        if directory_scope and (normalized == pattern or normalized.startswith(pattern + "/")):
            return True
        if fnmatch.fnmatchcase(normalized, pattern) or PurePosixPath(normalized).match(pattern):
            return True
    return False


def validate_source_contract(contract: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    required = {
        "schema",
        "task_id",
        "target_id",
        "repository_id",
        "objective",
        "requested_actions",
        "acceptance_obligation_ids",
        "writable_paths",
        "validation_commands",
        "required_gate_ids",
        "required_evidence_ids",
        "risk_tier",
        "remote_mutation",
        "stop_conditions",
        "rollback",
    }
    allowed = required | {"kernel_profile", "consumers", "entrypoints"}
    missing = sorted(required - set(contract))
    unknown = sorted(set(contract) - allowed)
    if missing:
        raise ContractError(f"missing source-contract fields: {missing}")
    if unknown:
        raise ContractError(f"unsupported source-contract fields: {unknown}")
    if contract["schema"] != "program-execution-controller.source-contract.v2":
        raise ContractError("unsupported source-contract schema")
    if contract["task_id"] != task["id"]:
        raise ContractError("task ID mismatch")
    if contract["target_id"] != task["target_id"]:
        raise ContractError("target ID mismatch")
    if contract["repository_id"] != task.get("repository_id"):
        raise ContractError("repository ID mismatch")
    if task["execution_kind"] != "repo_local":
        raise ContractError("repository Source Contracts are only valid for repo_local tasks")
    if contract["remote_mutation"] != "denied":
        raise ContractError("remote mutation must be denied in the universal Controller core")
    actions = contract.get("requested_actions") or []
    if not actions or not set(actions) <= ACTIONS:
        raise ContractError("requested_actions contains unsupported values")
    ceiling = task.get("authorization_ceiling") or {}
    inflated = sorted(action for action in actions if not ceiling.get(action, False))
    if inflated:
        raise ContractError(f"Source Contract widens Blueprint authorization ceiling: {inflated}")
    if RISK_ORDER.get(contract["risk_tier"], -1) < RISK_ORDER.get(task["risk_tier"], -1):
        raise ContractError("Source Contract risk tier may not downgrade the Blueprint task risk")
    writable = [normalize_repo_path(value) for value in contract.get("writable_paths") or []]
    if "local_write" in actions and not writable:
        raise ContractError("local_write requires non-empty writable_paths")
    commands = contract.get("validation_commands") or []
    if not all(isinstance(command, str) and command.strip() for command in commands):
        raise ContractError("validation commands must be non-empty strings")
    required_commands = set(task.get("required_validation_commands") or [])
    if not required_commands <= set(commands):
        raise ContractError(
            f"Source Contract omits Blueprint validation commands: {sorted(required_commands - set(commands))}"  # noqa: E501
        )
    if not set(task.get("required_acceptance") or []) <= set(
        contract.get("acceptance_obligation_ids") or []
    ):
        raise ContractError("Source Contract omits Blueprint acceptance obligations")
    if not set(task.get("completion_gates") or []) <= set(contract.get("required_gate_ids") or []):
        raise ContractError("Source Contract omits Blueprint completion gates")
    if not set(task.get("required_evidence") or []) <= set(
        contract.get("required_evidence_ids") or []
    ):
        raise ContractError("Source Contract omits Blueprint evidence obligations")
    if not contract.get("stop_conditions") or not contract.get("rollback"):
        raise ContractError("stop_conditions and rollback are required")
    rollback = contract.get("rollback")
    if isinstance(rollback, str) and "REPLACE_WITH" in rollback:
        raise ContractError("rollback placeholder REPLACE_WITH is forbidden")
    return {
        **contract,
        "requested_actions": sorted(set(actions)),
        "writable_paths": sorted(set(writable)),
        "validation_commands": list(dict.fromkeys(commands)),
    }


def _task_source_from_lock(workspace: Path, task_id: str) -> dict[str, Any]:
    lock_path = workspace / "runtime" / "program-lock.json"
    lock = load_json(lock_path)
    for item in lock.get("tasks") or []:
        if item.get("id") == task_id:
            source = item.get("source")
            return source if isinstance(source, dict) else {}
    return {}


def draft_source_contract(
    db: StateDB, task_id: str, output: Path, *, workspace: Path | None = None
) -> Path:
    task = db.task(task_id)
    if task is None:
        raise ContractError(f"unknown task: {task_id}")
    if task["execution_kind"] != "repo_local" or not task.get("repository_id"):
        raise ContractError("task does not use a repository Source Contract")
    source = _task_source_from_lock(workspace, task_id) if workspace is not None else {}
    rollback = str((source.get("rollback") or {}).get("strategy") or "").strip()
    if not rollback or "REPLACE_WITH" in rollback:
        raise ContractError(
            "DEFINITION_INVALID: source.rollback.strategy missing or contains REPLACE_WITH"
        )
    writable = [
        str(item.get("location"))
        for item in (source.get("outputs") or [])
        if isinstance(item, dict) and item.get("location")
    ]
    requested = [
        action
        for action, allowed in task["authorization_ceiling"].items()
        if allowed and action in {"inspect", "local_write"}
    ]
    payload = {
        "schema": "program-execution-controller.source-contract.v2",
        "task_id": task_id,
        "target_id": task["target_id"],
        "repository_id": task["repository_id"],
        "objective": task["objective"],
        "requested_actions": requested or ["inspect"],
        "acceptance_obligation_ids": task["required_acceptance"],
        "writable_paths": writable,
        "validation_commands": task["required_validation_commands"],
        "required_gate_ids": task["completion_gates"],
        "required_evidence_ids": task["required_evidence"],
        "risk_tier": task["risk_tier"],
        "remote_mutation": "denied",
        "stop_conditions": ["stop_on_program_contract_scope_authority_or_base_state_drift"],
        "rollback": rollback,
        "kernel_profile": str(
            source.get("kernel_profile") or task.get("kernel_profile") or "BUILD"
        ),
    }
    payload = validate_source_contract(payload, task)
    write_json(output, payload)
    return output


def register_source_contract(
    db: StateDB,
    ledger: EventLedger,
    workspace: Path,
    task_id: str,
    source: Path,
    actor: str,
    replace: bool = False,
) -> dict[str, Any]:
    task = db.task(task_id)
    if task is None:
        raise ContractError(f"unknown task: {task_id}")
    contract = validate_source_contract(load_json(source), task)
    target = workspace / "contracts" / "source" / f"{task_id}.json"
    if target.exists() and not replace:
        raise ContractError("Source Contract already exists; explicit replacement is required")
    write_json(target, contract)
    digest = digest_object(contract)
    db.update_task(
        task_id,
        source_contract_path=str(target),
        source_contract_digest=digest,
        scope_status="exact",
    )
    ledger.append(
        "SOURCE_CONTRACT_REGISTERED",
        actor,
        {"task_id": task_id, "path": str(target), "digest": digest, "replaced": bool(replace)},
    )
    return {"status": "REGISTERED", "task_id": task_id, "path": str(target), "digest": digest}


def render_contract(
    db: StateDB, ledger: EventLedger, workspace: Path, task_id: str
) -> dict[str, Any]:
    task = db.task(task_id)
    if task is None:
        raise ContractError(f"unknown task: {task_id}")
    lease = db.active_lease_for_task(task_id)
    if lease is None:
        raise ContractError("active lease required")
    if task["runtime_state"] != "PREPARED":
        raise ContractError(
            f"task must be PREPARED before rendering, found {task['runtime_state']}"
        )
    if not task.get("source_contract_path"):
        raise ContractError("registered Source Contract required")
    source = load_json(Path(task["source_contract_path"]))
    source = validate_source_contract(source, task)
    if digest_object(source) != task["source_contract_digest"]:
        raise ContractError("Source Contract digest mismatch")
    program_digest = db.get_meta("program_digest")
    attempt_number = db.next_attempt_number(task_id)
    receipt_path = (
        workspace / "attempts" / task_id / f"attempt-{attempt_number:03d}" / "attempt-receipt.json"
    )
    rendered = {
        **source,
        "schema": "program-execution-controller.rendered-contract.v2",
        "program_digest": program_digest,
        "source_contract_digest": task["source_contract_digest"],
        "base_sha": lease["base_sha"],
        "branch": lease["branch"],
        "worktree": lease["worktree"],
        "lease_id": lease["lease_id"],
        "attempt_number": attempt_number,
        "attempt_receipt_path": str(receipt_path),
    }
    # Fresh attempt contracts are rendered from current durable typed state, so
    # each new attempt carries the active plan revision and any active Replan
    # Revision. Conversational history is never an input to rendering.
    from .replan import current_plan_revision

    plan = current_plan_revision(workspace)
    rendered["plan_revision"] = plan["plan_revision"]
    rendered["active_replan_revision_id"] = plan.get("active_replan_revision_id")
    rendered["contract_digest"] = digest_object(rendered)
    target = workspace / "contracts" / "rendered" / f"{task_id}.json"
    write_json(target, rendered)
    brief = workspace / "contracts" / "rendered" / f"{task_id}.WORKER_BRIEF.md"
    brief.write_text(
        "\n".join(
            [
                f"# Worker Brief: {task_id}",
                "",
                f"Objective: {rendered['objective']}",
                "",
                f"kernel_profile: {rendered.get('kernel_profile') or 'BUILD'}",
                "",
                f"Target: `{rendered['target_id']}` / `{rendered['repository_id']}`",
                f"Worktree: `{rendered['worktree']}`",
                f"Base SHA: `{rendered['base_sha']}`",
                f"Program digest: `{rendered['program_digest']}`",
                f"Contract digest: `{rendered['contract_digest']}`",
                "",
                "Allowed actions:",
                *[f"- `{action}`" for action in rendered["requested_actions"]],
                "",
                "Writable paths:",
                *[f"- `{path}`" for path in rendered["writable_paths"]],
                "",
                "Validation commands:",
                *[f"- `{command}`" for command in rendered["validation_commands"]],
                "",
                "Stop immediately on any program, contract, scope, authorization, lease, or base-state drift.",  # noqa: E501
                "Do not use remote credentials or claim independent verification.",
                f"Write the Attempt Receipt to `{rendered['attempt_receipt_path']}`.",
                "",
                (
                    "Worktree contract: leave changes dirty (uncommitted) OR commit them on "
                    + "this task branch — verification covers both. Declare EVERY touched path "
                    + "in `changed_files` exactly; commits happen later at campaign integration, "
                    + "not inside this task."
                ),
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    forbidden = (
        "AUDIT.md",
        "PLAN.md",
        "BUILD.md",
        "CHANGE.md",
        "VALIDATION.md",
        "DEFINITION_OF_DONE.md",
        "RELEASE.md",
    )
    brief_text = brief.read_text(encoding="utf-8")
    hit = [name for name in forbidden if name in brief_text]
    if hit:
        raise ContractError(f"worker brief names kernel files {hit}; ADR-0024 forbids that")
    db.update_task(
        task_id,
        rendered_contract_path=str(target),
        rendered_contract_digest=rendered["contract_digest"],
    )
    db.transition_task(task_id, "CONTRACTED")
    db.update_lease(lease["lease_id"], contract_digest=rendered["contract_digest"])
    ledger.append(
        "CONTRACT_RENDERED",
        "controller",
        {
            "task_id": task_id,
            "path": str(target),
            "digest": rendered["contract_digest"],
            "lease_id": lease["lease_id"],
        },
    )
    return {
        "task_id": task_id,
        "contract": str(target),
        "worker_brief": str(brief),
        "contract_digest": rendered["contract_digest"],
    }

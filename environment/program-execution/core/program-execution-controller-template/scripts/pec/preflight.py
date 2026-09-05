"""Compose validate_runtime + task_readiness + receipt/lock into next_action."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

from .common import load_json
from .controller import open_runtime, task_readiness, validate_runtime

SCHEMA = "program-execution-controller.preflight-receipt.v1"
UNKNOWN = "UNKNOWN"

TOKEN_TO_CODE = {
    "program_lock_stale_or_invalid": "PROGRAM_LOCK_STALE",
    "repository_not_reconciled": "REPOSITORY_STATE_DRIFT",
    "repository_dirty": "REPOSITORY_STATE_DRIFT",
    "source_contract_incomplete": "DEFINITION_INVALID",
    "source_contract_invalid": "DEFINITION_INVALID",
    "runtime_receipt_missing": "REVISION_MISMATCH",
    "runtime_receipt_not_ready": "REVISION_MISMATCH",
    "runtime_receipt_unknown_revision": "REVISION_MISMATCH",
    "lock_identity_mismatch": "LOCK_IDENTITY_MISMATCH",
    "writable_paths_missing": "DEFINITION_INVALID",
    "actor_required": "DEFINITION_INVALID",
    "not_prepared": "REPOSITORY_STATE_DRIFT",
    "lease_missing": "LEASE_EXPIRED",
    "task_already_leased": "LEASE_EXPIRED",
}


def _error_code(token: str) -> str:
    if token in TOKEN_TO_CODE:
        return TOKEN_TO_CODE[token]
    prefix = token.split(":", 1)[0]
    return TOKEN_TO_CODE.get(prefix, "DEFINITION_INVALID")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[6]


_RECEIPT_READER_MODULE = "pec_runtime_readiness_receipt"


def _readiness_receipt_reader() -> Any | None:
    """Bind `ops/scripts/write_runtime_readiness_receipt.py` by FILE LOCATION.

    Prepending `ops/scripts` to sys.path exposed every bare module name in that
    directory (dozens of them) at the front of the import path of whichever
    process called preflight. The receipt reader is one file; bind that file.
    None when the file is absent, which callers report as a missing receipt.
    """
    source = _repo_root() / "ops" / "scripts" / "write_runtime_readiness_receipt.py"
    if not source.is_file():
        return None
    existing = sys.modules.get(_RECEIPT_READER_MODULE)
    if (
        existing is not None
        and Path(getattr(existing, "__file__", "")).resolve() == source.resolve()
    ):
        return existing
    spec = importlib.util.spec_from_file_location(_RECEIPT_READER_MODULE, source)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[_RECEIPT_READER_MODULE] = module
    try:
        spec.loader.exec_module(module)
    # BaseException, not Exception: a partially executed module must be
    # unregistered even when the load is interrupted, or the next import
    # silently gets the broken half. The block re-raises.
    except BaseException:
        sys.modules.pop(_RECEIPT_READER_MODULE, None)
        raise
    return module


def _load_receipt(
    surface: str, receipt_workspace: Path
) -> tuple[Path | None, dict[str, Any] | None]:
    reader = _readiness_receipt_reader()
    if reader is None:
        return None, None
    path = reader.receipt_path(surface=surface, workspace=receipt_workspace)
    if not path.is_file():
        return path, None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return path, None
    return path, data if isinstance(data, dict) else None


def _receipt_blockers(receipt: dict[str, Any] | None) -> list[str]:
    if receipt is None:
        return ["runtime_receipt_missing"]
    status = str(receipt.get("overall_status") or "")
    if status == "NOT_READY":
        return ["runtime_receipt_not_ready"]
    for field in ("governance_revision", "runtime_script_revision"):
        if str(receipt.get(field) or UNKNOWN) == UNKNOWN:
            return ["runtime_receipt_unknown_revision"]
    return []


def _lock_blockers() -> list[str]:
    claude = os.environ.get("CLAUDE_PROJECT_DIR", "").strip()
    cursor = os.environ.get("CURSOR_PROJECT_DIR", "").strip()
    if claude and cursor and Path(claude).resolve() != Path(cursor).resolve():
        return ["lock_identity_mismatch"]
    return []


#: What `next_action` names when the runtime does not know it. A caller must
#: supply these; preflight never invents a holder, an actor or a repository.
ACTOR_INPUT = "<actor>"
TASK_INPUT = "<task-id>"
REPOSITORY_INPUT = "<repository-id>=<path>"


def _actor_hint() -> str | None:
    for name in ("L9_MEMORY_AGENT_ID", "PEC_ACTOR"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return None


def _with_required_inputs(action: dict[str, Any]) -> dict[str, Any]:
    required = sorted(
        {item for item in action["args"] if item in {ACTOR_INPUT, TASK_INPUT, REPOSITORY_INPUT}}
    )
    if required:
        action["required_inputs"] = required
    return action


def _next_action(
    token: str | None,
    *,
    workspace: Path,
    task_id: str | None,
    receipt_workspace: Path,
    surface: str,
    repository_ids: list[str] | None = None,
) -> dict[str, Any]:
    return _with_required_inputs(
        _next_action_template(
            token,
            workspace=workspace,
            task_id=task_id,
            receipt_workspace=receipt_workspace,
            surface=surface,
            repository_ids=repository_ids or [],
        )
    )


def _next_action_template(
    token: str | None,
    *,
    workspace: Path,
    task_id: str | None,
    receipt_workspace: Path,
    surface: str,
    repository_ids: list[str],
) -> dict[str, Any]:
    ws = str(workspace)
    # `TASK-001` used to stand in for an unknown task; a next action against a
    # task the runtime never named is an invented instruction.
    tid = task_id or TASK_INPUT
    actor = _actor_hint() or ACTOR_INPUT
    if token in {
        "runtime_receipt_missing",
        "runtime_receipt_not_ready",
        "runtime_receipt_unknown_revision",
    }:
        writer = str(_repo_root() / "ops" / "scripts" / "write_runtime_readiness_receipt.py")
        return {
            "command": "python3",
            "args": [
                writer,
                "--surface",
                surface,
                "--workspace",
                str(receipt_workspace),
            ],
        }
    if token == "lock_identity_mismatch":
        # Repository-write authority no longer comes from a memory lock, so the
        # remedy is to re-hydrate this session, not to acquire one (E7/E8).
        return {
            "command": "python3",
            "args": [
                "environment/agents/adapters/claude-code/hooks/memory_prefetch.py",
                "--session-id",
                os.environ.get("CURSOR_CONVERSATION_ID")
                or os.environ.get("CLAUDE_SESSION_ID")
                or "REQUIRED",
            ],
        }
    if token == "repository_not_reconciled":
        repository = (
            f"{repository_ids[0]}={receipt_workspace}"
            if len(repository_ids) == 1
            else REPOSITORY_INPUT
        )
        return {
            "command": "pec",
            "args": ["reconcile", "--workspace", ws, "--repository", repository],
        }
    if token in {"source_contract_incomplete", "writable_paths_missing"}:
        return {
            "command": "pec",
            "args": [
                "draft-contract",
                tid,
                "--workspace",
                ws,
                "--output",
                str(workspace / "contracts" / "source" / f"{tid}.draft.json"),
            ],
        }
    if token == "lease_missing":
        return {"command": "pec", "args": ["claim", tid, "--workspace", ws, "--holder", actor]}
    if token == "not_prepared":
        return {"command": "pec", "args": ["prepare", tid, "--workspace", ws]}
    if token == "actor_required":
        return {
            "command": "pec",
            "args": ["start", tid, "--workspace", ws, "--actor", actor],
        }
    if token and token.startswith("runtime_state_not_claimable:PREPARED"):
        return {"command": "pec", "args": ["render-contract", tid, "--workspace", ws]}
    if token and token.startswith("runtime_state_not_claimable:CONTRACTED"):
        return {
            "command": "pec",
            "args": ["start", tid, "--workspace", ws, "--actor", actor],
        }
    if token is None:
        return {"command": "pec", "args": ["claim", tid, "--workspace", ws, "--holder", actor]}
    return {"command": "pec", "args": ["status", "--workspace", ws]}


def _extra_task_blockers(db: Any, task: dict[str, Any]) -> list[str]:
    extra: list[str] = []
    state = task.get("runtime_state")
    if state in {"WAITING", "BLOCKED", "ELIGIBLE"} and task.get("scope_status") == "exact":
        if db.active_lease_for_task(task["id"]) is None:
            extra.append("lease_missing")
    if state == "LEASED":
        extra.append("not_prepared")
    if state == "CONTRACTED":
        extra.append("actor_required")
    if task.get("source_contract_path"):
        try:
            contract = load_json(Path(task["source_contract_path"]))
            if "local_write" in (contract.get("requested_actions") or []) and not contract.get(
                "writable_paths"
            ):
                extra.append("writable_paths_missing")
        except (OSError, json.JSONDecodeError, TypeError):
            # Unreadable or invalid source contract must not abort preflight;
            # task_readiness already reports source_contract_invalid when needed.
            pass
    return extra


def preflight(
    workspace: Path,
    *,
    task_id: str | None = None,
    surface: str = "cursor",
    receipt_workspace: Path | None = None,
) -> dict[str, Any]:
    workspace = workspace.resolve()
    receipt_ws = (receipt_workspace or Path.cwd()).resolve()
    receipt_path, receipt = _load_receipt(surface, receipt_ws)
    blockers = [
        {"token": token, "error_code": _error_code(token)} for token in _receipt_blockers(receipt)
    ]
    blockers.extend(
        {"token": token, "error_code": _error_code(token)} for token in _lock_blockers()
    )

    program: dict[str, Any] = {"workspace": str(workspace), "lock_digest": UNKNOWN}
    runtime_validation: dict[str, Any] = {"status": "SKIPPED"}
    task_payload: dict[str, Any] | None = None
    repository_ids: list[str] = []

    mutating_blocked = bool(blockers)
    if not mutating_blocked:
        runtime_validation = validate_runtime(workspace)
        db, _ = open_runtime(workspace)
        try:
            lock_path = workspace / "runtime" / "program-lock.json"
            if lock_path.is_file():
                lock = load_json(lock_path)
                program["lock_digest"] = str(lock.get("lock_digest") or UNKNOWN)
            repository_ids = [str(row["repository_id"]) for row in db.repositories()]
            tasks = [db.task(task_id)] if task_id else db.tasks()
            tasks = [t for t in tasks if t is not None]
            chosen = tasks[0] if tasks else None
            if chosen is not None:
                ready, tokens = task_readiness(db, chosen, workspace)
                tokens = list(tokens) + _extra_task_blockers(db, chosen)
                task_payload = {
                    "id": chosen["id"],
                    "runtime_state": chosen["runtime_state"],
                    "eligible": ready and not tokens,
                    "blockers": tokens,
                }
                for token in tokens:
                    blockers.append({"token": token, "error_code": _error_code(token)})
        finally:
            db.close()

    first = blockers[0]["token"] if blockers else None
    if task_payload and not blockers:
        first = None
    next_action = _next_action(
        first,
        workspace=workspace,
        task_id=(task_payload or {}).get("id") if task_payload else task_id,
        receipt_workspace=receipt_ws,
        surface=surface,
        repository_ids=repository_ids,
    )
    ready = not blockers
    return {
        "schema": SCHEMA,
        "ready": ready,
        "runtime": {
            "path": str(receipt_path) if receipt_path else UNKNOWN,
            "overall_status": (receipt or {}).get("overall_status", UNKNOWN),
        },
        "program": program,
        "task": task_payload,
        "runtime_validation": runtime_validation,
        "blockers": blockers,
        "next_action": next_action,
    }

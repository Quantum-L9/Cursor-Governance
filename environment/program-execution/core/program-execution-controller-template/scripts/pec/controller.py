from __future__ import annotations

import datetime as dt
import importlib.util
import json
import os
import subprocess
import uuid
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .blueprint import BlueprintError, verify_program_lock, write_program_lock
from .common import digest_object, load_json, load_yaml, parse_time, run_git, utc_now, write_json
from .contracts import ContractError, path_allowed, validate_source_contract
from .ledger import EventLedger
from .state import StateDB


class ControllerError(RuntimeError):
    pass


def open_runtime(workspace: Path) -> tuple[StateDB, EventLedger]:
    workspace = workspace.resolve()
    if not (workspace / "runtime" / "state.sqlite").is_file():
        raise ControllerError(f"Controller runtime not bootstrapped: {workspace}")
    return StateDB(workspace / "runtime" / "state.sqlite"), EventLedger(
        workspace / "ledger" / "events.jsonl"
    )


def load_json_or_yaml(path: Path) -> Any:
    return load_json(path) if path.suffix == ".json" else load_yaml(path)


def _runtime_config(workspace: Path) -> dict[str, Any]:
    path = workspace / "config" / "controller.json"
    if not path.is_file():
        raise ControllerError("runtime controller config missing")
    return load_json(path)


def _validate_schema(workspace: Path, schema_name: str, value: Any) -> None:
    config = _runtime_config(workspace)
    schema_path = Path(config["template_root"]) / "schemas" / schema_name
    schema = load_json(schema_path)
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda e: list(e.path))
    if errors:
        messages = [f"{'.'.join(str(p) for p in e.path) or '<root>'}: {e.message}" for e in errors]
        raise ControllerError(f"schema validation failed for {schema_name}: " + "; ".join(messages))


def _validate_blueprint(blueprint: Path, mode: str) -> list[str]:
    path = (
        Path(__file__).resolve().parents[3]
        / "program-execution-blueprint-template"
        / "scripts"
        / "validate_blueprint.py"
    )
    spec = importlib.util.spec_from_file_location("pec_validate_blueprint", path)
    if spec is None or spec.loader is None:
        raise ControllerError(f"cannot load validate_blueprint.py: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return list(module.validate(blueprint, mode))


def _complete_pair(blueprint: Path) -> bool:
    return (blueprint / "MANIFEST.yaml").is_file() and (blueprint / "README.md").is_file()


def _admission_errors(blueprint: Path, *, admission_draft: bool) -> list[str]:
    program = load_yaml(blueprint / "PROGRAM.yaml").get("program") or {}
    status = program.get("definition_status")
    if admission_draft:
        if _complete_pair(blueprint):
            return _validate_blueprint(blueprint, "template")
        return []
    if status != "accepted":
        return [
            "bootstrap requires an accepted Blueprint; "
            f"found definition_status={status}; use --admission-draft"
        ]
    if _complete_pair(blueprint):
        return _validate_blueprint(blueprint, "instantiated")
    return []


def bootstrap(
    workspace: Path,
    blueprint: Path,
    template_root: Path,
    *,
    admission_draft: bool = False,
) -> dict[str, Any]:
    workspace = workspace.resolve()
    blueprint = blueprint.resolve()
    template_root = template_root.resolve()
    admission_errors = _admission_errors(blueprint, admission_draft=admission_draft)
    if admission_errors:
        raise ControllerError(
            "blueprint admission failed: " + "; ".join(admission_errors)
        )
    if workspace.exists() and any(workspace.iterdir()):
        raise ControllerError(f"workspace is not empty: {workspace}")
    for rel in [
        "config",
        "runtime",
        "ledger",
        "contracts/source",
        "contracts/rendered",
        "attempts",
        "receipts/verification",
        "receipts/gates",
        "receipts/approvals",
        "receipts/handoffs",
        "worktrees",
        "recovery",
    ]:
        (workspace / rel).mkdir(parents=True, exist_ok=True)
    try:
        lock = write_program_lock(blueprint, workspace / "runtime" / "program-lock.json")
    except BlueprintError as exc:
        raise ControllerError(str(exc)) from exc
    controller_definition = load_yaml(template_root / "CONTROLLER.yaml")["controller"]
    if controller_definition["contracts"]["blueprint"] != lock["blueprint_contract"]:
        raise ControllerError("Controller and Blueprint contract versions are incompatible")
    config = {
        "schema": "program-execution-controller.runtime-config.v2",
        "template_root": str(template_root),
        "blueprint_root": str(blueprint),
        "controller_id": controller_definition["id"],
        "controller_contract": controller_definition["contracts"]["controller"],
        "global_halt": False,
    }
    write_json(workspace / "config" / "controller.json", config)
    db = StateDB(workspace / "runtime" / "state.sqlite")
    ledger = EventLedger(workspace / "ledger" / "events.jsonl")
    try:
        db.set_meta("program_digest", lock["lock_digest"])
        db.set_meta("program", lock["program"])
        db.set_meta("targets", lock["targets"])
        db.set_meta("waves", lock["waves"])
        db.set_meta("risks", lock["risks"])
        db.set_meta("global_halt", False)
        db.set_meta("admission_draft", bool(admission_draft))
        db.set_meta(
            "definition_status",
            "draft" if admission_draft else lock["program"].get("definition_status"),
        )
        for target in lock["targets"]:
            if target.get("repository_id"):
                db.upsert_repository(target["repository_id"], target["id"])
        for task in lock["tasks"]:
            db.upsert_task(task)
        for gate in lock["gates"]:
            db.upsert_gate(gate)
        for decision in lock["decisions"]:
            db.upsert_decision(decision)
        for item in lock["unknowns"]:
            db.upsert_unknown(item)
        for waiver in lock["waivers"]:
            db.upsert_waiver(waiver)
        for evidence in lock["evidence"]:
            db.upsert_evidence(evidence)
        ledger.append(
            "CONTROLLER_BOOTSTRAPPED",
            "controller",
            {
                "workspace": str(workspace),
                "blueprint": str(blueprint),
                "program_digest": lock["lock_digest"],
                "controller_contract": config["controller_contract"],
            },
        )
    finally:
        db.close()
    return {
        "status": "BOOTSTRAPPED",
        "workspace": str(workspace),
        "program_digest": lock["lock_digest"],
        "tasks": len(lock["tasks"]),
        "targets": len(lock["targets"]),
        "admission_draft": bool(admission_draft),
        "definition_status": (
            "draft" if admission_draft else lock["program"].get("definition_status")
        ),
    }


def validate_runtime(workspace: Path) -> dict[str, Any]:
    db, ledger = open_runtime(workspace)
    errors: list[str] = []
    try:
        ok, lock_errors = verify_program_lock(workspace / "runtime" / "program-lock.json")
        if not ok:
            errors.extend(lock_errors)
        ledger_ok, ledger_message = ledger.verify()
        if not ledger_ok:
            errors.append(ledger_message)
        if db.get_meta("program_digest") is None:
            errors.append("program digest missing from state")
        task_ids = {task["id"] for task in db.tasks()}
        gate_ids = {gate["id"] for gate in db.gates()}
        decision_ids = {item["id"] for item in db.decisions()}
        unknown_ids = {item["id"] for item in db.unknowns()}
        for task in db.tasks():
            for dep in task["dependencies"]:
                if dep not in task_ids:
                    errors.append(f"{task['id']}: unresolved dependency {dep}")
            for gate_id in task["completion_gates"]:
                if gate_id not in gate_ids:
                    errors.append(f"{task['id']}: unresolved completion gate {gate_id}")
            for decision_id in task["required_decisions"]:
                if decision_id not in decision_ids:
                    errors.append(f"{task['id']}: unresolved decision {decision_id}")
            for unknown_id in task["blocking_unknowns"]:
                if unknown_id not in unknown_ids:
                    errors.append(f"{task['id']}: unresolved Unknown {unknown_id}")
        for lease in db.active_leases():
            if lease["task_id"] not in task_ids:
                errors.append(f"lease references unknown task: {lease['task_id']}")
    finally:
        db.close()
    return {"status": "PASS" if not errors else "FAIL", "errors": errors}


def reconcile_repositories(workspace: Path, mappings: list[str]) -> dict[str, Any]:
    db, ledger = open_runtime(workspace)
    results: list[dict[str, Any]] = []
    try:
        target_by_repo = {
            target.get("repository_id"): target
            for target in db.get_meta("targets", [])
            if target.get("repository_id")
        }
        for mapping in mappings:
            if "=" not in mapping:
                raise ControllerError(f"repository mapping must be repository_id=/path: {mapping}")
            repository_id, raw_path = mapping.split("=", 1)
            if repository_id not in target_by_repo:
                raise ControllerError(
                    f"repository ID is not declared by the Blueprint: {repository_id}"
                )
            repo = Path(raw_path).expanduser().resolve()
            if run_git(repo, "rev-parse", "--git-dir", check=False).returncode != 0:
                raise ControllerError(f"not a Git repository: {repo}")
            branch = run_git(repo, "branch", "--show-current").stdout.strip()
            head = run_git(repo, "rev-parse", "HEAD").stdout.strip()
            dirty = bool(run_git(repo, "status", "--porcelain").stdout.strip())
            remote = (
                run_git(repo, "remote", "get-url", "origin", check=False).stdout.strip() or None
            )
            target = target_by_repo[repository_id]
            record = {
                "repository_id": repository_id,
                "target_id": target["id"],
                "local_path": str(repo),
                "current_branch": branch,
                "head_sha": head,
                "dirty": dirty,
                "remote_url": remote,
                "reconciled_at": utc_now(),
            }
            db.upsert_repository(
                repository_id,
                target["id"],
                **{k: v for k, v in record.items() if k not in {"repository_id", "target_id"}},
            )
            results.append(record)
        ledger.append("REPOSITORIES_RECONCILED", "controller", {"repositories": results})
    finally:
        db.close()
    return {"status": "RECONCILED", "repositories": results}


def _evidence_valid(db: StateDB, evidence_id: str) -> bool:
    item = db.evidence(evidence_id)
    if item is None:
        return False
    status = item.get("status")
    if status in {"invalidated", "expired", "UNKNOWN", "planned"}:
        return False
    expires_at = item.get("expires_at")
    if expires_at and parse_time(expires_at) <= dt.datetime.now(dt.UTC):
        return False
    return True


def _gate_satisfied(db: StateDB, gate: dict[str, Any]) -> bool:
    if gate["result"] == "PASS":
        return True
    if gate["result"] != "NOT_APPLICABLE_WITH_REASON" or not gate.get("evaluation_receipt"):
        return False
    receipt_path = Path(gate["evaluation_receipt"])
    if not receipt_path.is_file():
        return False
    try:
        receipt = load_json(receipt_path)
        waiver_id = receipt.get("waiver_id")
        waiver = db.waiver(waiver_id) if waiver_id else None
        return bool(
            waiver
            and waiver.get("status") == "active"
            and gate["id"] in (waiver.get("scope") or [])
            and parse_time(waiver["expires_at"]) > dt.datetime.now(dt.UTC)
            and all(_evidence_valid(db, item) for item in waiver.get("evidence_ids") or [])
        )
    except Exception:
        return False


def _approval_valid(
    db: StateDB, task: dict[str, Any], repo: dict[str, Any] | None, requested_actions: list[str]
) -> bool:
    requires = task["risk_tier"] == "T4" or "destructive_change" in requested_actions
    if not requires:
        return True
    if repo is None:
        return False
    now = dt.datetime.now(dt.UTC)
    program_digest = db.get_meta("program_digest")
    for approval in db.approvals():
        if approval.get("action") != "execute_task":
            continue
        if approval.get("task_id") != task["id"] or approval.get("target_id") != task["target_id"]:
            continue
        if approval.get("repository_id") != task.get("repository_id"):
            continue
        if approval.get("program_digest") != program_digest or approval.get("base_sha") != repo.get(
            "head_sha"
        ):
            continue
        if not set(requested_actions) <= set(approval.get("permits") or []):
            continue
        if set(requested_actions) & set(approval.get("forbids") or []):
            continue
        if not all(
            _evidence_valid(db, item) for item in approval.get("prerequisite_evidence_ids") or []
        ):
            continue
        if parse_time(approval["expires_at"]) <= now:
            continue
        return True
    return False


def task_readiness(
    db: StateDB, task: dict[str, Any], workspace: Path | None = None
) -> tuple[bool, list[str]]:
    blockers: list[str] = []
    if workspace is not None:
        lock_ok, _ = verify_program_lock(workspace / "runtime" / "program-lock.json")
        if not lock_ok:
            blockers.append("program_lock_stale_or_invalid")
    if db.get_meta("global_halt", False):
        blockers.append("global_halt")
    if task["definition_status"] != "ready":
        blockers.append(f"definition_not_ready:{task['definition_status']}")
    if task["runtime_state"] in {
        "LEASED",
        "PREPARED",
        "CONTRACTED",
        "EXECUTING",
        "SUBMITTED",
        "VERIFYING",
        "PASSED_LOCAL",
        "COMPLETED",
        "CANCELLED",
    }:
        blockers.append(f"runtime_state_not_claimable:{task['runtime_state']}")
    for dep in task["dependencies"]:
        dependency = db.task(dep)
        if dependency is None or dependency["runtime_state"] not in {"PASSED_LOCAL", "COMPLETED"}:
            blockers.append(f"dependency_not_complete:{dep}")
    for decision_id in task["required_decisions"]:
        decision = db.decision(decision_id)
        if decision is None or decision["status"] != "accepted" or not decision["evidence_ids"]:
            blockers.append(f"required_decision_not_accepted:{decision_id}")
    for unknown_id in task["blocking_unknowns"]:
        item = db.unknown(unknown_id)
        if (
            item is None
            or item["status"] not in {"resolved", "accepted_risk", "superseded"}
            or not item["evidence_ids"]
        ):
            blockers.append(f"blocking_unknown:{unknown_id}")
    for evidence_id in task["required_evidence"]:
        if not _evidence_valid(db, evidence_id):
            blockers.append(f"required_evidence_missing_or_invalid:{evidence_id}")
    waves = {wave["id"]: wave for wave in db.get_meta("waves", [])}
    wave = waves.get(task["wave_id"])
    gates = {gate["id"]: gate for gate in db.gates()}
    if wave:
        for predecessor_id in wave.get("depends_on") or []:
            predecessor = waves.get(predecessor_id)
            if predecessor is None:
                blockers.append(f"unknown_predecessor_wave:{predecessor_id}")
                continue
            for predecessor_task_id in predecessor.get("task_ids") or []:
                predecessor_task = db.task(predecessor_task_id)
                if predecessor_task is None or predecessor_task["runtime_state"] != "COMPLETED":
                    blockers.append(
                        f"predecessor_wave_task_not_completed:{predecessor_id}:{predecessor_task_id}"
                    )
            for gate_id in predecessor.get("exit_gate_ids") or []:
                gate = gates.get(gate_id)
                if gate is None or not _gate_satisfied(db, gate):
                    blockers.append(
                        f"predecessor_wave_exit_gate_not_satisfied:{predecessor_id}:{gate_id}"
                    )
        for gate_id in wave.get("entry_gate_ids") or []:
            gate = gates.get(gate_id)
            if gate is None or not _gate_satisfied(db, gate):
                blockers.append(f"entry_gate_not_satisfied:{gate_id}")
    repo = None
    requested_actions: list[str] = []
    if task["execution_kind"] == "repo_local":
        repo = db.repository(task["repository_id"])
        if repo is None or not repo.get("head_sha"):
            blockers.append("repository_not_reconciled")
        elif repo.get("dirty"):
            blockers.append("repository_dirty")
        if task["scope_status"] != "exact" or not task.get("source_contract_path"):
            blockers.append("source_contract_incomplete")
        else:
            try:
                contract = validate_source_contract(
                    load_json(Path(task["source_contract_path"])), task
                )
                requested_actions = contract["requested_actions"]
                if any(
                    action not in {"inspect", "local_write", "destructive_change"}
                    for action in requested_actions
                ):
                    blockers.append("requested_action_requires_uninstalled_adapter")
            except Exception as exc:
                blockers.append(f"source_contract_invalid:{exc}")
        if db.active_lease_for_task(task["id"]) is not None:
            blockers.append("task_already_leased")
    if not _approval_valid(db, task, repo, requested_actions):
        blockers.append("required_approval_missing_or_invalid")
    return not blockers, blockers


def status(workspace: Path) -> dict[str, Any]:
    db, ledger = open_runtime(workspace)
    try:
        tasks = []
        for task in db.tasks():
            ready, blockers = task_readiness(db, task, workspace)
            tasks.append(
                {
                    "id": task["id"],
                    "runtime_state": task["runtime_state"],
                    "definition_status": task["definition_status"],
                    "target_id": task["target_id"],
                    "repository_id": task.get("repository_id"),
                    "eligible": ready,
                    "blockers": blockers,
                }
            )
        ledger_ok, ledger_message = ledger.verify()
        program = db.get_meta("program") or {}
        admission_draft = bool(db.get_meta("admission_draft", False))
        definition_status = (
            "draft" if admission_draft else program.get("definition_status")
        )
        campaign_root = Path.home() / ".l9/autonomy/campaigns"
        return {
            "program": program,
            "program_digest": db.get_meta("program_digest"),
            "global_halt": db.get_meta("global_halt", False),
            "definition_status": definition_status,
            "admission_draft": admission_draft,
            "autonomy_plane": {
                "authoritative": False,
                "note": (
                    "Program Controller is authoritative; autonomy campaign "
                    "packets are not a second scheduler"
                ),
                "campaign_packets_present": bool(
                    campaign_root.is_dir() and any(campaign_root.glob("*.json"))
                ),
            },
            "tasks": tasks,
            "gates": db.gates(),
            "decisions": db.decisions(),
            "unknowns": db.unknowns(),
            "active_leases": db.active_leases(),
            "ledger": {"valid": ledger_ok, "message": ledger_message},
        }
    finally:
        db.close()


def next_tasks(workspace: Path) -> dict[str, Any]:
    db, _ = open_runtime(workspace)
    try:
        ready, blocked = [], []
        admission_draft = bool(db.get_meta("admission_draft", False))
        for task in db.tasks():
            ok, blockers = task_readiness(db, task, workspace)
            item = {
                "id": task["id"],
                "title": task["title"],
                "wave_id": task["wave_id"],
                "target_id": task["target_id"],
                "repository_id": task.get("repository_id"),
                "blockers": blockers,
            }
            if admission_draft:
                item["blockers"] = list(blockers) + ["admission_draft"]
                blocked.append(item)
            elif ok:
                ready.append(item)
            else:
                blocked.append(item)
        return {
            "ready": ready,
            "blocked": blocked,
            "definition_status": "draft" if admission_draft else None,
            "admission_draft": admission_draft,
        }
    finally:
        db.close()


def claim_task(workspace: Path, task_id: str, holder: str, ttl_hours: int = 8) -> dict[str, Any]:
    db, ledger = open_runtime(workspace)
    try:
        task = db.task(task_id)
        if task is None:
            raise ControllerError(f"unknown task: {task_id}")
        ok, blockers = task_readiness(db, task, workspace)
        if not ok:
            raise ControllerError("task not eligible: " + ", ".join(blockers))
        if task["execution_kind"] != "repo_local" or not task.get("repository_id"):
            raise ControllerError("only repo_local tasks use worker leases")
        if task["runtime_state"] != "ELIGIBLE":
            db.transition_task(task_id, "ELIGIBLE")
            ledger.append("TASK_BECAME_ELIGIBLE", "controller", {"task_id": task_id})
        repo = db.repository(task["repository_id"])
        assert repo is not None
        issued = dt.datetime.now(dt.UTC).replace(microsecond=0)
        lease_id = f"lease-{uuid.uuid4().hex[:16]}"
        branch = f"pec/{task['wave_id'].lower()}/{task_id.lower()}"
        lease = {
            "lease_id": lease_id,
            "task_id": task_id,
            "repository_id": task["repository_id"],
            "holder": holder,
            "base_sha": repo["head_sha"],
            "branch": branch,
            "worktree": None,
            "contract_digest": None,
            "issued_at": issued.isoformat(),
            "expires_at": (issued + dt.timedelta(hours=ttl_hours)).isoformat(),
        }
        try:
            db.create_lease(lease)
        except Exception as exc:
            raise ControllerError(
                f"repository already has an active writer lease: {task['repository_id']}"
            ) from exc
        db.update_task(
            task_id, base_sha=repo["head_sha"], branch=branch, lease_id=lease_id, last_error=None
        )
        db.transition_task(task_id, "LEASED")
        ledger.append("TASK_LEASED", holder, lease)
        return lease
    finally:
        db.close()


def prepare_worktree(workspace: Path, task_id: str) -> dict[str, Any]:
    db, ledger = open_runtime(workspace)
    try:
        task = db.task(task_id)
        if task is None or task["runtime_state"] != "LEASED":
            raise ControllerError("task must be LEASED")
        lease = db.active_lease_for_task(task_id)
        if lease is None:
            raise ControllerError("active lease required")
        repo = db.repository(task["repository_id"])
        if repo is None:
            raise ControllerError("repository not reconciled")
        repo_path = Path(repo["local_path"])
        current_head = run_git(repo_path, "rev-parse", "HEAD").stdout.strip()
        current_dirty = bool(run_git(repo_path, "status", "--porcelain").stdout.strip())
        if current_head != lease["base_sha"] or current_dirty:
            db.transition_task(task_id, "STALE", last_error="repository_state_changed")
            raise ControllerError("repository state changed after reconciliation")
        worktree = workspace / "worktrees" / task_id
        if worktree.exists():
            raise ControllerError(f"worktree already exists: {worktree}")
        result = run_git(
            repo_path,
            "worktree",
            "add",
            "-b",
            lease["branch"],
            str(worktree),
            lease["base_sha"],
            check=False,
        )
        if result.returncode != 0:
            raise ControllerError(f"failed to create worktree: {result.stderr.strip()}")
        db.update_lease(lease["lease_id"], worktree=str(worktree))
        db.update_task(task_id, worktree=str(worktree))
        db.transition_task(task_id, "PREPARED")
        ledger.append(
            "WORKTREE_PREPARED",
            "controller",
            {
                "task_id": task_id,
                "lease_id": lease["lease_id"],
                "worktree": str(worktree),
                "base_sha": lease["base_sha"],
            },
        )
        return {
            "task_id": task_id,
            "worktree": str(worktree),
            "branch": lease["branch"],
            "base_sha": lease["base_sha"],
        }
    finally:
        db.close()


def start_task(workspace: Path, task_id: str, actor: str) -> dict[str, Any]:
    db, ledger = open_runtime(workspace)
    try:
        task = db.task(task_id)
        if task is None or task["runtime_state"] != "CONTRACTED":
            raise ControllerError("task must be CONTRACTED")
        db.transition_task(task_id, "EXECUTING")
        ledger.append(
            "TASK_EXECUTION_STARTED",
            actor,
            {"task_id": task_id, "contract_digest": task["rendered_contract_digest"]},
        )
        return {"status": "EXECUTING", "task_id": task_id}
    finally:
        db.close()


def record_attempt(workspace: Path, task_id: str, receipt_source: Path) -> dict[str, Any]:
    db, ledger = open_runtime(workspace)
    try:
        task = db.task(task_id)
        if task is None or not task.get("rendered_contract_path"):
            raise ControllerError("Rendered Contract required")
        if task["runtime_state"] not in {"CONTRACTED", "EXECUTING"}:
            raise ControllerError(f"task cannot submit from state {task['runtime_state']}")
        receipt = load_json(receipt_source)
        _validate_schema(workspace, "attempt-receipt.schema.json", receipt)
        if receipt["task_id"] != task_id:
            raise ControllerError("Attempt Receipt task mismatch")
        if receipt["contract_digest"] != task["rendered_contract_digest"]:
            raise ControllerError("Attempt Receipt contract mismatch")
        if receipt["program_digest"] != db.get_meta("program_digest"):
            raise ControllerError("Attempt Receipt Program Lock mismatch")
        if receipt["base_sha"] != task["base_sha"]:
            raise ControllerError("Attempt Receipt base SHA mismatch")
        attempt = db.next_attempt_number(task_id)
        target = (
            workspace / "attempts" / task_id / f"attempt-{attempt:03d}" / "attempt-receipt.json"
        )
        write_json(target, receipt)
        db.create_attempt(task_id, attempt, str(target), utc_now())
        db.update_task(task_id, attempts=attempt)
        db.transition_task(task_id, "SUBMITTED")
        ledger.append(
            "ATTEMPT_RECORDED",
            "worker",
            {
                "task_id": task_id,
                "attempt": attempt,
                "receipt": str(target),
                "receipt_digest": digest_object(receipt),
            },
        )
        return {
            "status": "SUBMITTED",
            "task_id": task_id,
            "attempt": attempt,
            "receipt": str(target),
        }
    finally:
        db.close()


def _changed_paths(worktree: Path) -> list[str]:
    raw = run_git(worktree, "status", "--porcelain=v1", "-z", "--untracked-files=all").stdout
    paths: list[str] = []
    parts = raw.split("\0")
    index = 0
    while index < len(parts):
        entry = parts[index]
        if not entry:
            index += 1
            continue
        status_code = entry[:2]
        path = entry[3:]
        if status_code[0] in {"R", "C"} and index + 1 < len(parts):
            index += 1
            path = parts[index]
        paths.append(path.replace("\\", "/"))
        index += 1
    return sorted(set(paths))


def _run_validation(command: str, worktree: Path) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            ["bash", "-lc", command],
            cwd=worktree,
            text=True,
            capture_output=True,
            check=False,
            timeout=300,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "status": "FAIL",
            "exit_code": 124,
            "stdout": (exc.stdout or "")[-8000:] if isinstance(exc.stdout, str) else "",
            "stderr": "validation command timed out after 300s",
        }
    return {
        "command": command,
        "status": "PASS" if completed.returncode == 0 else "FAIL",
        "exit_code": completed.returncode,
        "stdout": completed.stdout[-8000:],
        "stderr": completed.stderr[-8000:],
    }


def verify_attempt(workspace: Path, task_id: str) -> dict[str, Any]:
    db, ledger = open_runtime(workspace)
    try:
        task = db.task(task_id)
        if task is None or task["runtime_state"] != "SUBMITTED":
            raise ControllerError("task must be SUBMITTED")
        db.transition_task(task_id, "VERIFYING")
        lease = db.active_lease_for_task(task_id)
        attempt = db.latest_attempt(task_id)
        gates: dict[str, str] = {}
        lock_ok, _ = verify_program_lock(workspace / "runtime" / "program-lock.json")
        gates["program_lock"] = "PASS" if lock_ok else "STALE"
        ledger_ok, _ = ledger.verify()
        gates["ledger"] = "PASS" if ledger_ok else "FAIL"
        gates["lease"] = (
            "PASS" if lease and lease.get("lease_id") == task.get("lease_id") else "FAIL"
        )
        contract: dict[str, Any] = {}
        if task.get("rendered_contract_path") and Path(task["rendered_contract_path"]).is_file():
            contract = load_json(Path(task["rendered_contract_path"]))
            try:
                _validate_schema(workspace, "task-contract.schema.json", contract)
                claimed = contract["contract_digest"]
                body = dict(contract)
                body.pop("contract_digest", None)
                gates["contract"] = (
                    "PASS"
                    if digest_object(body) == claimed == task["rendered_contract_digest"]
                    else "FAIL"
                )
            except Exception:
                gates["contract"] = "FAIL"
        else:
            gates["contract"] = "FAIL"
        receipt = (
            load_json(Path(attempt["receipt_path"]))
            if attempt and Path(attempt["receipt_path"]).is_file()
            else {}
        )
        gates["receipt_binding"] = (
            "PASS"
            if receipt
            and receipt.get("task_id") == task_id
            and receipt.get("contract_digest") == task["rendered_contract_digest"]
            and receipt.get("program_digest") == db.get_meta("program_digest")
            and receipt.get("base_sha") == task["base_sha"]
            else "FAIL"
        )
        worktree = Path(task["worktree"]) if task.get("worktree") else None
        changed: list[str] = []
        validations: list[dict[str, Any]] = []
        candidate_sha = None
        if worktree is None or not worktree.is_dir():
            for name in [
                "base_sha",
                "changed_files_exact",
                "scope",
                "symlink",
                "worker_validation_claim",
                "validation",
            ]:
                gates[name] = "FAIL"
        else:
            gates["base_sha"] = (
                "PASS"
                if run_git(
                    worktree, "merge-base", "--is-ancestor", task["base_sha"], "HEAD", check=False
                ).returncode
                == 0
                else "FAIL"
            )
            changed = _changed_paths(worktree)
            declared = sorted(set(receipt.get("changed_files") or []))
            gates["changed_files_exact"] = "PASS" if declared == changed else "FAIL"
            patterns = contract.get("writable_paths") or []
            gates["scope"] = (
                "PASS"
                if changed and all(path_allowed(path, patterns) for path in changed)
                else "FAIL"
            )
            lock = load_json(workspace / "runtime" / "program-lock.json")
            prohibited = [
                item.get("path_or_pattern")
                for item in (lock.get("do_not_build") or {}).get(
                    "prohibited_primary_paths"
                )
                or []
                if isinstance(item, dict) and item.get("path_or_pattern")
            ]
            dnb_hit = False
            for path in changed:
                for pattern in prohibited:
                    try:
                        if path_allowed(path, [str(pattern)]):
                            dnb_hit = True
                    except ContractError:
                        if str(pattern) in path:
                            dnb_hit = True
            gates["do_not_build"] = "FAIL" if dnb_hit else "PASS"
            gates["symlink"] = (
                "PASS"
                if not any(
                    (worktree / path).is_symlink() for path in changed if (worktree / path).exists()
                )
                else "FAIL"
            )
            claimed_results = receipt.get("validation_results") or []
            claimed_commands = [item.get("command") for item in claimed_results]
            gates["worker_validation_claim"] = (
                "PASS"
                if claimed_commands == contract.get("validation_commands")
                and all(item.get("status") == "PASS" for item in claimed_results)
                else "FAIL"
            )
            validations = [
                _run_validation(command, worktree)
                for command in contract.get("validation_commands") or []
            ]
            gates["validation"] = (
                "PASS"
                if validations and all(item["status"] == "PASS" for item in validations)
                else "FAIL"
            )
            candidate_sha = run_git(worktree, "rev-parse", "HEAD").stdout.strip()
        gates["residual_unknowns"] = (
            "PASS" if not (receipt.get("residual_unknowns") or []) else "BLOCKED"
        )
        verdict = (
            "PASSED_LOCAL"
            if gates and all(value == "PASS" for value in gates.values())
            else ("STALE" if "STALE" in gates.values() else "FAILED")
        )
        attempt_number = attempt["attempt_number"] if attempt else task["attempts"]
        evidence_id = f"EVID-RUNTIME-{task_id}-{int(attempt_number):03d}"
        verification = {
            "schema": "program-execution-controller.verification-receipt.v2",
            "verification_id": f"VERIFY-{uuid.uuid4().hex[:16]}",
            "task_id": task_id,
            "contract_digest": task.get("rendered_contract_digest"),
            "program_digest": db.get_meta("program_digest"),
            "base_sha": task.get("base_sha"),
            "candidate_sha": candidate_sha,
            "declared_changed_files": sorted(set(receipt.get("changed_files") or [])),
            "observed_changed_files": changed,
            "validations": validations,
            "gates": gates,
            "verdict": verdict,
            "evidence_id": evidence_id,
            "verified_at": utc_now(),
        }
        verification["receipt_digest"] = digest_object(verification)
        _validate_schema(workspace, "verification-receipt.schema.json", verification)
        target = workspace / "receipts" / "verification" / f"{task_id}.json"
        write_json(target, verification)
        db.upsert_evidence(
            {
                "id": evidence_id,
                "type": "test_result",
                "source": str(target),
                "revision": candidate_sha or task.get("base_sha"),
                "digest": verification["receipt_digest"],
                "method": "independent_controller_verification",
                "environment": "local_worktree",
                "producer": "Program Execution Controller",
                "produced_at": verification["verified_at"],
                "expires_at": None,
                "result": "PASS" if verdict == "PASSED_LOCAL" else "FAIL",
                "status": "available",
                "supports": [task_id],
                "contradicts": [],
                "notes": None,
            }
        )
        db.transition_task(
            task_id,
            verdict,
            last_error=None if verdict == "PASSED_LOCAL" else json.dumps(gates, sort_keys=True),
        )
        ledger.append(
            "ATTEMPT_VERIFIED",
            "controller",
            {
                "task_id": task_id,
                "verdict": verdict,
                "receipt": str(target),
                "receipt_digest": verification["receipt_digest"],
                "evidence_id": evidence_id,
            },
        )
        return verification
    finally:
        db.close()


def release_lease(workspace: Path, task_id: str, reason: str, actor: str) -> dict[str, Any]:
    db, ledger = open_runtime(workspace)
    try:
        lease = db.active_lease_for_task(task_id)
        if lease is None:
            raise ControllerError("no active lease")
        db.release_lease(lease["lease_id"])
        db.update_task(task_id, lease_id=None)
        ledger.append(
            "LEASE_RELEASED",
            actor,
            {"task_id": task_id, "lease_id": lease["lease_id"], "reason": reason},
        )
        return {"status": "RELEASED", "task_id": task_id, "lease_id": lease["lease_id"]}
    finally:
        db.close()


def recover(workspace: Path, actor: str) -> dict[str, Any]:
    db, ledger = open_runtime(workspace)
    recovered: list[dict[str, Any]] = []
    try:
        now = dt.datetime.now(dt.UTC)
        for lease in db.active_leases():
            if parse_time(lease["expires_at"]) > now:
                continue
            task = db.task(lease["task_id"])
            recovery_root = workspace / "recovery" / lease["task_id"] / lease["lease_id"]
            recovery_root.mkdir(parents=True, exist_ok=True)
            metadata = {"lease": lease, "task": task, "recovered_at": utc_now(), "actor": actor}
            worktree = Path(lease["worktree"]) if lease.get("worktree") else None
            if worktree and worktree.is_dir():
                (recovery_root / "status.txt").write_text(
                    run_git(worktree, "status", "--porcelain=v1").stdout, encoding="utf-8"
                )
                patch = run_git(worktree, "diff", "--binary", check=False).stdout
                (recovery_root / "changes.patch").write_text(patch, encoding="utf-8")
                (recovery_root / "untracked.txt").write_text(
                    run_git(worktree, "ls-files", "--others", "--exclude-standard").stdout,
                    encoding="utf-8",
                )
            write_json(recovery_root / "metadata.json", metadata)
            evidence_id = f"EVID-RECOVERY-{lease['lease_id']}"
            db.upsert_evidence(
                {
                    "id": evidence_id,
                    "type": "recovery_artifact",
                    "source": str(recovery_root),
                    "revision": lease["base_sha"],
                    "digest": digest_object(metadata),
                    "method": "expired_lease_recovery",
                    "environment": "controller_runtime",
                    "producer": actor,
                    "produced_at": metadata["recovered_at"],
                    "expires_at": None,
                    "result": "INFORMATIONAL",
                    "status": "available",
                    "supports": [lease["task_id"]],
                    "contradicts": [],
                    "notes": "Expired lease evidence preserved.",
                }
            )
            db.release_lease(lease["lease_id"])
            db.update_task(lease["task_id"], lease_id=None)
            if task and task["runtime_state"] not in {"COMPLETED", "CANCELLED"}:
                try:
                    db.transition_task(lease["task_id"], "STALE", last_error="lease_expired")
                except ValueError:
                    # Task may already be outside the STALE-capable set after concurrent recovery.
                    pass
            ledger.append(
                "LEASE_RECOVERED",
                actor,
                {
                    "task_id": lease["task_id"],
                    "lease_id": lease["lease_id"],
                    "artifact": str(recovery_root),
                    "evidence_id": evidence_id,
                },
            )
            recovered.append(
                {
                    "task_id": lease["task_id"],
                    "lease_id": lease["lease_id"],
                    "artifact": str(recovery_root),
                    "evidence_id": evidence_id,
                }
            )
    finally:
        db.close()
    return {"status": "RECOVERED", "items": recovered}


def add_approval(workspace: Path, approval_file: Path) -> dict[str, Any]:
    db, ledger = open_runtime(workspace)
    try:
        approval = load_json(approval_file)
        _validate_schema(workspace, "approval.schema.json", approval)
        if approval["program_digest"] != db.get_meta("program_digest"):
            raise ControllerError("approval Program Lock mismatch")
        task = db.task(approval["task_id"])
        if (
            task is None
            or approval["target_id"] != task["target_id"]
            or approval["repository_id"] != task.get("repository_id")
        ):
            raise ControllerError("approval task or target mismatch")
        if set(approval["permits"]) & set(approval["forbids"]):
            raise ControllerError("approval permits and forbids overlap")
        if not all(db.evidence(item) is not None for item in approval["prerequisite_evidence_ids"]):
            raise ControllerError("approval references unknown prerequisite evidence")
        target = workspace / "receipts" / "approvals" / f"{approval['approval_id']}.json"
        write_json(target, approval)
        db.add_approval(approval)
        ledger.append(
            "APPROVAL_RECORDED",
            approval["approved_by"],
            {
                "approval_id": approval["approval_id"],
                "task_id": approval["task_id"],
                "receipt": str(target),
            },
        )
        return {
            "status": "RECORDED",
            "approval_id": approval["approval_id"],
            "receipt": str(target),
        }
    finally:
        db.close()


def set_decision(
    workspace: Path, decision_id: str, status_value: str, evidence_ids: list[str], actor: str
) -> dict[str, Any]:
    db, ledger = open_runtime(workspace)
    try:
        if db.decision(decision_id) is None:
            raise ControllerError(f"unknown decision: {decision_id}")
        if status_value == "accepted" and not evidence_ids:
            raise ControllerError("accepted decision requires evidence")
        if not all(_evidence_valid(db, item) for item in evidence_ids):
            raise ControllerError("decision evidence is missing, stale, or invalid")
        db.set_decision(decision_id, status_value, evidence_ids)
        ledger.append(
            "DECISION_PROJECTION_UPDATED",
            actor,
            {"decision_id": decision_id, "status": status_value, "evidence_ids": evidence_ids},
        )
        return {"status": status_value, "decision_id": decision_id, "evidence_ids": evidence_ids}
    finally:
        db.close()


def set_unknown(
    workspace: Path, unknown_id: str, status_value: str, evidence_ids: list[str], actor: str
) -> dict[str, Any]:
    db, ledger = open_runtime(workspace)
    try:
        if db.unknown(unknown_id) is None:
            raise ControllerError(f"unknown Unknown: {unknown_id}")
        if status_value in {"resolved", "accepted_risk"} and not evidence_ids:
            raise ControllerError("resolved or accepted-risk Unknown requires evidence")
        if not all(_evidence_valid(db, item) for item in evidence_ids):
            raise ControllerError("Unknown resolution evidence is missing, stale, or invalid")
        db.set_unknown(unknown_id, status_value, evidence_ids)
        ledger.append(
            "UNKNOWN_PROJECTION_UPDATED",
            actor,
            {"unknown_id": unknown_id, "status": status_value, "evidence_ids": evidence_ids},
        )
        return {"status": status_value, "unknown_id": unknown_id, "evidence_ids": evidence_ids}
    finally:
        db.close()


def evaluate_gate(
    workspace: Path,
    gate_id: str,
    result: str,
    evidence_ids: list[str],
    method: str,
    actor: str,
    waiver_id: str | None = None,
) -> dict[str, Any]:
    db, ledger = open_runtime(workspace)
    try:
        gate = db.gate(gate_id)
        if gate is None:
            raise ControllerError(f"unknown gate: {gate_id}")
        if not evidence_ids or not all(_evidence_valid(db, item) for item in evidence_ids):
            raise ControllerError("gate evaluation requires valid evidence")
        if result == "NOT_APPLICABLE_WITH_REASON":
            if not gate["definition"].get("waiver_allowed") or not waiver_id:
                raise ControllerError(
                    "NOT_APPLICABLE_WITH_REASON requires an allowed, explicit waiver"
                )
            waiver = db.waiver(waiver_id)
            if (
                waiver is None
                or waiver.get("status") != "active"
                or gate_id not in (waiver.get("scope") or [])
            ):
                raise ControllerError("waiver is missing, inactive, or out of scope")
            if parse_time(waiver["expires_at"]) <= dt.datetime.now(dt.UTC):
                raise ControllerError("waiver is expired")
            if not all(_evidence_valid(db, item) for item in waiver.get("evidence_ids") or []):
                raise ControllerError("waiver evidence is invalid")
        elif waiver_id is not None:
            raise ControllerError("waiver_id is only valid for NOT_APPLICABLE_WITH_REASON")
        evaluated_at = utc_now()
        receipt = {
            "schema": "program-execution-controller.gate-evaluation.v2",
            "evaluation_id": f"GATE-EVAL-{uuid.uuid4().hex[:16]}",
            "gate_id": gate_id,
            "program_digest": db.get_meta("program_digest"),
            "gate_definition_digest": digest_object(gate["definition"]),
            "result": result,
            "evidence_ids": sorted(set(evidence_ids)),
            "evaluated_by": actor,
            "evaluated_at": evaluated_at,
            "method": method,
            "waiver_id": waiver_id,
        }
        receipt["receipt_digest"] = digest_object(receipt)
        _validate_schema(workspace, "gate-evaluation.schema.json", receipt)
        target = workspace / "receipts" / "gates" / gate_id / f"{receipt['evaluation_id']}.json"
        write_json(target, receipt)
        db.set_gate(gate_id, result, receipt["evidence_ids"], str(target))
        ledger.append(
            "GATE_EVALUATED",
            actor,
            {
                "gate_id": gate_id,
                "result": result,
                "receipt": str(target),
                "receipt_digest": receipt["receipt_digest"],
            },
        )
        return receipt
    finally:
        db.close()


def complete_task(
    workspace: Path, task_id: str, actor: str, evidence_ids: list[str]
) -> dict[str, Any]:
    db, ledger = open_runtime(workspace)
    try:
        task = db.task(task_id)
        if task is None:
            raise ControllerError(f"unknown task: {task_id}")
        if not evidence_ids or not all(_evidence_valid(db, item) for item in evidence_ids):
            raise ControllerError("task completion requires valid evidence")
        for gate_id in task["completion_gates"]:
            gate = db.gate(gate_id)
            if gate is None or not _gate_satisfied(db, gate):
                raise ControllerError(f"completion gate not satisfied: {gate_id}")
        if task["execution_kind"] == "program_control":
            if task["runtime_state"] == "BLOCKED":
                ok, blockers = task_readiness(db, task, workspace)
                if not ok:
                    raise ControllerError("program-control task is blocked: " + ", ".join(blockers))
                db.transition_task(task_id, "ELIGIBLE")
            if task["runtime_state"] != "ELIGIBLE":
                task = db.task(task_id)
                if task is None or task["runtime_state"] != "ELIGIBLE":
                    raise ControllerError("program-control task must be ELIGIBLE")
            db.transition_task(task_id, "COMPLETED")
        else:
            if task["runtime_state"] != "PASSED_LOCAL":
                raise ControllerError("repository task must be PASSED_LOCAL before completion")
            db.transition_task(task_id, "COMPLETED")
            lease = db.active_lease_for_task(task_id)
            if lease:
                db.release_lease(lease["lease_id"])
                db.update_task(task_id, lease_id=None)
        ledger.append("TASK_COMPLETED", actor, {"task_id": task_id, "evidence_ids": evidence_ids})
        return {"status": "COMPLETED", "task_id": task_id, "evidence_ids": evidence_ids}
    finally:
        db.close()


def set_halt(workspace: Path, halted: bool, reason: str, actor: str) -> dict[str, Any]:
    db, ledger = open_runtime(workspace)
    try:
        db.set_meta("global_halt", halted)
        ledger.append("GLOBAL_HALT_CHANGED", actor, {"halted": halted, "reason": reason})
        return {"global_halt": halted, "reason": reason}
    finally:
        db.close()


def export_handoff(workspace: Path, actor: str, output: Path) -> dict[str, Any]:
    db, ledger = open_runtime(workspace)
    try:
        tasks = db.tasks()
        gates = db.gates()
        decisions = db.decisions()
        unknowns = db.unknowns()
        blocking_gates = [gate for gate in gates if gate["blocking"]]
        required_tasks = [
            task for task in tasks if task["definition_status"] not in {"cancelled", "superseded"}
        ]
        open_risks = [
            risk["id"]
            for risk in db.get_meta("risks", [])
            if risk.get("status") not in {"closed", "superseded"}
        ]
        unresolved_decisions = [item["id"] for item in decisions if item["status"] == "pending"]
        unresolved_unknowns = [item["id"] for item in unknowns if item["status"] == "open"]
        if any(gate["result"] == "FAIL" for gate in blocking_gates):
            recommendation = "NOT_CONVERGED"
        elif unresolved_decisions or unresolved_unknowns:
            recommendation = "INCONCLUSIVE"
        elif (
            required_tasks
            and all(task["runtime_state"] == "COMPLETED" for task in required_tasks)
            and all(_gate_satisfied(db, gate) for gate in blocking_gates)
        ):
            recommendation = "CONVERGED_WITH_NON_BLOCKING_RISKS" if open_risks else "CONVERGED"
        else:
            recommendation = "INCONCLUSIVE"
        program = db.get_meta("program")
        receipt = {
            "schema": "program-execution-controller.handoff-receipt.v2",
            "handoff_id": f"HANDOFF-{uuid.uuid4().hex[:16]}",
            "program_id": program["id"],
            "program_digest": db.get_meta("program_digest"),
            "controller_id": _runtime_config(workspace)["controller_id"],
            "exported_at": utc_now(),
            "runtime_summary": {
                "global_halt": db.get_meta("global_halt", False),
                "ledger_valid": ledger.verify()[0],
                "completed_tasks": sum(1 for task in tasks if task["runtime_state"] == "COMPLETED"),
                "total_required_tasks": len(required_tasks),
                "blocking_gates_passed": sum(
                    1 for gate in blocking_gates if gate["result"] == "PASS"
                ),
                "total_blocking_gates": len(blocking_gates),
                "unresolved_decisions": len(unresolved_decisions),
                "unresolved_unknowns": len(unresolved_unknowns),
            },
            "tasks": [
                {
                    "id": t["id"],
                    "runtime_state": t["runtime_state"],
                    "target_id": t["target_id"],
                    "last_error": t["last_error"],
                }
                for t in tasks
            ],
            "gates": [
                {
                    "id": g["id"],
                    "result": g["result"],
                    "evidence_ids": g["evidence_ids"],
                    "evaluation_receipt": g["evaluation_receipt"],
                }
                for g in gates
            ],
            "decisions": [
                {"id": d["id"], "status": d["status"], "evidence_ids": d["evidence_ids"]}
                for d in decisions
            ],
            "unknowns": [
                {"id": u["id"], "status": u["status"], "evidence_ids": u["evidence_ids"]}
                for u in unknowns
            ],
            "approvals": [
                {
                    "approval_id": a["approval_id"],
                    "task_id": a["task_id"],
                    "expires_at": a["expires_at"],
                }
                for a in db.approvals()
            ],
            "residual_risks": open_risks,
            "recommended_program_verdict": recommendation,
        }
        receipt["receipt_digest"] = digest_object(receipt)
        _validate_schema(workspace, "handoff-receipt.schema.json", receipt)
        write_json(output, receipt)
        archive = workspace / "receipts" / "handoffs" / f"{receipt['handoff_id']}.json"
        write_json(archive, receipt)
        ledger.append(
            "HANDOFF_EXPORTED",
            actor,
            {
                "handoff_id": receipt["handoff_id"],
                "output": str(output),
                "archive": str(archive),
                "receipt_digest": receipt["receipt_digest"],
            },
        )
        return receipt
    finally:
        db.close()

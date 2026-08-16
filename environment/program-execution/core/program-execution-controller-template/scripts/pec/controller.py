from __future__ import annotations

import datetime as dt
import importlib.util
import json
import os
import re
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


CAMPAIGN_STATUS_SCHEMA = "program-execution-controller.campaign-status.v1"
SOURCE_STATUSES = {"operator_intake", "registered", "withdrawn"}
RUNTIME_STATUSES = {"operator_intake", "active", "halted", "completed"}
TERMINAL_RUNTIME = {"halted", "completed"}
TERMINAL_VERDICTS = {"CONVERGED", "CONVERGED_WITH_NON_BLOCKING_RISKS", "NOT_CONVERGED"}


def campaign_status_path(workspace: Path) -> Path:
    return workspace.resolve() / "runtime" / "campaign-status.json"


def read_campaign_status(workspace: Path) -> dict[str, Any] | None:
    path = campaign_status_path(workspace)
    if not path.is_file():
        return None
    return load_json(path)


def write_campaign_status(
    workspace: Path,
    *,
    campaign_id: str,
    source_status: str,
    runtime_status: str,
    actor: str,
    ledger: EventLedger | None = None,
    verdict: str | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if source_status not in SOURCE_STATUSES:
        raise ControllerError(f"invalid source_status={source_status}")
    if runtime_status not in RUNTIME_STATUSES:
        raise ControllerError(f"invalid runtime_status={runtime_status}")
    current = read_campaign_status(workspace) or {}
    activated_at = current.get("activated_at")
    if runtime_status == "active" and not activated_at:
        activated_at = utc_now()
    payload = {
        "schema": CAMPAIGN_STATUS_SCHEMA,
        "campaign_id": campaign_id,
        "source_status": source_status,
        "runtime_status": runtime_status,
        "activated_at": activated_at,
        "completed_at": utc_now() if runtime_status == "completed" else current.get("completed_at"),
        "verdict": verdict if runtime_status == "completed" else current.get("verdict"),
        "evidence": evidence or current.get("evidence") or {},
        "actor": actor,
    }
    write_json(campaign_status_path(workspace), payload)
    if ledger is not None and runtime_status == "active":
        ledger.append("CAMPAIGN_ACTIVATED", actor, payload)
    if ledger is not None and runtime_status == "completed":
        ledger.append("CAMPAIGN_COMPLETED", actor, payload)
    return payload


def complete_campaign(
    workspace: Path,
    actor: str,
    verdict: str,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Mark a live campaign completed. Last required campaign step."""
    if verdict not in TERMINAL_VERDICTS:
        raise ControllerError(f"closeout requires a terminal verdict, got {verdict}")
    db, ledger = open_runtime(workspace)
    try:
        current = read_campaign_status(workspace) or db.get_meta("campaign_status") or {}
        payload = write_campaign_status(
            workspace,
            campaign_id=str(
                current.get("campaign_id") or _campaign_id_from_program(db.get_meta("program"))
            ),
            source_status=str(current.get("source_status") or "operator_intake"),
            runtime_status="completed",
            actor=actor,
            ledger=ledger,
            verdict=verdict,
            evidence=evidence,
        )
        db.set_meta("campaign_status", payload)
        return payload
    finally:
        db.close()


def _campaign_id_from_program(program: dict[str, Any] | None) -> str:
    return str((program or {}).get("id") or "unknown")


def ensure_campaign_active(
    workspace: Path,
    actor: str,
    db: StateDB,
    ledger: EventLedger,
) -> dict[str, Any]:
    current = read_campaign_status(workspace)
    if current and current.get("runtime_status") == "active":
        return current
    if current and current.get("runtime_status") in TERMINAL_RUNTIME:
        raise ControllerError(
            f"campaign cannot run; runtime_status={current.get('runtime_status')}"
        )
    source_status = str((current or {}).get("source_status") or "operator_intake")
    payload = write_campaign_status(
        workspace,
        campaign_id=_campaign_id_from_program(db.get_meta("program")),
        source_status=source_status,
        runtime_status="active",
        actor=actor,
        ledger=ledger,
    )
    db.set_meta("campaign_status", payload)
    return payload


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
            f"found definition_status={status}; "
            "live campaigns use make campaign INTENT= "
            "(do not pass --admission-draft)"
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
        raise ControllerError("blueprint admission failed: " + "; ".join(admission_errors))
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
    program_id = str((lock.get("program") or {}).get("id") or "")
    if re.fullmatch(r"pe-[0-9a-f]{8,}", program_id):
        raise ControllerError(
            f"{program_id} is a program-execution.intent.v1 hash id; pec bootstrap refuses it"
        )
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
        campaign_status = write_campaign_status(
            workspace,
            campaign_id=_campaign_id_from_program(lock.get("program")),
            source_status="operator_intake",
            runtime_status="operator_intake" if admission_draft else "active",
            actor="controller",
            ledger=None if admission_draft else ledger,
        )
        db.set_meta("campaign_status", campaign_status)
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
        "campaign_status": campaign_status,
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


ACTIVE_RUNTIME_STATES = {
    "LEASED",
    "PREPARED",
    "CONTRACTED",
    "EXECUTING",
    "SUBMITTED",
    "VERIFYING",
    "PASSED_LOCAL",
}


def _current_work(tasks: list[dict[str, Any]]) -> dict[str, str] | None:
    for task in tasks:
        state = str(task.get("runtime_state") or "")
        if state in ACTIVE_RUNTIME_STATES:
            return {"task_id": str(task["id"]), "runtime_state": state}
    return None


def _lease_base_sha(workspace: Path, repo: dict[str, Any], task_id: str) -> str:
    repo_path = Path(repo["local_path"])
    stack_path = workspace / "runtime" / "STACK.json"
    if not stack_path.is_file():
        return str(repo["head_sha"])
    stack = load_json(stack_path)
    item = next(
        (row for row in (stack.get("stack") or []) if row.get("task_id") == task_id),
        None,
    )
    if item is None:
        return str(repo["head_sha"])
    pr_base = str(item.get("pr_base") or "")
    if not pr_base:
        return str(repo["head_sha"])
    resolved = run_git(repo_path, "rev-parse", "--verify", pr_base, check=False)
    if resolved.returncode != 0:
        raise ControllerError(f"STACK.json pr_base {pr_base} is not a git ref")
    sha = resolved.stdout.strip()
    main = run_git(repo_path, "rev-parse", "--verify", "origin/main", check=False)
    if main.returncode != 0:
        main = run_git(repo_path, "rev-parse", "--verify", "main", check=False)
    if pr_base.startswith("pec/") and main.returncode == 0 and sha == main.stdout.strip():
        raise ControllerError(
            f"refuse lease.base_sha equal to origin/main; predecessor {pr_base} has no commit"
        )
    return sha


def _refuse_operator_memo_cwd(workspace: Path) -> None:
    launch_path = workspace / "runtime" / "LAUNCH.json"
    if not launch_path.is_file():
        return
    launch = load_json(launch_path)
    if launch.get("load_operator_brief") is not False:
        return
    brief = launch.get("operator_brief") or launch.get("brief_path")
    if not brief:
        return
    cwd = Path.cwd().resolve()
    memo = Path(str(brief)).expanduser().resolve()
    if cwd == memo or cwd == memo.parent:
        raise ControllerError("pec start refuses operator memo as working context")


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
    adaptation: dict[str, Any] = {
        "dependency_overrides": {},
        "scoped_unknowns": [],
    }
    if workspace is not None:
        lock_ok, _ = verify_program_lock(workspace / "runtime" / "program-lock.json")
        if not lock_ok:
            blockers.append("program_lock_stale_or_invalid")
        try:
            from .replan import plan_adaptation

            adaptation = plan_adaptation(workspace)
        except ControllerError:
            # Replan layer unavailable or plan revision not yet initialized;
            # readiness falls back to the locked plan alone.
            pass
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
    override = adaptation["dependency_overrides"].get(task["id"])
    effective_dependencies = list(task["dependencies"])
    if override:
        removed = set(override.get("remove") or [])
        effective_dependencies = [dep for dep in effective_dependencies if dep not in removed]
        for dep in override.get("add") or []:
            if dep not in effective_dependencies:
                effective_dependencies.append(dep)
    for dep in effective_dependencies:
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
    for scoped in adaptation["scoped_unknowns"]:
        if task["id"] in (scoped.get("blocked_task_ids") or []) and scoped.get("unknown_id"):
            blockers.append(f"scoped_runtime_unknown:{scoped['unknown_id']}")
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
        definition_status = "draft" if admission_draft else program.get("definition_status")
        campaign_root = Path.home() / ".l9/autonomy/campaigns"
        plan_revision = None
        try:
            from .replan import current_plan_revision

            plan = current_plan_revision(workspace)
            plan_revision = {
                "plan_revision": plan["plan_revision"],
                "active_replan_revision_id": plan.get("active_replan_revision_id"),
            }
        except ControllerError:
            # Runtime predates the replan layer; durable plan revision is unavailable.
            plan_revision = None
        return {
            "program": program,
            "program_digest": db.get_meta("program_digest"),
            "global_halt": db.get_meta("global_halt", False),
            "plan_revision": plan_revision,
            "current": _current_work(tasks),
            "definition_status": definition_status,
            "admission_draft": admission_draft,
            "campaign_status": read_campaign_status(workspace)
            or db.get_meta("campaign_status")
            or {
                "source_status": "operator_intake",
                "runtime_status": "operator_intake",
            },
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
        children: list[dict[str, Any]] = []
        try:
            from .replan import plan_adaptation

            adaptation = plan_adaptation(workspace)
        except ControllerError:
            adaptation = {"runtime_child_tasks": {}, "scoped_unknowns": []}
        for parent_id, child_ids in adaptation["runtime_child_tasks"].items():
            parent = db.task(parent_id)
            if parent is None:
                continue
            for child_id in child_ids:
                children.append(
                    {
                        "id": child_id,
                        "title": f"{parent['title']} / {child_id}",
                        "runtime_only": True,
                        "parent_task_id": parent_id,
                        "parent_authority": parent.get("authorization_ceiling", {}),
                        "blockers": ["runtime_split_child_pending_admission"],
                    }
                )
        return {
            "ready": ready,
            "blocked": blocked,
            "current": _current_work(db.tasks()),
            "runtime_split_children": children,
            "definition_status": "draft" if admission_draft else None,
            "admission_draft": admission_draft,
        }
    finally:
        db.close()


def claim_task(
    workspace: Path,
    task_id: str,
    holder: str,
    ttl_hours: int = 8,
    ttl_minutes: int | None = None,
) -> dict[str, Any]:
    db, ledger = open_runtime(workspace)
    try:
        task = db.task(task_id)
        if task is None:
            raise ControllerError(f"unknown task: {task_id}")
        ok, blockers = task_readiness(db, task, workspace)
        if not ok:
            raise ControllerError("task not eligible: " + ", ".join(blockers))
        ensure_campaign_active(workspace, holder, db, ledger)
        if task["execution_kind"] != "repo_local" or not task.get("repository_id"):
            raise ControllerError("only repo_local tasks use worker leases")
        if task["runtime_state"] != "ELIGIBLE":
            db.transition_task(task_id, "ELIGIBLE")
            ledger.append("TASK_BECAME_ELIGIBLE", "controller", {"task_id": task_id})
        repo = db.repository(task["repository_id"])
        assert repo is not None
        issued = dt.datetime.now(dt.UTC).replace(microsecond=0)
        minutes = ttl_minutes if ttl_minutes is not None else ttl_hours * 60
        lease_id = f"lease-{uuid.uuid4().hex[:16]}"
        branch = f"pec/{task['wave_id'].lower()}/{task_id.lower()}"
        base_sha = _lease_base_sha(workspace, repo, task_id)
        lease = {
            "lease_id": lease_id,
            "task_id": task_id,
            "repository_id": task["repository_id"],
            "holder": holder,
            "base_sha": base_sha,
            "branch": branch,
            "worktree": None,
            "contract_digest": None,
            "issued_at": issued.isoformat(),
            "expires_at": (issued + dt.timedelta(minutes=minutes)).isoformat(),
        }
        try:
            db.create_lease(lease)
        except Exception as exc:
            raise ControllerError(
                f"repository already has an active writer lease: {task['repository_id']}"
            ) from exc
        db.update_task(
            task_id, base_sha=base_sha, branch=branch, lease_id=lease_id, last_error=None
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
        current_dirty = bool(run_git(repo_path, "status", "--porcelain").stdout.strip())
        if current_dirty:
            db.transition_task(task_id, "STALE", last_error="repository_state_changed")
            raise ControllerError("repository state changed after reconciliation")
        stacked = (workspace / "runtime" / "STACK.json").is_file()
        current_head = run_git(repo_path, "rev-parse", "HEAD").stdout.strip()
        has_base = run_git(repo_path, "cat-file", "-t", lease["base_sha"], check=False)
        if has_base.returncode != 0 or has_base.stdout.strip() != "commit":
            db.transition_task(task_id, "STALE", last_error="lease_base_missing")
            raise ControllerError("lease base_sha is not a commit in the repository")
        if not stacked and current_head != lease["base_sha"]:
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


def _require_stack_proof_reentry(workspace: Path, extra_text: str) -> None:
    proof_path = (
        Path(__file__).resolve().parents[4] / "scripts" / "context7_stack_proof.py"
    )
    if not proof_path.is_file():
        raise ControllerError("context7_stack_proof.py missing; refuse start")
    spec = importlib.util.spec_from_file_location("context7_stack_proof", proof_path)
    if spec is None or spec.loader is None:
        raise ControllerError("cannot load context7_stack_proof")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    status = read_campaign_status(workspace) or {}
    campaign_id = str(status.get("campaign_id") or "").strip()
    if not campaign_id:
        raise ControllerError("campaign_id missing; cannot re-entry stack-proof")
    try:
        module.require_existing_receipt(campaign_id, extra_text)
    except module.StackProofError as exc:
        raise ControllerError(str(exc)) from exc


def start_task(workspace: Path, task_id: str, actor: str) -> dict[str, Any]:
    db, ledger = open_runtime(workspace)
    try:
        task = db.task(task_id)
        if task is None or task["runtime_state"] != "CONTRACTED":
            raise ControllerError("task must be CONTRACTED")
        _require_stack_proof_reentry(workspace, str(task_id))
        _refuse_operator_memo_cwd(workspace)
        ensure_campaign_active(workspace, actor, db, ledger)
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


def _changed_paths(worktree: Path, base_sha: str | None = None) -> list[str]:
    """Union of dirty working-tree changes and committed work since the base.

    The worker contract allows both styles: leave the worktree dirty, or
    commit on the task branch. Either way every touched path must be declared
    in the Attempt Receipt and stay inside the Source Contract's writable
    paths.
    """
    raw = run_git(worktree, "status", "--porcelain=v1", "-z", "--untracked-files=all").stdout
    paths: set[str] = set()
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
        paths.add(path.replace("\\", "/"))
        index += 1
    if base_sha:
        committed = run_git(
            worktree, "diff", "--name-only", f"{base_sha}..HEAD", check=False
        ).stdout
        for line in committed.splitlines():
            if line.strip():
                paths.add(line.strip().replace("\\", "/"))
    return sorted(paths)


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
            changed = _changed_paths(worktree, task.get("base_sha"))
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
                for item in (lock.get("do_not_build") or {}).get("prohibited_primary_paths") or []
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
            required_commands = contract.get("validation_commands") or []
            gates["worker_validation_claim"] = (
                "PASS"
                if claimed_commands == required_commands
                and all(item.get("status") == "PASS" for item in claimed_results)
                else "FAIL"
            )
            if required_commands:
                validations = [_run_validation(command, worktree) for command in required_commands]
                gates["validation"] = (
                    "PASS"
                    if validations and all(item["status"] == "PASS" for item in validations)
                    else "FAIL"
                )
            else:
                outputs = [
                    str(item.get("location") or "")
                    for item in (task.get("source") or {}).get("outputs") or []
                    if item.get("location")
                ]
                if not outputs:
                    outputs = [str(path) for path in (contract.get("writable_paths") or []) if path]
                gates["validation"] = (
                    "PASS"
                    if outputs and all((worktree / path).is_file() for path in outputs)
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


def _replan_contract_digest() -> str:
    import hashlib

    core = Path(__file__).resolve().parents[3]
    contract = core / "shared/REPLAN_CONTRACT.yaml"
    if not contract.is_file():
        raise ControllerError(f"Replan contract missing from core pair: {contract}")
    return hashlib.sha256(contract.read_bytes()).hexdigest()


def _peer_parity_section(repository_root: Path, workspace: Path) -> dict[str, Any]:
    import sys

    pe_root = Path(repository_root).resolve() / "environment/program-execution"
    if not pe_root.is_dir():
        raise ControllerError(f"program-execution seam not found under repository root: {pe_root}")
    sys.path.insert(0, str(pe_root))
    from peer_execution.golden_vectors import run_parity_gate

    report = run_parity_gate(repository_root, workspace)
    accounting_path = Path(workspace).resolve() / "runtime/projection/peer-accounting.json"
    semantic_digest = None
    coverage: list[str] = []
    if accounting_path.is_file():
        accounting = json.loads(accounting_path.read_text(encoding="utf-8"))
        semantic_digest = accounting.get("semantic_revision_digest")
        coverage = [record["peer_id"] for record in accounting.get("records") or []]
    return {
        "status": "PASS" if report["status"] == "PASS" else "BLOCKED",
        "semantic_revision_digest": semantic_digest,
        "peer_coverage": coverage,
        "failures": report.get("failures", []),
    }


def export_handoff(
    workspace: Path,
    actor: str,
    output: Path,
    repository_root: Path | None = None,
) -> dict[str, Any]:
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
        # Replan section: contract revision, plan revision, and the full
        # revision history. Failed and stale revisions remain visible; the
        # Controller recommends but never declares terminal convergence.
        from .replan import current_plan_revision, list_revisions

        plan = current_plan_revision(workspace)
        revisions = list_revisions(workspace)
        receipt["replan"] = {
            "plan_revision": plan["plan_revision"],
            "active_replan_revision_id": plan.get("active_replan_revision_id"),
            "contract_digest": _replan_contract_digest(),
            "revisions": revisions,
            "failed_revisions_visible": [
                revision["revision_id"]
                for revision in revisions
                if revision["status"] in {"rejected", "stale"}
            ],
        }
        # Peer parity section: coverage and cross-peer results are required
        # whenever a repository root is supplied; a missing or blocked parity
        # proof caps the recommendation at INCONCLUSIVE.
        receipt["peer_parity"] = {
            "status": "NOT_RUN",
            "semantic_revision_digest": None,
            "peer_coverage": [],
            "failures": [],
        }
        if repository_root is not None:
            parity = _peer_parity_section(repository_root, workspace)
            receipt["peer_parity"] = parity
            if parity["status"] != "PASS" and recommendation in {
                "CONVERGED",
                "CONVERGED_WITH_NON_BLOCKING_RISKS",
            }:
                recommendation = "INCONCLUSIVE"
                receipt["recommended_program_verdict"] = recommendation
        receipt["rollback_state"] = {
            "strategy": "restore_source_worktree_from_program_lock_base",
            "program_lock_digest": db.get_meta("program_digest"),
            "blueprint_root": _runtime_config(workspace).get("blueprint_root"),
            "worktree_isolation": True,
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
        if recommendation in TERMINAL_VERDICTS:
            campaign_id = _campaign_id_from_program(program)
            current = read_campaign_status(workspace) or {}
            payload = write_campaign_status(
                workspace,
                campaign_id=campaign_id,
                source_status=str(current.get("source_status") or "operator_intake"),
                runtime_status="completed",
                actor=actor,
                ledger=ledger,
                verdict=recommendation,
                evidence={"handoff_id": receipt["handoff_id"], "output": str(output)},
            )
            db.set_meta("campaign_status", payload)
            receipt["campaign_status"] = payload
        return receipt
    finally:
        db.close()

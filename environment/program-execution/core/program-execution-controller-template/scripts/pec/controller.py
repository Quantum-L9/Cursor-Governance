from __future__ import annotations

import datetime as dt
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import uuid
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .blueprint import (
    BlueprintError,
    build_program_lock,
    relock_tasks,
    stale_task_ids,
    verify_program_lock,
)
from .common import (
    ControllerError,
    digest_object,
    load_json,
    load_yaml,
    parse_time,
    run_git,
    utc_now,
    write_json,
)
from .contracts import (
    LOCALLY_EXECUTABLE_ACTIONS,
    ContractError,
    path_allowed,
    validate_source_contract,
)
from .exec_env import resolve_exec_env, run_validation_command
from .ledger import EventLedger
from .runtime import (
    _require_stack_proof_reentry,
    _runtime_config,
    campaign_status_path,
    open_runtime,
    read_campaign_status,
)
from .state import StateDB
from .workspace_reset import clean_task_execution

CAMPAIGN_STATUS_SCHEMA = "program-execution-controller.campaign-status.v1"
SOURCE_STATUSES = {"operator_intake", "registered", "withdrawn"}
RUNTIME_STATUSES = {"operator_intake", "active", "halted", "completed"}
TERMINAL_RUNTIME = {"halted", "completed"}
TERMINAL_VERDICTS = {"CONVERGED", "CONVERGED_WITH_NON_BLOCKING_RISKS", "NOT_CONVERGED"}
SUCCESS_VERDICTS = {"CONVERGED", "CONVERGED_WITH_NON_BLOCKING_RISKS"}
TERMINAL_TASK_STATES = {"COMPLETED", "FAILED", "CANCELLED"}


def _campaign_completion_blockers(db: StateDB, verdict: str) -> dict[str, list[str]]:
    """Canonical task/lease/gate truth that refuses a premature campaign close.

    A successful verdict requires every task COMPLETED; NOT_CONVERGED permits
    terminal failed/cancelled children but never live children or active
    leases. Blocking gates are only a success-side requirement.
    """
    success = verdict in SUCCESS_VERDICTS
    tasks = db.tasks()
    if success:
        unfinished = [str(item["id"]) for item in tasks if item["runtime_state"] != "COMPLETED"]
    else:
        unfinished = [
            str(item["id"]) for item in tasks if item["runtime_state"] not in TERMINAL_TASK_STATES
        ]
    blockers: dict[str, list[str]] = {}
    if unfinished:
        blockers["tasks"] = unfinished
    active = db.active_leases()
    if active:
        blockers["active_leases"] = [str(item["lease_id"]) for item in active]
    if success:
        blocked_gates = [
            str(item["id"])
            for item in db.gates()
            if bool(item.get("blocking")) and item.get("result") != "PASS"
        ]
        if blocked_gates:
            blockers["blocking_gates"] = blocked_gates
    return blockers


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


def _program_recommendation(db: StateDB, ledger: EventLedger) -> tuple[str, dict[str, Any]]:
    """The one verdict computation `export-handoff` and `close` both consult.

    Returns the recommended terminal verdict and the facts it rests on. A
    success verdict is recommended only when every required task is COMPLETED,
    every blocking gate is satisfied, no decision or Unknown is open, the
    runtime is not halted and the ledger verifies.
    """
    tasks = db.tasks()
    gates = db.gates()
    blocking_gates = [gate for gate in gates if gate["blocking"]]
    required_tasks = [
        task for task in tasks if task["definition_status"] not in {"cancelled", "superseded"}
    ]
    open_risks = [
        risk["id"]
        for risk in db.get_meta("risks", [])
        if risk.get("status") not in {"closed", "superseded"}
    ]
    unresolved_decisions = [item["id"] for item in db.decisions() if item["status"] == "pending"]
    unresolved_unknowns = [item["id"] for item in db.unknowns() if item["status"] == "open"]
    ledger_ok, ledger_message = ledger.verify()
    halted = bool(db.get_meta("global_halt", False))
    if any(gate["result"] == "FAIL" for gate in blocking_gates):
        recommendation = "NOT_CONVERGED"
    elif unresolved_decisions or unresolved_unknowns or halted or not ledger_ok:
        recommendation = "INCONCLUSIVE"
    elif (
        required_tasks
        and all(task["runtime_state"] == "COMPLETED" for task in required_tasks)
        and all(_gate_satisfied(db, gate) for gate in blocking_gates)
    ):
        recommendation = "CONVERGED_WITH_NON_BLOCKING_RISKS" if open_risks else "CONVERGED"
    else:
        recommendation = "INCONCLUSIVE"
    facts = {
        "unresolved_decisions": unresolved_decisions,
        "unresolved_unknowns": unresolved_unknowns,
        "open_risks": open_risks,
        "global_halt": halted,
        "ledger_valid": ledger_ok,
        "ledger_message": ledger_message,
        "required_tasks": len(required_tasks),
        "blocking_gates": len(blocking_gates),
    }
    return recommendation, facts


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
        blockers = _campaign_completion_blockers(db, verdict)
        if blockers:
            raise ControllerError(
                "campaign close refused; canonical child/gate/lease state is not terminal: "
                + json.dumps(blockers, sort_keys=True)
            )
        recommendation, facts = _program_recommendation(db, ledger)
        if verdict in SUCCESS_VERDICTS and recommendation not in SUCCESS_VERDICTS:
            # The caller's verdict is a claim; the runtime's own facts decide
            # whether a success verdict is supportable. Pending decisions, open
            # Unknowns, a halt or a broken ledger recommend INCONCLUSIVE, and a
            # close may not declare more than the Controller can recommend.
            raise ControllerError(
                f"campaign close refused; verdict {verdict} exceeds the Controller "
                f"recommendation {recommendation}: " + json.dumps(facts, sort_keys=True)
            )
        if verdict in SUCCESS_VERDICTS and not facts["ledger_valid"]:
            raise ControllerError("campaign close refused; ledger integrity failure")
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


def load_json_or_yaml(path: Path) -> Any:
    return load_json(path) if path.suffix == ".json" else load_yaml(path)


def _validate_schema(workspace: Path, schema_name: str, value: Any) -> None:
    # Imported here, not at module scope: jsonschema costs ~0.19s to import and
    # every `pec.py` CLI invocation paid it whether or not it validated anything.
    # The conformance suite spawns that CLI ~14 times per campaign test, so the
    # import alone was minutes of the suite's wall clock.
    from jsonschema import Draft202012Validator  # noqa: PLC0415 - deferred: see above

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
    if not path.is_file():
        raise ControllerError(f"validate_blueprint.py missing; refuse start: {path}")
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
    # A hand-assembled blueprint (the Controller's own fixtures) carries no
    # MANIFEST/README pair, so the instantiated validator cannot run. Live
    # blueprints always carry both (instantiate copies README, accept writes
    # MANIFEST). The skip is recorded in the ledger by `bootstrap`, never silent.
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
    if workspace.exists() and any(item.name != "telemetry" for item in workspace.iterdir()):
        raise ControllerError(f"workspace is not empty: {workspace}")
    # Validate BEFORE the first write. A lock written ahead of a failed check
    # left `runtime/program-lock.json` behind, and every retry then hit
    # "workspace is not empty" until an operator deleted it by hand.
    try:
        lock = build_program_lock(blueprint)
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
    write_json(workspace / "runtime" / "program-lock.json", lock)
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
    ledger = EventLedger(workspace / "ledger" / "events.jsonl", anchor_store=db)
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
        blueprint_validation = "instantiated" if _complete_pair(blueprint) else "skipped"
        ledger.append(
            "CONTROLLER_BOOTSTRAPPED",
            "controller",
            {
                "workspace": str(workspace),
                "blueprint": str(blueprint),
                "program_digest": lock["lock_digest"],
                "controller_contract": config["controller_contract"],
                "blueprint_validation": blueprint_validation,
            },
        )
        if blueprint_validation == "skipped":
            # Visible, never silent: the pair was incomplete so the
            # instantiated validator did not run over this blueprint.
            ledger.append(
                "BLUEPRINT_VALIDATION_SKIPPED",
                "controller",
                {
                    "blueprint": str(blueprint),
                    "reason": "incomplete MANIFEST.yaml/README.md pair",
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
        "blueprint_validation": blueprint_validation,
    }


def relock_definitions(
    workspace: Path, *, actor: str, task_ids: Iterable[str] | None = None
) -> dict[str, Any]:
    """Adopt edited task definitions without discarding execution history.

    Definition state and execution history were conflated: an edited task card
    made the whole lock stale, and the only cure was a fresh workspace, which
    threw away every completed task to adopt one changed definition.

    This separates them. The definitions that moved are relocked; the tasks that
    did not move are untouched. A task still in flight loses its contract
    binding, because that contract was rendered from a definition that no longer
    exists and re-rendering it is cheap. A task already COMPLETED keeps its
    state and its receipts: the work happened, and the provenance record below
    is what makes "which definition produced that code" answerable afterwards.

    Which definitions moved is either inferred here from the blueprint on disk,
    or named by the caller. Naming them exists because inference reads compiled
    blueprint files, and admission annotates several of those after the lock
    freezes them -- so on a live campaign every rerun looks program-wide even
    when the operator edited one task card. A caller that compared the authored
    campaign source knows better than the annotated output does, and takes
    responsibility for that comparison by passing the ids.
    """
    db, ledger = open_runtime(workspace)
    lock_path = workspace / "runtime" / "program-lock.json"
    try:
        stale = (
            stale_task_ids(lock_path)
            if task_ids is None
            else sorted(dict.fromkeys(str(item) for item in task_ids))
        )
        if stale is None:
            raise ControllerError(
                "definition drift cannot be attributed to individual tasks "
                "(program-wide source changed, or the lock is unreadable); "
                "start a fresh workspace instead of relocking"
            )
        if not stale:
            return {"status": "CURRENT", "relocked": [], "superseded_after_completion": []}

        outcome = relock_tasks(lock_path, stale)
        superseded: list[str] = []
        for task_id in outcome["relocked"]:
            existing = db.task(task_id)
            state = str((existing or {}).get("runtime_state") or "")
            db.upsert_task(outcome["tasks"][task_id])
            if state == "COMPLETED":
                # History survives: the receipt stays bound to the definition it
                # was verified against, and provenance records the supersession.
                superseded.append(task_id)
                continue
            db.update_task(
                task_id,
                scope_status="intent_only",
                source_contract_path=None,
                source_contract_digest=None,
                rendered_contract_path=None,
                rendered_contract_digest=None,
            )
            for name in ("source", "rendered"):
                (workspace / "contracts" / name / f"{task_id}.json").unlink(missing_ok=True)
            lease = db.active_lease_for_task(task_id)
            if lease is not None:
                db.release_lease(str(lease["lease_id"]))
            if state not in {"WAITING", "BLOCKED", "ELIGIBLE"}:
                # STALE is the state model's own word for "the definition this
                # was working from was replaced", and unlike BLOCKED it is
                # reachable from every active state. Land on ELIGIBLE from
                # there: readiness is recomputed per call, so an unmet
                # dependency still blocks the task.
                db.transition_task(task_id, "STALE", last_error=None)
                db.transition_task(task_id, "ELIGIBLE", last_error=None)

        db.set_meta("program_digest", outcome["lock_digest"])
        record = {
            "schema": "program-execution-controller.definition-provenance.v1",
            "recorded_at": utc_now(),
            "actor": actor,
            "previous_lock_digest": outcome["previous_lock_digest"],
            "lock_digest": outcome["lock_digest"],
            "definitions": outcome["definitions"],
            "superseded_after_completion": sorted(superseded),
        }
        history = workspace / "runtime" / "definition-provenance.jsonl"
        history.parent.mkdir(parents=True, exist_ok=True)
        with history.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True) + "\n")
        ledger.append(
            "TASK_DEFINITIONS_RELOCKED",
            actor,
            {
                "relocked": outcome["relocked"],
                "lock_digest": outcome["lock_digest"],
                "superseded_after_completion": sorted(superseded),
            },
        )
        return {
            "status": "RELOCKED",
            "relocked": outcome["relocked"],
            "superseded_after_completion": sorted(superseded),
            "lock_digest": outcome["lock_digest"],
            "provenance": str(history),
        }
    finally:
        db.close()


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
    # STATE_MODEL.evidence_result: UNKNOWN is non-passing, and a FAIL or BLOCKED
    # result is not evidence FOR anything. `verify_attempt` records a FAILED
    # verdict with `result: FAIL, status: available`; it must not satisfy a
    # decision, an unknown, a gate, or a waiver.
    if str(item.get("result") or "") in {"FAIL", "BLOCKED", "UNKNOWN"}:
        return False
    expires_at = item.get("expires_at")
    if expires_at and parse_time(expires_at) <= dt.datetime.now(dt.UTC):
        return False
    return True


def _require_ledger_integrity(ledger: EventLedger) -> None:
    """A Program-state transition never lands on top of a tampered ledger.

    `verify()` used to run only where a reader happened to ask; a middle event
    could be rewritten and every later mutation still appended on top of it.
    Every transition that changes Program truth checks the chain first.
    """
    ok, message = ledger.verify()
    if not ok:
        raise ControllerError(
            f"ledger integrity failure; refusing to mutate Program state: {message}"
        )


def _evidence_supports(db: StateDB, evidence_ids: list[str], task_ids: set[str]) -> bool:
    """Does any of this evidence support one of these tasks?"""
    for evidence_id in evidence_ids:
        item = db.evidence(evidence_id) or {}
        if set(item.get("supports") or []) & task_ids:
            return True
    return False


#: Gate classes that close over executed work. Their PASS needs the
#: Controller's own verification of an in-scope task, never catalog evidence.
EXECUTION_GATE_CLASSES = frozenset({"execution", "validation"})
CONTROLLER_VERIFICATION_METHOD = "independent_controller_verification"


def _controller_verification_supports(
    db: StateDB, evidence_ids: list[str], task_ids: set[str]
) -> bool:
    for evidence_id in evidence_ids:
        item = db.evidence(evidence_id) or {}
        if str(item.get("method") or "") != CONTROLLER_VERIFICATION_METHOD:
            continue
        if str(item.get("result") or "") != "PASS":
            continue
        if set(item.get("supports") or []) & task_ids:
            return True
    return False


def _risk_tier_policy() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[2] / "policy" / "risk-tiers.yaml"
    if not path.is_file():
        raise ControllerError(f"risk tier policy missing: {path}")
    document = load_json_or_yaml(path)
    tiers = document.get("tiers") if isinstance(document, dict) else None
    if not isinstance(tiers, dict):
        raise ControllerError(f"risk tier policy has no tiers: {path}")
    return tiers


def _max_attempts(task: dict[str, Any]) -> int:
    """The retry budget the risk policy grants this task. Undefined is refused."""
    tier = str(task.get("risk_tier") or "")
    policy = _risk_tier_policy().get(tier)
    budget = (policy or {}).get("max_attempts") if isinstance(policy, dict) else None
    if not isinstance(budget, int) or isinstance(budget, bool) or budget < 1:
        raise ControllerError(
            f"risk tier {tier!r} declares no positive max_attempts; retries are finite or refused"
        )
    return budget


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


def _campaign_integration_branch(workspace: Path) -> str | None:
    status = read_campaign_status(workspace) or {}
    campaign_id = str(status.get("campaign_id") or "").strip()
    if not campaign_id or campaign_id == "unknown":
        return None
    return f"campaign/{campaign_id}"


def _integration_branch_in_force(db: StateDB, workspace: Path, task: dict[str, Any]) -> bool:
    """Is fan-in through `campaign/<id>` live for this task's repository?

    The same test `_integrate_candidate` applies: a named integration branch
    that does not exist in the reconciled repository is not in force, and a
    standalone runtime keeps PASSED_LOCAL as a satisfying dependency state.
    """
    branch = _campaign_integration_branch(workspace)
    if branch is None or not task.get("repository_id"):
        return False
    repo = db.repository(str(task["repository_id"]))
    if repo is None or not repo.get("local_path"):
        return False
    repo_path = Path(str(repo["local_path"]))
    if not repo_path.is_dir():
        return False
    return (
        run_git(repo_path, "rev-parse", "--verify", f"refs/heads/{branch}", check=False).returncode
        == 0
    )


def _lease_base_sha(workspace: Path, repo: dict[str, Any], task_id: str) -> str:
    """Local execution lineage comes from the campaign integration branch.

    STACK.json and PR bases describe publication topology only; they never
    choose a local task execution base. When the reconciled repository carries
    the campaign integration branch (`campaign/<campaign_id>`), every task
    worktree fans out from that branch's current clean HEAD — dependent tasks
    see accumulated fan-in because verified candidates are integrated back
    into the branch before their task COMPLETEs. Without an integration
    branch (a standalone Controller runtime), the reconciled repository head
    remains the base.
    """
    del task_id  # lineage is per-campaign, never per-task publication routing
    repo_path = Path(repo["local_path"])
    branch = _campaign_integration_branch(workspace)
    if branch is None:
        return str(repo["head_sha"])
    resolved = run_git(repo_path, "rev-parse", "--verify", f"refs/heads/{branch}", check=False)
    if resolved.returncode != 0:
        # No integration branch in this repository: campaign lineage is not in
        # force here (standalone Controller runtimes never create one).
        return str(repo["head_sha"])
    sha = resolved.stdout.strip()
    kind = run_git(repo_path, "cat-file", "-t", sha, check=False)
    if kind.returncode != 0 or kind.stdout.strip() != "commit":
        raise ControllerError(f"campaign integration head is not a commit: {branch}={sha}")
    if run_git(repo_path, "status", "--porcelain").stdout.strip():
        raise ControllerError(
            "repository must be clean before leasing from the campaign integration branch"
        )
    recorded = str(repo.get("head_sha") or "")
    if recorded and recorded != sha:
        ancestry = run_git(repo_path, "merge-base", "--is-ancestor", recorded, sha, check=False)
        if ancestry.returncode != 0:
            raise ControllerError(
                f"campaign integration branch {branch} does not descend from the "
                f"reconciled repository record {recorded}; reconcile before leasing"
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
    # Deliberately broad and fail-CLOSED: any fault reading or validating the
    # waiver returns False, i.e. "no active waiver". Narrowing risks a fault
    # propagating as an exception where the caller expects a boolean verdict.
    # nosemgrep: l9.baseline.python.broad-except
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


def lock_trusted_for_task(workspace: Path, task_id: str) -> bool:
    """Is the locked plan still authoritative for this one task?

    Editing one task card used to make every task in the program unready and
    every verification STALE, because the lock is verified at file granularity
    and all task cards share a file. That conflates the definition of a task
    with the history recorded against every other task.

    A task is judged against its own definition: unchanged means the lock still
    describes it, whatever was edited elsewhere in the file. When the change
    cannot be attributed to particular tasks, `stale_task_ids` says so and the
    global verdict stands.
    """
    lock_path = workspace / "runtime" / "program-lock.json"
    stale = stale_task_ids(lock_path)
    if stale is None:
        return verify_program_lock(lock_path)[0]
    return task_id not in stale


# Readiness reason kinds (ADR-0023). "waiting" is ordinary sequencing or a
# setup step the runtime can deterministically progress toward; "blocking" is
# a genuine inability to proceed; "state" is a runtime lifecycle position
# (already executing, terminal) that is neither waiting nor blocked.
_WAITING = "waiting"
_BLOCKING = "blocking"
_STATE = "state"


#: A verification mechanism that can actually produce a verdict. `inspection`
#: alone cannot: it yields a reading, not the pass/fail the Controller acts on.
_TERMINAL_VERIFICATION_METHODS = {"command", "command_and_inspection", "external_adapter"}

#: Ceiling flags that make a task mutating, and so require a terminal verifier.
_MUTATING_AUTHORIZATIONS = ("local_write", "commit", "destructive_change")


def missing_terminal_verifier(task: dict[str, Any]) -> bool:
    """A mutating repo-local task the Controller could never verify.

    Acceptance already refuses this before a Blueprint is sealed. This is the
    defence in depth: a lock written before that rule existed, or a task that
    reached runtime by some other path, would otherwise be claimable and fail
    only at `verify` — after the worker had already changed the repository.
    Readiness is where that costs nothing.
    """
    if str(task.get("execution_kind") or "").strip() != "repo_local":
        return False
    ceiling = task.get("authorization_ceiling") or {}
    if not any(bool(ceiling.get(action)) for action in _MUTATING_AUTHORIZATIONS):
        return False
    mechanisms = task.get("verification_mechanisms") or []
    return not any(
        isinstance(item, dict) and str(item.get("method") or "") in _TERMINAL_VERIFICATION_METHODS
        for item in mechanisms
    )


def _gate_prerequisite_kind(gate: dict[str, Any] | None) -> str:
    """Classify an unsatisfied gate prerequisite (ADR-0023).

    A gate that has not yet been evaluated (result UNKNOWN) is an ordering
    condition: waiting. A missing gate, an authoritative FAIL/BLOCKED result,
    or an evaluated waiver that no longer holds is a real blocker.
    """
    if gate is None:
        return _BLOCKING
    result = str(gate.get("result") or "UNKNOWN")
    if result in {"FAIL", "BLOCKED", "NOT_APPLICABLE_WITH_REASON"}:
        return _BLOCKING
    return _WAITING


def task_readiness_detail(
    db: StateDB, task: dict[str, Any], workspace: Path | None = None
) -> dict[str, Any]:
    """One authoritative readiness evaluation, with classified reasons.

    Every check below is preserved from the pre-ADR-0023 evaluation; the only
    change is that each reason is classified as waiting (sequencing / setup
    not yet prepared), blocking (genuine inability to proceed), or state
    (runtime lifecycle position). Eligibility itself is unchanged: any reason
    at all refuses a claim.
    """
    entries: list[tuple[str, str]] = []
    adaptation: dict[str, Any] = {
        "dependency_overrides": {},
        "scoped_unknowns": [],
    }
    if workspace is not None:
        if not lock_trusted_for_task(workspace, str(task["id"])):
            entries.append((_BLOCKING, "program_lock_stale_or_invalid"))
        try:
            from .replan import plan_adaptation

            adaptation = plan_adaptation(workspace)
        except ControllerError:
            # Replan layer unavailable or plan revision not yet initialized;
            # readiness falls back to the locked plan alone.
            pass
    if db.get_meta("global_halt", False):
        entries.append((_BLOCKING, "global_halt"))
    if task["definition_status"] != "ready":
        entries.append((_BLOCKING, f"definition_not_ready:{task['definition_status']}"))
    if missing_terminal_verifier(task):
        entries.append((_BLOCKING, "missing_terminal_verifier"))
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
        entries.append((_STATE, f"runtime_state_not_claimable:{task['runtime_state']}"))
    override = adaptation["dependency_overrides"].get(task["id"])
    effective_dependencies = list(task["dependencies"])
    if override:
        removed = set(override.get("remove") or [])
        effective_dependencies = [dep for dep in effective_dependencies if dep not in removed]
        for dep in override.get("add") or []:
            if dep not in effective_dependencies:
                effective_dependencies.append(dep)
    # Under a campaign integration branch a dependency's work reaches the
    # successor's base only at COMPLETED (fan-in). PASSED_LOCAL work is still
    # sitting on its task branch, so a successor claimed against it would base
    # on a lineage that lacks exactly the change it depends on.
    integrated_only = _integration_branch_in_force(db, workspace, task)
    satisfied = {"COMPLETED"} if integrated_only else {"PASSED_LOCAL", "COMPLETED"}
    for dep in effective_dependencies:
        dependency = db.task(dep)
        if dependency is None or dependency["runtime_state"] not in satisfied:
            entries.append((_WAITING, f"dependency_not_complete:{dep}"))
    for decision_id in task["required_decisions"]:
        decision = db.decision(decision_id)
        if decision is None or decision["status"] != "accepted" or not decision["evidence_ids"]:
            entries.append((_BLOCKING, f"required_decision_not_accepted:{decision_id}"))
    for unknown_id in task["blocking_unknowns"]:
        item = db.unknown(unknown_id)
        if (
            item is None
            or item["status"] not in {"resolved", "accepted_risk", "superseded"}
            or not item["evidence_ids"]
        ):
            entries.append((_BLOCKING, f"blocking_unknown:{unknown_id}"))
    for scoped in adaptation["scoped_unknowns"]:
        if task["id"] in (scoped.get("blocked_task_ids") or []) and scoped.get("unknown_id"):
            entries.append((_BLOCKING, f"scoped_runtime_unknown:{scoped['unknown_id']}"))
    for evidence_id in task["required_evidence"]:
        if not _evidence_valid(db, evidence_id):
            entries.append((_BLOCKING, f"required_evidence_missing_or_invalid:{evidence_id}"))
    waves = {wave["id"]: wave for wave in db.get_meta("waves", [])}
    wave = waves.get(task["wave_id"])
    gates = {gate["id"]: gate for gate in db.gates()}
    if wave:
        for predecessor_id in wave.get("depends_on") or []:
            predecessor = waves.get(predecessor_id)
            if predecessor is None:
                entries.append((_BLOCKING, f"unknown_predecessor_wave:{predecessor_id}"))
                continue
            for predecessor_task_id in predecessor.get("task_ids") or []:
                predecessor_task = db.task(predecessor_task_id)
                if predecessor_task is None or predecessor_task["runtime_state"] != "COMPLETED":
                    entries.append(
                        (
                            _WAITING,
                            "predecessor_wave_task_not_completed:"
                            f"{predecessor_id}:{predecessor_task_id}",
                        )
                    )
            for gate_id in predecessor.get("exit_gate_ids") or []:
                gate = gates.get(gate_id)
                if gate is None or not _gate_satisfied(db, gate):
                    entries.append(
                        (
                            _gate_prerequisite_kind(gate),
                            f"predecessor_wave_exit_gate_not_satisfied:{predecessor_id}:{gate_id}",
                        )
                    )
        for gate_id in wave.get("entry_gate_ids") or []:
            gate = gates.get(gate_id)
            if gate is None or not _gate_satisfied(db, gate):
                entries.append(
                    (_gate_prerequisite_kind(gate), f"entry_gate_not_satisfied:{gate_id}")
                )
    repo = None
    requested_actions: list[str] = []
    if task["execution_kind"] == "repo_local":
        repo = db.repository(task["repository_id"])
        if repo is None or not repo.get("head_sha"):
            # Setup not prepared yet; `pec reconcile` deterministically clears it.
            entries.append((_WAITING, "repository_not_reconciled"))
        elif repo.get("dirty"):
            entries.append((_BLOCKING, "repository_dirty"))
        if task["scope_status"] != "exact" or not task.get("source_contract_path"):
            # Setup not prepared yet; draft/register-contract deterministically clears it.
            entries.append((_WAITING, "source_contract_incomplete"))
        else:
            try:
                contract = validate_source_contract(
                    load_json(Path(task["source_contract_path"])), task
                )
                requested_actions = contract["requested_actions"]
                if any(
                    action not in set(LOCALLY_EXECUTABLE_ACTIONS) for action in requested_actions
                ):
                    entries.append((_BLOCKING, "requested_action_requires_uninstalled_adapter"))
            except Exception as exc:
                entries.append((_BLOCKING, f"source_contract_invalid:{exc}"))
        if db.active_lease_for_task(task["id"]) is not None:
            entries.append((_STATE, "task_already_leased"))
    if not _approval_valid(db, task, repo, requested_actions):
        entries.append((_BLOCKING, "required_approval_missing_or_invalid"))
    return {
        "eligible": not entries,
        "waiting_reasons": [reason for kind, reason in entries if kind == _WAITING],
        "blocking_reasons": [reason for kind, reason in entries if kind == _BLOCKING],
        "state_reasons": [reason for kind, reason in entries if kind == _STATE],
        "reasons": [reason for _, reason in entries],
    }


def task_readiness(
    db: StateDB, task: dict[str, Any], workspace: Path | None = None
) -> tuple[bool, list[str]]:
    detail = task_readiness_detail(db, task, workspace)
    return detail["eligible"], detail["reasons"]


def _task_classification(task: dict[str, Any], detail: dict[str, Any]) -> str:
    """ready / waiting / blocked / in_progress / terminal (ADR-0023)."""
    state = str(task.get("runtime_state") or "")
    if state in ACTIVE_RUNTIME_STATES:
        return "in_progress"
    if state in {"COMPLETED", "CANCELLED"}:
        return "terminal"
    if detail["eligible"]:
        return "ready"
    if detail["blocking_reasons"]:
        return "blocked"
    return "waiting"


def status(workspace: Path) -> dict[str, Any]:
    db, ledger = open_runtime(workspace)
    try:
        tasks = []
        for task in db.tasks():
            detail = task_readiness_detail(db, task, workspace)
            tasks.append(
                {
                    "id": task["id"],
                    "runtime_state": task["runtime_state"],
                    "definition_status": task["definition_status"],
                    "target_id": task["target_id"],
                    "repository_id": task.get("repository_id"),
                    "eligible": detail["eligible"],
                    "classification": _task_classification(task, detail),
                    "waiting_reasons": detail["waiting_reasons"],
                    "blocking_reasons": detail["blocking_reasons"],
                    # Genuine blocking reasons only; sequencing lives in
                    # waiting_reasons and the full set in reasons (ADR-0023).
                    "blockers": detail["blocking_reasons"],
                    "reasons": detail["reasons"],
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
        ready: list[dict[str, Any]] = []
        waiting: list[dict[str, Any]] = []
        blocked: list[dict[str, Any]] = []
        in_progress: list[dict[str, Any]] = []
        terminal: list[dict[str, Any]] = []
        admission_draft = bool(db.get_meta("admission_draft", False))
        for task in db.tasks():
            detail = task_readiness_detail(db, task, workspace)
            classification = _task_classification(task, detail)
            item = {
                "id": task["id"],
                "title": task["title"],
                "wave_id": task["wave_id"],
                "target_id": task["target_id"],
                "repository_id": task.get("repository_id"),
                "waiting_reasons": detail["waiting_reasons"],
                "blocking_reasons": detail["blocking_reasons"],
                # Genuine blocking reasons only (ADR-0023); ordering waits are
                # never blockers. The full machine-readable set is `reasons`.
                "blockers": detail["blocking_reasons"],
                "reasons": detail["reasons"],
            }
            if admission_draft:
                # An unadmitted draft cannot execute anything: that is a
                # genuine blocker on every task, not sequencing.
                item["blocking_reasons"] = detail["blocking_reasons"] + ["admission_draft"]
                item["blockers"] = item["blocking_reasons"]
                item["reasons"] = detail["reasons"] + ["admission_draft"]
                blocked.append(item)
            elif classification == "in_progress":
                # Already claimed or executing: not claimable, but neither
                # waiting nor blocked (ADR-0023).
                item["runtime_state"] = task["runtime_state"]
                in_progress.append(item)
            elif classification == "terminal":
                # COMPLETED/CANCELLED work is done, not blocked.
                item["runtime_state"] = task["runtime_state"]
                terminal.append(item)
            elif classification == "ready":
                ready.append(item)
            elif classification == "blocked":
                blocked.append(item)
            else:
                waiting.append(item)
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
            "waiting": waiting,
            "blocked": blocked,
            "in_progress": in_progress,
            "terminal": terminal,
            "current": _current_work(db.tasks()),
            "runtime_split_children": children,
            "definition_status": "draft" if admission_draft else None,
            "admission_draft": admission_draft,
        }
    finally:
        db.close()


def _claim_autonomy_projection(
    task: dict[str, Any], lease: dict[str, Any]
) -> dict[str, Any] | None:
    """Emit autonomy_action_id + packet skeleton. No autonomy-side mutation.

    Returns None rather than raising. The caller invokes this *after* the task
    has durably transitioned to LEASED and the ledger event is on disk, so any
    exception escaping here would abandon a lease no worker ever received:
    the task reads in_progress while the caller sees a failed claim. This is a
    projection, never an authority -- ``contract_mapper.require_coherent_actions``
    deliberately raises ContractActionError on an incoherent action set, and that
    is a fact about the contract, not a reason to lose the claim.
    """

    path = task.get("source_contract_path")
    if not path or not Path(path).is_file():
        return None
    pe_root = Path(__file__).resolve().parents[4]
    mapper = pe_root / "integrations" / "autonomy-control-plane"
    if str(pe_root) not in sys.path:
        sys.path.append(str(pe_root))
    if str(mapper) not in sys.path:
        sys.path.insert(0, str(mapper))
    try:
        from contract_mapper import map_program_contract

        contract = load_json(Path(path))
        mapped = map_program_contract(
            {
                **contract,
                "task_id": task["id"],
                "base_sha": lease.get("base_sha"),
                "branch": lease.get("branch"),
                "program_digest": contract.get("program_digest"),
            },
            adapter_id="controller",
            attempt_number=1,
        )
        ids = mapped["ids"]
    except Exception as exc:
        # Explicit, not silent: a broken mapper and "this task has no contract
        # to project" must not look identical to whoever reads the lease. The
        # claim still stands -- that is the whole point of the guard.
        return {"autonomy_projection_error": f"{type(exc).__name__}: {exc}"}
    return {
        "autonomy_action_id": ids["action_id"],
        "autonomy_packet_skeleton": {
            "campaign_id": ids["campaign_id"],
            "graph_id": ids["graph_id"],
            "action_id": ids["action_id"],
        },
    }


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
            # Same-repository tasks may hold concurrent leases: dependency,
            # resource, path, root-Autonomy claim, worktree, and provider
            # constraints decide parallelism. Only a duplicate active lease
            # for the *same task* is denied here.
            raise ControllerError(f"task already has an active lease: {task_id}") from exc
        db.update_task(
            task_id, base_sha=base_sha, branch=branch, lease_id=lease_id, last_error=None
        )
        db.transition_task(task_id, "LEASED")
        ledger.append("TASK_LEASED", holder, lease)
        projection = _claim_autonomy_projection(task, lease)
        if projection is not None:
            lease = {**lease, **projection}
        return lease
    finally:
        db.close()


def _add_task_worktree(
    repo_path: Path, worktree: Path, lease: dict[str, Any]
) -> subprocess.CompletedProcess[str]:
    return run_git(
        repo_path,
        "worktree",
        "add",
        "-b",
        lease["branch"],
        str(worktree),
        lease["base_sha"],
        check=False,
    )


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
            _stale_and_release(db, task_id, lease, "repository_state_changed")
            raise ControllerError("repository state changed after reconciliation")
        # Campaign lineage (an existing campaign/<id> integration branch) means
        # task bases come from that branch, not the checked-out HEAD — the
        # equality check below only applies to standalone runtimes. STACK.json
        # is publication topology and never decides execution lineage.
        integration_branch = _campaign_integration_branch(workspace)
        campaign_lineage = bool(
            integration_branch
            and run_git(
                repo_path, "rev-parse", "--verify", f"refs/heads/{integration_branch}", check=False
            ).returncode
            == 0
        )
        current_head = run_git(repo_path, "rev-parse", "HEAD").stdout.strip()
        has_base = run_git(repo_path, "cat-file", "-t", lease["base_sha"], check=False)
        if has_base.returncode != 0 or has_base.stdout.strip() != "commit":
            _stale_and_release(db, task_id, lease, "lease_base_missing")
            raise ControllerError("lease base_sha is not a commit in the repository")
        if not campaign_lineage and current_head != lease["base_sha"]:
            _stale_and_release(db, task_id, lease, "repository_state_changed")
            raise ControllerError("repository state changed after reconciliation")
        worktree = workspace / "worktrees" / task_id
        reused = False
        recovered = False
        if worktree.exists():
            if not _worktree_matches_lease(worktree, lease, repo_path):
                raise ControllerError(f"worktree already exists: {worktree}")
            reused = True
        else:
            result = _add_task_worktree(repo_path, worktree, lease)
            if result.returncode != 0:
                # Residue from an interrupted attempt — the branch, the git
                # worktree registration, or the directory — is recoverable, and
                # recreating a task worktree must not depend on manual cleanup.
                clean_task_execution(workspace, repo_path, task_id, branch=lease["branch"])
                recovered = True
                result = _add_task_worktree(repo_path, worktree, lease)
            if result.returncode != 0:
                raise ControllerError(
                    "failed to create worktree for "
                    f"{task_id}: {result.stderr.strip() or result.stdout.strip()} "
                    f"(worktree={worktree}, branch={lease['branch']}, "
                    f"base_sha={lease['base_sha']}; residue cleanup already attempted — "
                    "run `pec fresh-workspace` to reset every task worktree)"
                )
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
                "reused": reused,
                "recovered": recovered,
            },
        )
        return {
            "task_id": task_id,
            "worktree": str(worktree),
            "branch": lease["branch"],
            "base_sha": lease["base_sha"],
            "reused": reused,
            "recovered": recovered,
        }
    finally:
        db.close()


def _stale_and_release(db: StateDB, task_id: str, lease: dict[str, Any], error: str) -> None:
    """STALE the task AND release its lease, so re-claiming is possible.

    A STALE transition that kept the lease made the task unclaimable until the
    lease TTL expired: `task_readiness` reported task_already_leased and
    `claim` collided, while `recover` only handles expired leases.
    """
    db.transition_task(task_id, "STALE", last_error=error)
    db.release_lease(str(lease["lease_id"]))


def _worktree_matches_lease(worktree: Path, lease: dict[str, Any], repo_path: Path) -> bool:
    """Reuse a leftover task worktree only while it still belongs to this lease.

    Belonging means the lease's branch is checked out AND the lease base is in
    the worktree's ancestry. The branch name alone is deterministic per task,
    so after STALE -> re-claim at a newer base the old worktree carried the
    right name on the wrong lineage and was reused as if it were current.
    """
    if not ((worktree / ".git").exists() or (worktree / ".git").is_file()):
        return False
    listed = run_git(repo_path, "worktree", "list", "--porcelain", check=False)
    if listed.returncode != 0:
        return False
    text = listed.stdout or ""
    if not any(candidate in text for candidate in {str(worktree), str(worktree.resolve())}):
        return False
    branch = run_git(worktree, "rev-parse", "--abbrev-ref", "HEAD", check=False)
    if branch.returncode != 0 or branch.stdout.strip() != str(lease.get("branch") or ""):
        return False
    ancestry = run_git(
        worktree,
        "merge-base",
        "--is-ancestor",
        str(lease.get("base_sha") or ""),
        "HEAD",
        check=False,
    )
    return ancestry.returncode == 0


def start_task(workspace: Path, task_id: str, actor: str) -> dict[str, Any]:
    db, ledger = open_runtime(workspace)
    try:
        task = db.task(task_id)
        if task is None:
            raise ControllerError(f"unknown task: {task_id}")
        state = str(task["runtime_state"] or "")
        if state == "VERIFYING":
            # verify() is synchronous. VERIFYING after a crashed or abandoned
            # campaign process is residue, not an in-flight verifier. Land
            # FAILED so a new attempt can start (VERIFYING → EXECUTING is
            # not a legal edge).
            db.transition_task(task_id, "FAILED", last_error="verify_interrupted")
            task = db.task(task_id)
            if task is None:
                raise ControllerError(f"unknown task: {task_id}")
            state = "FAILED"
        retrying = state == "FAILED" and bool(task.get("rendered_contract_path"))
        if not retrying and state != "CONTRACTED":
            raise ControllerError("task must be CONTRACTED")
        if retrying and db.active_lease_for_task(task_id) is None:
            # fail_task released the writer lease. A retry that starts without
            # re-claiming reaches verify with no lease and is FAILED again on
            # the lease gate -- a guaranteed dead end, so refuse it here.
            raise ControllerError(
                "FAILED task has no active lease; run `pec claim` before `pec start` to retry"
            )
        if retrying:
            budget = _max_attempts(task)
            attempts = int(task.get("attempts") or 0)
            if attempts >= budget:
                db.transition_task(task_id, "CANCELLED", last_error="RETRY_BUDGET_EXHAUSTED")
                lease = db.active_lease_for_task(task_id)
                if lease:
                    db.release_lease(lease["lease_id"])
                    db.update_task(task_id, lease_id=None)
                ledger.append(
                    "TASK_CANCELLED",
                    actor,
                    {
                        "task_id": task_id,
                        "reason": "RETRY_BUDGET_EXHAUSTED",
                        "attempts": attempts,
                        "max_attempts": budget,
                    },
                )
                raise ControllerError(
                    f"retry budget exhausted for {task_id}: {attempts} attempt(s) recorded, "
                    f"risk tier allows {budget}; task CANCELLED"
                )
        _require_stack_proof_reentry(workspace, str(task_id))
        _require_ledger_integrity(ledger)
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
        if task["runtime_state"] != "EXECUTING":
            raise ControllerError(
                f"task cannot submit from state {task['runtime_state']}; an attempt is "
                "recorded only for a task that `pec start` moved to EXECUTING"
            )
        _require_ledger_integrity(ledger)
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
        submitted = {
            "status": "SUBMITTED",
            "task_id": task_id,
            "attempt": attempt,
            "receipt": str(target),
        }
        from .signals import publish_controller_event

        submitted["signal"] = publish_controller_event(
            workspace, event="record-attempt", receipt=submitted
        )
        return submitted
    finally:
        db.close()


WIRING_PATHS = frozenset({".cursor-commands", ".cursor/plans"})
WIRING_PREFIXES = (
    ".cursor-commands/",
    ".cursor/plans/",
    ".cursor/governance/",
    ".cursor/rules/",
    ".claude/",
    ".vscode/",
)


def _is_wiring_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized.rstrip("/") in WIRING_PATHS:
        return True
    return any(normalized.startswith(prefix) for prefix in WIRING_PREFIXES)


def _changed_paths(worktree: Path, base_sha: str | None = None) -> list[str]:
    """Union of dirty working-tree changes and committed work since the base.

    The worker contract allows both styles: leave the worktree dirty, or
    commit on the task branch. Either way every touched path must be declared
    in the Attempt Receipt and stay inside the Source Contract's writable
    paths. Governance wiring links created by ensure_workspace_wired are not
    worker mutations.
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
        paths.add(path.replace("\\", "/"))
        if status_code[0] in {"R", "C"} and index + 1 < len(parts):
            # `R  <new>\0<old>\0`: this entry names the NEW path; the next field
            # is the old one. Both are touched paths -- a rename INTO a
            # non-writable directory must fail the scope gate, and the old
            # path is a deletion the declared set must include.
            index += 1
            paths.add(parts[index].replace("\\", "/"))
        index += 1
    if base_sha:
        committed = run_git(
            worktree, "diff", "--name-only", f"{base_sha}..HEAD", check=False
        ).stdout
        for line in committed.splitlines():
            if line.strip():
                paths.add(line.strip().replace("\\", "/"))
    return sorted(path for path in paths if path and not _is_wiring_path(path))


def _observed_file_digests(worktree: Path, changed: list[str]) -> dict[str, str]:
    """Content identity of every observed change, as verified.

    The verdict is about these bytes. Recording them lets integration prove
    that what it lands is byte-identical to what was verified, instead of
    trusting that nothing touched the tree between the verdict and the commit.
    """
    digests: dict[str, str] = {}
    for path in changed:
        target = worktree / path
        if target.is_symlink():
            digests[path] = "symlink"
        elif target.is_dir():
            digests[path] = "directory"
        elif target.is_file():
            digests[path] = "sha256:" + hashlib.sha256(target.read_bytes()).hexdigest()
        else:
            digests[path] = "absent"
    return digests


def _blob_digest(repo_path: Path, revision: str, path: str) -> str:
    """Content identity of `path` at `revision`, in the same vocabulary."""
    exists = run_git(repo_path, "cat-file", "-e", f"{revision}:{path}", check=False)
    if exists.returncode != 0:
        return "absent"
    kind = run_git(repo_path, "cat-file", "-t", f"{revision}:{path}", check=False).stdout.strip()
    if kind == "tree":
        return "directory"
    mode = run_git(repo_path, "ls-tree", revision, "--", path, check=False).stdout.split(" ", 1)[0]
    if mode == "120000":
        return "symlink"
    completed = subprocess.run(
        ["git", "-C", str(repo_path), "show", f"{revision}:{path}"],
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return "absent"
    return "sha256:" + hashlib.sha256(completed.stdout).hexdigest()


def _require_candidate_matches_verification(
    workspace: Path,
    task: dict[str, Any],
    attempt: dict[str, Any] | None,
    repo_path: Path,
    candidate_sha: str,
) -> dict[str, Any]:
    """The integrated candidate must be the verified state, byte for byte.

    Verification ran against a working tree; the candidate is a commit made
    afterwards. Nothing else binds the two, so this does: every observed path
    must be committed, nothing else may be, and each committed blob must carry
    the digest the verdict recorded. A drift leaves the task PASSED_LOCAL with
    its candidate preserved for diagnosis rather than landing unverified bytes.
    """
    task_id = str(task["id"])
    verification = _verified_this_attempt(workspace, task, attempt)
    if not verification or verification.get("verdict") != "PASSED_LOCAL":
        raise ControllerError(
            f"{task_id}: no PASSED_LOCAL verification for the current attempt; refuse integration"
        )
    base_sha = str(task.get("base_sha") or "")
    committed = sorted(
        line.strip().replace("\\", "/")
        for line in run_git(
            repo_path, "diff", "--name-only", f"{base_sha}..{candidate_sha}", check=False
        ).stdout.splitlines()
        if line.strip() and not _is_wiring_path(line.strip())
    )
    observed = sorted(set(verification.get("observed_changed_files") or []))
    if committed != observed:
        raise ControllerError(
            f"{task_id}: integrated diff does not match the verified changes; "
            f"verified={observed} committed={committed}; task remains PASSED_LOCAL"
        )
    worktree = Path(str(task.get("worktree") or ""))
    if worktree.is_dir():
        pending = _changed_paths(worktree, None)
        if pending:
            raise ControllerError(
                f"{task_id}: verified worktree still carries uncommitted changes {pending}; "
                "refuse to integrate a candidate that is not the verified state"
            )
    digests = verification.get("observed_file_digests") or {}
    for path, expected in sorted(digests.items()):
        actual = _blob_digest(repo_path, candidate_sha, path)
        if actual != expected:
            raise ControllerError(
                f"{task_id}: {path} at candidate {candidate_sha[:12]} is {actual}, "
                f"verified as {expected}; refuse to integrate unverified bytes"
            )
    return verification


def _run_validation(command: str, worktree: Path) -> dict[str, Any]:
    return run_validation_command(command, worktree, exec_env=resolve_exec_env(worktree))


DOD_GATES = (
    "target_and_scope_verified",
    "implementation_complete",
    "no_scope_drift",
    "validation_honest",
    "mandatory_checks_green",
    "final_state_hygienic",
    "handoff_verified",
)


def _command_runnable(command: str) -> bool:
    token = command.strip().split(None, 1)[0] if command.strip() else ""
    if not token:
        return False
    if token in {"python3", "python", "make", "bash", "sh"}:
        return shutil.which(token) is not None or token in {"python3", "python"}
    return shutil.which(token) is not None or Path(token).exists()


def _preflight2_gates(commands: list[str], declared: list[str] | None = None) -> dict[str, str]:
    """Inventory, blocking and coverage of the contract's required commands.

    `inventory` and `coverage` used to be the literal "PASS" whenever any
    command existed. Inventory now means every required command is a
    well-formed, non-empty command line; coverage means every validation the
    contract declares is among the required commands (a declared validation
    with no command is uncovered).
    """
    if not commands:
        return {}
    well_formed = [
        bool(command.strip()) and not command.strip().startswith("#") for command in commands
    ]
    runnable = [_command_runnable(command) for command in commands]
    declared_commands = [str(item).strip() for item in (declared or []) if str(item).strip()]
    required = {command.strip() for command in commands}
    covered = all(item in required for item in declared_commands)
    return {
        "preflight2_inventory": "PASS" if all(well_formed) else "INCOMPLETE",
        "preflight2_blocking": "PASS" if runnable and all(runnable) else "INCOMPLETE",
        "preflight2_coverage": "PASS" if covered else "INCOMPLETE",
    }


def _unenforced_prohibitions(workspace: Path) -> list[dict[str, Any]]:
    """Prohibitions the do_not_build gate cannot evaluate.

    That gate matches file paths. A prohibition with no usable pattern - an
    architecture law such as "a second Program Execution runtime or Controller"
    - is enforced by review and conformance instead, and the gate is silent
    about it. Silence is what makes a PASS read wider than it is, so the
    verification receipt names them.

    Derived as the complement of the set the gate actually matches, rather than
    by reading `kind`, so a legacy entry carrying neither a kind nor a pattern
    is reported here too instead of vanishing between the two.
    """
    lock_path = workspace / "runtime" / "program-lock.json"
    if not lock_path.is_file():
        return []
    entries = (load_json(lock_path).get("do_not_build") or {}).get("prohibited_primary_paths") or []
    unenforced: list[dict[str, Any]] = []
    for item in entries:
        if not isinstance(item, dict) or item.get("path_or_pattern"):
            continue
        unenforced.append(
            {
                "id": str(item.get("id") or ""),
                "statement": str(item.get("statement") or ""),
                "enforced_by": str(item.get("detection") or "review_and_conformance"),
            }
        )
    return unenforced


def _wiring_gate(contract: dict[str, Any], task: dict[str, Any]) -> str:
    source = task.get("source") if isinstance(task.get("source"), dict) else {}
    consumers = contract.get("consumers") or source.get("consumers") or []
    entrypoints = contract.get("entrypoints") or source.get("entrypoints") or []
    if not consumers and not entrypoints:
        return "PASS"
    if consumers and entrypoints:
        return "PASS"
    return "INCOMPLETE"


def _kernel_and_pec_verdict(gates: dict[str, str]) -> tuple[str, str]:
    values = list(gates.values())
    if "STALE" in values:
        return "FAIL", "STALE"
    if "INCOMPLETE" in values:
        return "INCOMPLETE", "FAILED"
    if values and all(value == "PASS" for value in values):
        return "PASS", "PASSED_LOCAL"
    return "FAIL", "FAILED"


def _dod_gates_from_verify(
    gates: dict[str, str],
    *,
    kernel_verdict: str,
    candidate_sha: str | None,
) -> dict[str, str]:
    def _and(*names: str) -> str:
        vals = [gates.get(name, "FAIL") for name in names]
        if "INCOMPLETE" in vals:
            return "INCOMPLETE"
        if all(value == "PASS" for value in vals):
            return "PASS"
        return "FAIL"

    honest = gates.get("validation", "FAIL")
    if honest == "INCOMPLETE":
        validation_honest = "INCOMPLETE"
        mandatory = "INCOMPLETE"
    elif honest == "PASS" and gates.get("worker_validation_claim") == "PASS":
        validation_honest = "PASS"
        mandatory = "PASS"
    else:
        validation_honest = "FAIL"
        mandatory = "FAIL"
    return {
        "target_and_scope_verified": _and("program_lock", "contract", "scope"),
        "implementation_complete": _and("changed_files_exact", "scope"),
        "no_scope_drift": _and("scope", "do_not_build"),
        "validation_honest": validation_honest,
        "mandatory_checks_green": mandatory,
        "final_state_hygienic": gates.get("symlink", "FAIL"),
        "handoff_verified": (
            "PASS"
            if gates.get("receipt_binding") == "PASS" and candidate_sha
            else ("INCOMPLETE" if kernel_verdict == "INCOMPLETE" else "FAIL")
        ),
    }


def _latest_verification(workspace: Path, task_id: str) -> dict[str, Any]:
    path = workspace / "receipts" / "verification" / f"{task_id}.json"
    if not path.is_file():
        return {}
    return load_json(path)


def _dod_complete(verification: dict[str, Any]) -> bool:
    if verification.get("kernel_verdict") != "PASS":
        return False
    dod = verification.get("dod_gates") or {}
    return all(dod.get(name) == "PASS" for name in DOD_GATES)


def verification_receipt_path(workspace: Path, task_id: str) -> Path:
    return workspace.resolve() / "receipts" / "verification" / f"{task_id}.json"


def _verified_this_attempt(
    workspace: Path, task: dict[str, Any], attempt: dict[str, Any] | None
) -> dict[str, Any] | None:
    """Return the receipt already produced for the task's current attempt.

    An attempt gets exactly one controller verification. Re-invoking `verify`
    after that verdict changed the task state is a resumable duplicate, not a
    new verification, so the recorded verdict is replayed instead of a second
    run against a task the state machine no longer accepts.
    """
    path = verification_receipt_path(workspace, task["id"])
    if not path.is_file():
        return None
    try:
        receipt = load_json(path)
    except (json.JSONDecodeError, OSError):
        return None
    if str(receipt.get("task_id")) != str(task["id"]):
        return None
    digest = task.get("rendered_contract_digest")
    if digest and receipt.get("contract_digest") and receipt["contract_digest"] != digest:
        return None
    # The attempts table records no candidate_sha, so comparing against it was
    # dead: a receipt from an earlier attempt replayed as this one's verdict.
    # The receipt names the attempt it verified through its evidence id.
    if attempt is not None:
        expected = f"EVID-RUNTIME-{task['id']}-{int(attempt['attempt_number']):03d}"
        if str(receipt.get("evidence_id") or "") != expected:
            return None
    return dict(receipt)


def _verify_state_error(task: dict[str, Any] | None, task_id: str) -> ControllerError:
    """Explain how the task reached a state `verify` cannot act on."""
    if task is None:
        return ControllerError(
            f"cannot verify {task_id}: no such task in this runtime. "
            "Expected state SUBMITTED. Suggested next action: `pec status` to list "
            "task ids, then bootstrap or reconcile the correct blueprint. Retry is safe."
        )
    state = task["runtime_state"]
    guidance = {
        "WAITING": (
            "runtime prerequisites (dependencies, waves, gates) have not yet been "
            "satisfied; run `pec next` to see waiting reasons"
        ),
        "BLOCKED": "dependencies or definition readiness are unmet; run `pec next` to see blockers",
        "ELIGIBLE": "the task was never claimed; run `pec claim` then prepare/render/start",
        "LEASED": "the worktree is not prepared; run `pec prepare`",
        "PREPARED": "no contract is rendered; run `pec render-contract`",
        "CONTRACTED": "execution never started; run `pec start` then record an attempt",
        "EXECUTING": "the worker has not submitted an attempt; run `pec record-attempt`",
        "VERIFYING": "a verification is already in flight for this attempt; wait for it to finish",
        "PASSED_LOCAL": "this attempt already verified PASS; run `pec complete`",
        "FAILED": (
            "this attempt already verified FAIL and the receipt is preserved; "
            "repair the work and run `pec start` to retry, which submits a new attempt"
        ),
        "STALE": "the lease or repository moved; the lease was released, so re-claim the task",
        "CANCELLED": "the task is terminal and cannot be verified",
        "COMPLETED": "the task is already complete; verification is not repeated",
    }.get(state, "no transition to VERIFYING exists from this state")
    return ControllerError(
        f"cannot verify {task_id}: task is {state}, expected SUBMITTED. "
        f"Why: {guidance}. "
        f"Last error: {task.get('last_error') or 'none'}. "
        f"Attempts recorded: {task.get('attempts', 0)}. "
        f"Retry safe: {'yes' if state in {'FAILED', 'PASSED_LOCAL', 'COMPLETED'} else 'not as-is'}."
    )


def verify_attempt(workspace: Path, task_id: str) -> dict[str, Any]:
    db, ledger = open_runtime(workspace)
    try:
        task = db.task(task_id)
        if task is None or task["runtime_state"] != "SUBMITTED":
            replay = (
                None
                if task is None
                else _verified_this_attempt(workspace, task, db.latest_attempt(task_id))
            )
            if replay is not None:
                replay["replayed"] = True
                replay["runtime_state"] = task["runtime_state"]
                return replay
            raise _verify_state_error(task, task_id)
        db.transition_task(task_id, "VERIFYING")
        lease = db.active_lease_for_task(task_id)
        attempt = db.latest_attempt(task_id)
        gates: dict[str, str] = {}
        gates["program_lock"] = "PASS" if lock_trusted_for_task(workspace, task_id) else "STALE"
        ledger_ok, _ = ledger.verify()
        gates["ledger"] = "PASS" if ledger_ok else "FAIL"
        gates["lease"] = (
            "PASS" if lease and lease.get("lease_id") == task.get("lease_id") else "FAIL"
        )
        contract: dict[str, Any] = {}
        if task.get("rendered_contract_path") and Path(task["rendered_contract_path"]).is_file():
            contract = load_json(Path(task["rendered_contract_path"]))
            # Deliberately broad and fail-CLOSED: schema violation, a missing
            # contract_digest, and a digest mismatch are all the same verdict
            # here -- the contract gate is FAIL. This runs inside gate
            # evaluation, where raising would abandon the whole verdict.
            # nosemgrep: l9.baseline.python.broad-except
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
        observed_digests: dict[str, str] = {}
        validations: list[dict[str, Any]] = []
        candidate_sha = None
        # What the do_not_build gate does NOT cover. Semantic prohibitions carry
        # no path to match (W8/S1), so a PASS from that gate means "the changed
        # paths are clean", never "no prohibition was violated". Saying which
        # rules it could not evaluate keeps the receipt from reading as the
        # broader claim. Derived from the lock, so it stands even when the
        # worktree is gone and every gate is FAIL.
        unenforced_prohibitions = _unenforced_prohibitions(workspace)
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
            observed_digests = _observed_file_digests(worktree, changed)
            declared = sorted(set(receipt.get("changed_files") or []))
            gates["changed_files_exact"] = "PASS" if declared == changed else "FAIL"
            patterns = contract.get("writable_paths") or []
            try:
                in_scope = changed and all(path_allowed(path, patterns) for path in changed)
            except ContractError:
                # A touched path the contract grammar refuses outright (git or
                # controller internals) is a scope FAIL, not a traceback that
                # leaves the task VERIFYING.
                in_scope = False
            gates["scope"] = "PASS" if in_scope else "FAIL"
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
                        # An entry that will not parse as a repo path is not a
                        # path prohibition, and substring-matching it against a
                        # filename was never enforcement: a sentence does not
                        # appear inside a path, so the gate passed having
                        # matched nothing. Semantic prohibitions now travel in
                        # their own channel (compiler/prohibition_kind.py) and
                        # carry no path_or_pattern, so they never arrive here.
                        continue
            gates["do_not_build"] = "FAIL" if dnb_hit else "PASS"
            # A dangling symlink is still a symlink; Path.exists() follows the
            # link and reports False for one, which used to skip the check.
            gates["symlink"] = (
                "PASS" if not any((worktree / path).is_symlink() for path in changed) else "FAIL"
            )
            claimed_results = receipt.get("validation_results") or []
            claimed_commands = [item.get("command") for item in claimed_results]
            required_commands = contract.get("validation_commands") or []
            if not required_commands:
                # A claim gate that checked nothing must not report PASS. With no
                # commands both sides are empty, so the equality holds vacuously
                # and `all([])` is True - the gate would assert the worker's
                # validation claim on zero evidence. Today `validation` is
                # INCOMPLETE in the same breath so the verdict is already
                # refused, but that makes the safety a property of a sibling
                # gate rather than of this one. Say INCOMPLETE here too, so the
                # honest answer does not depend on which gate is read.
                gates["worker_validation_claim"] = "INCOMPLETE"
            else:
                gates["worker_validation_claim"] = (
                    "PASS"
                    if claimed_commands == required_commands
                    and all(item.get("status") == "PASS" for item in claimed_results)
                    else "FAIL"
                )
            if required_commands:
                lock_task = next(
                    (item for item in lock.get("tasks") or [] if item.get("id") == task_id), {}
                )
                declared_validations = [
                    str(item.get("command_or_inspection") or "")
                    for item in lock_task.get("validation") or []
                    if isinstance(item, dict)
                    and item.get("method") in {"command", "command_and_inspection"}
                ]
                gates.update(
                    _preflight2_gates(
                        [str(command) for command in required_commands],
                        declared=declared_validations,
                    )
                )
                validations = [_run_validation(command, worktree) for command in required_commands]
                gates["validation"] = (
                    "PASS"
                    if validations and all(item["status"] == "PASS" for item in validations)
                    else "FAIL"
                )
            else:
                gates["validation"] = "INCOMPLETE"
            gates["wiring"] = _wiring_gate(contract, task)
            # Controller-owned candidate identity. The worker cannot git add or
            # git commit (permission_renderer denials) and must return
            # candidate_sha JSON null. HEAD after the attempt is the identity.
            candidate_sha = run_git(worktree, "rev-parse", "HEAD").stdout.strip()
        gates["residual_unknowns"] = (
            "PASS" if not (receipt.get("residual_unknowns") or []) else "BLOCKED"
        )
        kernel_verdict, verdict = _kernel_and_pec_verdict(gates)
        dod_gates = _dod_gates_from_verify(
            gates, kernel_verdict=kernel_verdict, candidate_sha=candidate_sha
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
            "observed_file_digests": observed_digests,
            "validations": validations,
            "unenforced_prohibitions": unenforced_prohibitions,
            "gates": gates,
            "kernel_verdict": kernel_verdict,
            "dod_gates": dod_gates,
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
        from .signals import publish_controller_event

        verification["signal"] = publish_controller_event(
            workspace, event="verify", receipt=verification
        )
        return verification
    finally:
        db.close()


FAILABLE_RUNTIME_STATES = {
    "LEASED",
    "PREPARED",
    "CONTRACTED",
    "EXECUTING",
    "SUBMITTED",
    "VERIFYING",
}


def fail_task(workspace: Path, task_id: str, reason: str, actor: str) -> dict[str, Any]:
    """Canonical failure path for a task that dies after claim.

    One operation, whatever stage the failure happened at (LEASED through
    VERIFYING): record the failure reason, append the ledger event, land the
    task in FAILED (retryable), and release the Controller writer lease.
    The task worktree and every attempt/grant receipt are preserved as
    evidence — nothing is cleaned up here. Root-Autonomy lease revocation is
    the caller's obligation through the task's grant receipt; the Controller
    owns program state only.
    """
    db, ledger = open_runtime(workspace)
    try:
        task = db.task(task_id)
        if task is None:
            raise ControllerError(f"unknown task: {task_id}")
        state = str(task["runtime_state"] or "")
        transitioned = False
        if state in FAILABLE_RUNTIME_STATES:
            db.transition_task(task_id, "FAILED", last_error=reason)
            transitioned = True
        elif state != "FAILED":
            raise ControllerError(
                f"task {task_id} is {state}; canonical failure applies only to "
                f"{sorted(FAILABLE_RUNTIME_STATES)} or an already-FAILED task"
            )
        lease = db.active_lease_for_task(task_id)
        lease_id = None
        if lease is not None:
            lease_id = str(lease["lease_id"])
            db.release_lease(lease_id)
            db.update_task(task_id, lease_id=None)
        ledger.append(
            "TASK_FAILED",
            actor,
            {
                "task_id": task_id,
                "reason": reason,
                "previous_state": state,
                "lease_id": lease_id,
                "lease_released": lease_id is not None,
                "worktree_preserved": task.get("worktree"),
            },
        )
        return {
            "status": "FAILED",
            "task_id": task_id,
            "reason": reason,
            "previous_state": state,
            "transitioned": transitioned,
            "lease_released": lease_id is not None,
            "lease_id": lease_id,
        }
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
        _require_ledger_integrity(ledger)
        if not evidence_ids or not all(_evidence_valid(db, item) for item in evidence_ids):
            raise ControllerError("gate evaluation requires valid evidence")
        definition = gate.get("definition") or {}
        if result == "PASS":
            # Validity is not relevance. A PASS is a claim about THIS gate's
            # scope, so it needs the evidence the gate itself names and at
            # least one item that supports a task inside the gate's scope.
            required = [str(item) for item in definition.get("required_evidence_ids") or []]
            missing = sorted(set(required) - set(evidence_ids))
            if missing:
                raise ControllerError(
                    f"gate {gate_id} PASS requires its declared evidence; missing {missing}"
                )
            scope_tasks = {
                str(item) for item in (definition.get("scope") or {}).get("task_ids") or []
            }
            if scope_tasks and not _evidence_supports(db, list(evidence_ids), scope_tasks):
                raise ControllerError(
                    f"gate {gate_id} PASS requires evidence supporting a task in its scope "
                    f"{sorted(scope_tasks)}; none of {sorted(set(evidence_ids))} does"
                )
            if scope_tasks and str(definition.get("class") or "") in EXECUTION_GATE_CLASSES:
                # An execution or validation gate closes over work that ran.
                # Planning evidence from the catalog supports the same task
                # and is valid, but it says nothing about the attempt; only the
                # Controller's own verification of an in-scope task does.
                if not _controller_verification_supports(db, list(evidence_ids), scope_tasks):
                    raise ControllerError(
                        f"gate {gate_id} ({definition.get('class')}) PASS requires Controller "
                        "verification evidence for a task in its scope; planning or "
                        "catalog evidence cannot close an execution gate"
                    )
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
        # Definition of Done is enforced per task at `complete_task`, never here:
        # a gate's scope spans every task it converges (`scope.task_ids`), and a
        # multi-task gate must be PASS-able while later tasks in its scope have
        # not run, because completing the first task requires the gate. The
        # loop that once stood here read a `task_ids` key the schema never
        # placed at the top level, so it was dead; made live it deadlocked
        # every multi-task campaign. Evidence validity for the PASS is
        # `_evidence_valid` above, which rejects FAIL/BLOCKED/UNKNOWN results.
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
        from .signals import publish_controller_event

        receipt["signal"] = publish_controller_event(
            workspace, event="evaluate-gate", receipt=receipt
        )
        return receipt
    finally:
        db.close()


def _integration_receipt_path(workspace: Path, task_id: str) -> Path:
    return workspace / "receipts" / "integration" / f"{task_id}.json"


def _integration_checkout(workspace: Path, repo_path: Path, branch: str) -> tuple[Path, bool]:
    """A working tree whose HEAD is the campaign integration branch.

    When the primary checkout is already on the branch, integrate there.
    Otherwise use a dedicated integration worktree (a branch cannot be
    checked out twice), created once and reused.
    """
    current = run_git(repo_path, "branch", "--show-current", check=False).stdout.strip()
    if current == branch:
        return repo_path, False
    integration_root = workspace / "integration" / branch.replace("/", "__")
    if integration_root.is_dir() and (integration_root / ".git").exists():
        checked = run_git(integration_root, "rev-parse", "--abbrev-ref", "HEAD", check=False)
        if checked.returncode == 0 and checked.stdout.strip() == branch:
            return integration_root, True
        raise ControllerError(f"integration worktree is not on {branch}: {integration_root}")
    integration_root.parent.mkdir(parents=True, exist_ok=True)
    added = run_git(repo_path, "worktree", "add", str(integration_root), branch, check=False)
    if added.returncode != 0:
        raise ControllerError(
            f"cannot create integration worktree for {branch}: "
            f"{added.stderr.strip() or added.stdout.strip()}"
        )
    return integration_root, True


def _integrate_candidate(
    db: StateDB,
    ledger: EventLedger,
    workspace: Path,
    task: dict[str, Any],
) -> dict[str, Any] | None:
    """Integrate a verified candidate into the campaign integration branch.

    PASSED_LOCAL is not COMPLETED for repo_local work until the verified
    candidate commit range is part of campaign/<campaign_id>. Deterministic
    order (ancestry order of the candidate range), abort-on-conflict with the
    partial git operation rolled back, an idempotency receipt binding the
    candidate SHA to the resulting campaign SHA, and a Controller repository
    record that tracks the accumulated integration head.

    Returns the integration receipt, or ``None`` when no campaign integration
    branch is in force (standalone runtimes keep their existing semantics).
    """
    task_id = str(task["id"])
    branch = _campaign_integration_branch(workspace)
    if branch is None or not task.get("repository_id"):
        return None
    repo = db.repository(task["repository_id"])
    if repo is None:
        raise ControllerError("repository not reconciled")
    repo_path = Path(repo["local_path"])
    if (
        run_git(repo_path, "rev-parse", "--verify", f"refs/heads/{branch}", check=False).returncode
        != 0
    ):
        return None
    task_branch = str(task.get("branch") or "")
    base_sha = str(task.get("base_sha") or "")
    if not task_branch or not base_sha:
        raise ControllerError(f"task {task_id} has no branch/base lineage to integrate")
    candidate = run_git(
        repo_path, "rev-parse", "--verify", f"refs/heads/{task_branch}", check=False
    )
    if candidate.returncode != 0:
        raise ControllerError(f"verified candidate branch missing: {task_branch}")
    candidate_sha = candidate.stdout.strip()
    receipt_path = _integration_receipt_path(workspace, task_id)
    if receipt_path.is_file():
        receipt = load_json(receipt_path)
        if receipt.get("candidate_sha") == candidate_sha:
            # Already integrated: replay safely without duplicating commits.
            return receipt
    descends = run_git(
        repo_path, "merge-base", "--is-ancestor", base_sha, candidate_sha, check=False
    )
    if descends.returncode != 0:
        raise ControllerError(
            f"candidate {candidate_sha} does not descend from task base {base_sha}"
        )
    _require_candidate_matches_verification(
        workspace, task, db.latest_attempt(task_id), repo_path, candidate_sha
    )
    tree, _ = _integration_checkout(workspace, repo_path, branch)
    if run_git(tree, "status", "--porcelain").stdout.strip():
        raise ControllerError(
            f"campaign integration worktree is dirty; refuse fan-in for {task_id}"
        )
    commits = [
        line.strip()
        for line in run_git(
            tree, "rev-list", "--reverse", f"{base_sha}..{candidate_sha}"
        ).stdout.splitlines()
        if line.strip()
    ]
    integrated: list[str] = []
    # Controller worktrees carry no committer identity and CI runners have no
    # global one; integration commits are Controller-owned, so bind the
    # Controller identity per invocation rather than inheriting ambient config.
    identity = (
        "-c",
        "user.name=Program Execution Controller",
        "-c",
        "user.email=pec-controller@l9.invalid",
    )
    for commit in commits:
        picked = run_git(
            tree, *identity, "cherry-pick", "--allow-empty-message", commit, check=False
        )
        if picked.returncode != 0:
            porcelain = run_git(tree, "status", "--porcelain", check=False).stdout.strip()
            if not porcelain:
                # The change is already present on the branch (a replay after a
                # crash between cherry-pick and receipt): skip, don't duplicate.
                skipped = run_git(tree, *identity, "cherry-pick", "--skip", check=False)
                if skipped.returncode == 0:
                    continue
            unmerged = any(
                line[:2] in {"UU", "AA", "DD", "AU", "UA", "DU", "UD"}
                for line in porcelain.splitlines()
            )
            run_git(tree, "cherry-pick", "--abort", check=False)
            git_error = (picked.stderr or picked.stdout).strip()[:2000]
            failure = {
                "task_id": task_id,
                "candidate_sha": candidate_sha,
                "base_sha": base_sha,
                "conflicting_commit": commit,
                "conflict": unmerged,
                "error": git_error,
            }
            ledger.append("TASK_INTEGRATION_FAILED", "controller", failure)
            kind = "integration conflict" if unmerged else "integration failure"
            first_line = git_error.splitlines()[0] if git_error else "no git output"
            raise ControllerError(
                f"{kind} for {task_id} at {commit} ({first_line}); "
                "candidate branch and worktree preserved, task remains PASSED_LOCAL"
            )
        integrated.append(commit)
    campaign_sha = run_git(tree, "rev-parse", "HEAD").stdout.strip()
    receipt = {
        "schema": "program-execution-controller.integration-receipt.v1",
        "task_id": task_id,
        "integration_branch": branch,
        "base_sha": base_sha,
        "candidate_sha": candidate_sha,
        "integrated_commits": integrated,
        "campaign_sha": campaign_sha,
        "integrated_at": utc_now(),
    }
    write_json(receipt_path, receipt)
    db.upsert_repository(str(task["repository_id"]), str(repo["target_id"]), head_sha=campaign_sha)
    ledger.append("TASK_INTEGRATED", "controller", receipt)
    return receipt


def complete_task(
    workspace: Path, task_id: str, actor: str, evidence_ids: list[str]
) -> dict[str, Any]:
    db, ledger = open_runtime(workspace)
    try:
        task = db.task(task_id)
        if task is None:
            raise ControllerError(f"unknown task: {task_id}")
        _require_ledger_integrity(ledger)
        if not evidence_ids or not all(_evidence_valid(db, item) for item in evidence_ids):
            raise ControllerError("task completion requires valid evidence")
        for gate_id in task["completion_gates"]:
            gate = db.gate(gate_id)
            if gate is None or not _gate_satisfied(db, gate):
                raise ControllerError(f"completion gate not satisfied: {gate_id}")
        integration: dict[str, Any] | None = None
        if task["execution_kind"] == "program_control":
            # New complete tasks initialize WAITING (ADR-0023); legacy
            # persisted runtimes may still hold BLOCKED. Both promote through
            # the same readiness check.
            if task["runtime_state"] in {"WAITING", "BLOCKED"}:
                ok, reasons = task_readiness(db, task, workspace)
                if not ok:
                    raise ControllerError(
                        "program-control task is not eligible: " + ", ".join(reasons)
                    )
                db.transition_task(task_id, "ELIGIBLE")
            if task["runtime_state"] != "ELIGIBLE":
                task = db.task(task_id)
                if task is None or task["runtime_state"] != "ELIGIBLE":
                    raise ControllerError("program-control task must be ELIGIBLE")
            db.transition_task(task_id, "COMPLETED")
        else:
            if task["runtime_state"] != "PASSED_LOCAL":
                raise ControllerError("repository task must be PASSED_LOCAL before completion")
            attempt = db.latest_attempt(task_id)
            verification = _verified_this_attempt(workspace, task, attempt) or {}
            if not verification:
                raise ControllerError(
                    "no verification receipt for the current attempt; refuse completion"
                )
            # The completing evidence is this attempt's own verification, not
            # any valid evidence that happens to exist: the evidence id the
            # receipt minted must be supplied, still name this task, and still
            # carry the receipt's digest.
            verification_evidence = str(verification.get("evidence_id") or "")
            if verification_evidence not in set(evidence_ids):
                raise ControllerError(
                    f"task completion requires this attempt's verification evidence "
                    f"{verification_evidence!r}; got {sorted(set(evidence_ids))}"
                )
            recorded = db.evidence(verification_evidence) or {}
            if task_id not in set(recorded.get("supports") or []) or str(
                recorded.get("digest") or ""
            ) != str(verification.get("receipt_digest") or ""):
                raise ControllerError(
                    "verification evidence does not bind this task's receipt; refuse completion"
                )
            if not _dod_complete(verification):
                raise ControllerError(
                    "PASSED_LOCAL is not Done; Definition of Done required before complete"
                )
            # Verified fan-in first: a repo_local task is not COMPLETED until
            # its candidate range is integrated into the campaign integration
            # branch. An integration conflict raises here and leaves the task
            # PASSED_LOCAL with its candidate branch and worktree preserved.
            integration = _integrate_candidate(db, ledger, workspace, task)
            db.transition_task(task_id, "COMPLETED")
            lease = db.active_lease_for_task(task_id)
            if lease:
                db.release_lease(lease["lease_id"])
                db.update_task(task_id, lease_id=None)
        ledger.append("TASK_COMPLETED", actor, {"task_id": task_id, "evidence_ids": evidence_ids})
        result = {"status": "COMPLETED", "task_id": task_id, "evidence_ids": evidence_ids}
        if integration is not None:
            result["integration"] = integration
        return result
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
    # APPEND, never insert(0): `scripts` is a top-level name Program Execution
    # SHARES with the repository root, so a prepend hands PE's `scripts/` that
    # name process-wide. See peer_execution.imports.pe_script.
    if str(pe_root) not in sys.path:
        sys.path.append(str(pe_root))
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
        recommendation, facts = _program_recommendation(db, ledger)
        open_risks = facts["open_risks"]
        unresolved_decisions = facts["unresolved_decisions"]
        unresolved_unknowns = facts["unresolved_unknowns"]
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
        completion_blockers = (
            _campaign_completion_blockers(db, recommendation)
            if recommendation in TERMINAL_VERDICTS
            else {}
        )
        if completion_blockers:
            receipt["completion_blockers"] = completion_blockers
        # HANDOFF_PROTOCOL: a recommendation is not terminal acceptance. The
        # handoff reports what the Controller would recommend and leaves the
        # runtime active; `pec close`, invoked by the program owner, is the one
        # path that accepts or refuses a terminal verdict.
        receipt["campaign_status"] = read_campaign_status(workspace) or {}
        from .signals import publish_controller_event

        receipt["signal"] = publish_controller_event(
            workspace, event="export-handoff", receipt=receipt
        )
        return receipt
    finally:
        db.close()

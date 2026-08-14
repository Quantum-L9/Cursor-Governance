from __future__ import annotations

import argparse
import json
from pathlib import Path

from .contracts import (
    ContractError,
    draft_source_contract,
    register_source_contract,
    render_contract,
)
from .controller import (
    ControllerError,
    add_approval,
    bootstrap,
    claim_task,
    complete_task,
    evaluate_gate,
    export_handoff,
    next_tasks,
    open_runtime,
    prepare_worktree,
    reconcile_repositories,
    record_attempt,
    recover,
    release_lease,
    set_decision,
    set_halt,
    set_unknown,
    start_task,
    status,
    validate_runtime,
    verify_attempt,
)


def print_json(value) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pec", description="Program Execution Controller")
    sub = p.add_subparsers(dest="command", required=True)

    cmd = sub.add_parser("bootstrap")
    cmd.add_argument("--workspace", required=True, type=Path)
    cmd.add_argument("--blueprint", required=True, type=Path)

    cmd = sub.add_parser("validate")
    cmd.add_argument("--workspace", required=True, type=Path)

    cmd = sub.add_parser("reconcile")
    cmd.add_argument("--workspace", required=True, type=Path)
    cmd.add_argument("--repository", action="append", default=[], help="repository_id=/path")

    for name in ["status", "next"]:
        cmd = sub.add_parser(name)
        cmd.add_argument("--workspace", required=True, type=Path)

    cmd = sub.add_parser("draft-contract")
    cmd.add_argument("task_id")
    cmd.add_argument("--workspace", required=True, type=Path)
    cmd.add_argument("--output", required=True, type=Path)

    cmd = sub.add_parser("register-contract")
    cmd.add_argument("task_id")
    cmd.add_argument("--workspace", required=True, type=Path)
    cmd.add_argument("--file", required=True, type=Path)
    cmd.add_argument("--actor", required=True)
    cmd.add_argument("--replace", action="store_true")

    cmd = sub.add_parser("claim")
    cmd.add_argument("task_id")
    cmd.add_argument("--workspace", required=True, type=Path)
    cmd.add_argument("--holder", required=True)
    cmd.add_argument("--ttl-hours", type=int, default=8)

    cmd = sub.add_parser("prepare")
    cmd.add_argument("task_id")
    cmd.add_argument("--workspace", required=True, type=Path)

    cmd = sub.add_parser("render-contract")
    cmd.add_argument("task_id")
    cmd.add_argument("--workspace", required=True, type=Path)

    cmd = sub.add_parser("start")
    cmd.add_argument("task_id")
    cmd.add_argument("--workspace", required=True, type=Path)
    cmd.add_argument("--actor", required=True)

    cmd = sub.add_parser("record-attempt")
    cmd.add_argument("task_id")
    cmd.add_argument("--workspace", required=True, type=Path)
    cmd.add_argument("--receipt", required=True, type=Path)

    cmd = sub.add_parser("verify")
    cmd.add_argument("task_id")
    cmd.add_argument("--workspace", required=True, type=Path)

    cmd = sub.add_parser("complete")
    cmd.add_argument("task_id")
    cmd.add_argument("--workspace", required=True, type=Path)
    cmd.add_argument("--actor", required=True)
    cmd.add_argument("--evidence-id", action="append", default=[])

    cmd = sub.add_parser("release-lease")
    cmd.add_argument("task_id")
    cmd.add_argument("--workspace", required=True, type=Path)
    cmd.add_argument("--reason", required=True)
    cmd.add_argument("--actor", required=True)

    cmd = sub.add_parser("recover")
    cmd.add_argument("--workspace", required=True, type=Path)
    cmd.add_argument("--actor", required=True)

    cmd = sub.add_parser("add-approval")
    cmd.add_argument("--workspace", required=True, type=Path)
    cmd.add_argument("--file", required=True, type=Path)

    cmd = sub.add_parser("set-decision")
    cmd.add_argument("decision_id")
    cmd.add_argument("status", choices=["pending", "accepted", "rejected", "superseded"])
    cmd.add_argument("--workspace", required=True, type=Path)
    cmd.add_argument("--evidence-id", action="append", default=[])
    cmd.add_argument("--actor", required=True)

    cmd = sub.add_parser("set-unknown")
    cmd.add_argument("unknown_id")
    cmd.add_argument("status", choices=["open", "resolved", "accepted_risk", "superseded"])
    cmd.add_argument("--workspace", required=True, type=Path)
    cmd.add_argument("--evidence-id", action="append", default=[])
    cmd.add_argument("--actor", required=True)

    cmd = sub.add_parser("evaluate-gate")
    cmd.add_argument("gate_id")
    cmd.add_argument(
        "result", choices=["PASS", "FAIL", "BLOCKED", "UNKNOWN", "NOT_APPLICABLE_WITH_REASON"]
    )
    cmd.add_argument("--workspace", required=True, type=Path)
    cmd.add_argument("--evidence-id", action="append", default=[])
    cmd.add_argument("--method", required=True)
    cmd.add_argument("--actor", required=True)
    cmd.add_argument("--waiver-id")

    cmd = sub.add_parser("halt")
    cmd.add_argument("--workspace", required=True, type=Path)
    cmd.add_argument("--reason", required=True)
    cmd.add_argument("--actor", required=True)

    cmd = sub.add_parser("resume")
    cmd.add_argument("--workspace", required=True, type=Path)
    cmd.add_argument("--reason", required=True)
    cmd.add_argument("--actor", required=True)

    cmd = sub.add_parser("export-handoff")
    cmd.add_argument("--workspace", required=True, type=Path)
    cmd.add_argument("--actor", required=True)
    cmd.add_argument("--output", required=True, type=Path)

    cmd = sub.add_parser("plan-revision")
    cmd.add_argument("--workspace", required=True, type=Path)

    cmd = sub.add_parser("replan-propose")
    cmd.add_argument("revision_id")
    cmd.add_argument("--workspace", required=True, type=Path)
    cmd.add_argument("--program-id", required=True)
    cmd.add_argument("--trigger-evidence-id", action="append", default=[])
    cmd.add_argument("--affected-future-task-id", action="append", default=[])
    cmd.add_argument("--delta-file", required=True, type=Path)
    cmd.add_argument("--expected-validation-effect", required=True)
    cmd.add_argument("--proposer-actor", required=True)

    cmd = sub.add_parser("replan-verify")
    cmd.add_argument("revision_id")
    cmd.add_argument("--workspace", required=True, type=Path)
    cmd.add_argument("--verifier-actor", required=True)

    cmd = sub.add_parser("replan-activate")
    cmd.add_argument("revision_id")
    cmd.add_argument("--workspace", required=True, type=Path)
    cmd.add_argument("--actor", required=True)

    cmd = sub.add_parser("replan-reject")
    cmd.add_argument("revision_id")
    cmd.add_argument("--workspace", required=True, type=Path)
    cmd.add_argument("--reason", required=True)
    cmd.add_argument("--actor", required=True)

    cmd = sub.add_parser("replan-list")
    cmd.add_argument("--workspace", required=True, type=Path)

    cmd = sub.add_parser("project-replan")
    cmd.add_argument("--workspace", required=True, type=Path)
    cmd.add_argument("--repository-root", required=True, type=Path)
    cmd.add_argument("--actor", required=True)
    cmd.add_argument("--replan-revision-id")
    return p


def main(argv: list[str] | None = None, *, template_root: Path) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "bootstrap":
            value = bootstrap(args.workspace, args.blueprint, template_root)
        elif args.command == "validate":
            value = validate_runtime(args.workspace)
            if value["status"] != "PASS":
                print_json(value)
                return 1
        elif args.command == "reconcile":
            value = reconcile_repositories(args.workspace, args.repository)
        elif args.command == "status":
            value = status(args.workspace)
        elif args.command == "next":
            value = next_tasks(args.workspace)
        elif args.command == "draft-contract":
            db, _ = open_runtime(args.workspace)
            try:
                value = {"path": str(draft_source_contract(db, args.task_id, args.output))}
            finally:
                db.close()
        elif args.command == "register-contract":
            db, ledger = open_runtime(args.workspace)
            try:
                value = register_source_contract(
                    db,
                    ledger,
                    args.workspace.resolve(),
                    args.task_id,
                    args.file,
                    args.actor,
                    args.replace,
                )
            finally:
                db.close()
        elif args.command == "claim":
            value = claim_task(args.workspace, args.task_id, args.holder, args.ttl_hours)
        elif args.command == "prepare":
            value = prepare_worktree(args.workspace, args.task_id)
        elif args.command == "render-contract":
            db, ledger = open_runtime(args.workspace)
            try:
                value = render_contract(db, ledger, args.workspace.resolve(), args.task_id)
            finally:
                db.close()
        elif args.command == "start":
            value = start_task(args.workspace, args.task_id, args.actor)
        elif args.command == "record-attempt":
            value = record_attempt(args.workspace, args.task_id, args.receipt)
        elif args.command == "verify":
            value = verify_attempt(args.workspace, args.task_id)
        elif args.command == "complete":
            value = complete_task(args.workspace, args.task_id, args.actor, args.evidence_id)
        elif args.command == "release-lease":
            value = release_lease(args.workspace, args.task_id, args.reason, args.actor)
        elif args.command == "recover":
            value = recover(args.workspace, args.actor)
        elif args.command == "add-approval":
            value = add_approval(args.workspace, args.file)
        elif args.command == "set-decision":
            value = set_decision(
                args.workspace, args.decision_id, args.status, args.evidence_id, args.actor
            )
        elif args.command == "set-unknown":
            value = set_unknown(
                args.workspace, args.unknown_id, args.status, args.evidence_id, args.actor
            )
        elif args.command == "evaluate-gate":
            value = evaluate_gate(
                args.workspace,
                args.gate_id,
                args.result,
                args.evidence_id,
                args.method,
                args.actor,
                args.waiver_id,
            )
        elif args.command == "halt":
            value = set_halt(args.workspace, True, args.reason, args.actor)
        elif args.command == "resume":
            value = set_halt(args.workspace, False, args.reason, args.actor)
        elif args.command == "export-handoff":
            value = export_handoff(args.workspace, args.actor, args.output)
        elif args.command == "plan-revision":
            from .replan import current_plan_revision

            value = current_plan_revision(args.workspace)
        elif args.command == "replan-propose":
            from .replan import propose

            delta = json.loads(args.delta_file.read_text(encoding="utf-8"))
            value = propose(
                args.workspace,
                revision_id=args.revision_id,
                program_id=args.program_id,
                trigger_evidence_ids=args.trigger_evidence_id,
                affected_future_task_ids=args.affected_future_task_id,
                delta=delta,
                expected_validation_effect=args.expected_validation_effect,
                proposer_actor=args.proposer_actor,
            )
        elif args.command == "replan-verify":
            from .replan import verify

            value = verify(args.workspace, args.revision_id, verifier_actor=args.verifier_actor)
        elif args.command == "replan-activate":
            from .replan import activate

            value = activate(args.workspace, args.revision_id, actor=args.actor)
        elif args.command == "replan-reject":
            from .replan import reject

            value = reject(args.workspace, args.revision_id, actor=args.actor, reason=args.reason)
        elif args.command == "replan-list":
            from .replan import list_revisions

            value = {"revisions": list_revisions(args.workspace)}
        elif args.command == "project-replan":
            from .replan import project

            value = project(
                args.workspace,
                repository_root=args.repository_root,
                actor=args.actor,
                replan_revision_id=args.replan_revision_id,
            )
        else:
            raise ControllerError(f"unsupported command: {args.command}")
        print_json(value)
        return 0
    except (ControllerError, ContractError, ValueError, RuntimeError) as exc:
        print_json({"status": "ERROR", "error": str(exc)})
        return 2

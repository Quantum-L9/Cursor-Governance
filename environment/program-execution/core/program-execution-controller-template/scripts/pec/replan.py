"""Controller Replan Revision lifecycle (program-execution.replan.v1)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .common import ControllerError, digest_object, load_json, utc_now, write_json
from .runtime import _require_stack_proof_reentry, _runtime_config, open_runtime

FORBIDDEN = {
    "objective",
    "architecture",
    "public_contract",
    "ownership",
    "target_set",
    "authorization_ceiling",
    "accepted_risk",
    "mandatory_convergence_gates",
    "historical_evidence",
}

PLAN_REVISION_REL = Path("runtime/plan-revision.json")
REVISIONS_REL = Path("runtime/replan-revisions")
SCHEMA_REL = Path("shared/schemas/replan-revision.schema.json")


def _revision_schema() -> dict[str, Any]:
    """Load the canonical Replan Revision schema from the core pair."""
    core = Path(__file__).resolve().parents[3]
    path = core / SCHEMA_REL
    if not path.is_file():
        raise ControllerError(f"Replan Revision schema missing from core pair: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_revision_payload(payload: dict[str, Any]) -> None:
    # Imported here, not at module scope: jsonschema costs ~0.19s to import and
    # every `pec.py` CLI invocation paid it whether or not it validated anything.
    # The conformance suite spawns that CLI ~14 times per campaign test, so the
    # import alone was minutes of the suite's wall clock.
    from jsonschema import Draft202012Validator  # noqa: PLC0415 - deferred: see above

    errors = sorted(
        Draft202012Validator(_revision_schema()).iter_errors(payload),
        key=lambda error: list(error.path),
    )
    if errors:
        messages = [
            f"{'.'.join(str(part) for part in error.path) or '<root>'}: {error.message}"
            for error in errors
        ]
        raise ControllerError("Replan Revision schema validation failed: " + "; ".join(messages))


def _lock_digest(workspace: Path) -> str:
    lock = load_json(workspace / "runtime" / "program-lock.json")
    digest = lock.get("lock_digest")
    if not isinstance(digest, str) or len(digest) != 64:
        raise ControllerError("program lock digest missing")
    return digest


def current_plan_revision(workspace: Path) -> dict[str, Any]:
    path = workspace / PLAN_REVISION_REL
    if not path.is_file():
        lock_digest = _lock_digest(workspace)
        state = {
            "schema": "program-execution.replan.plan-revision.v1",
            "plan_revision": "plan-rev-0",
            "program_lock_digest": lock_digest,
            "active_replan_revision_id": None,
            "updated_at": utc_now(),
        }
        write_json(path, state)
        return state
    return load_json(path)


def _write_plan_revision(workspace: Path, state: dict[str, Any]) -> None:
    write_json(workspace / PLAN_REVISION_REL, state)


def _containment(delta: dict[str, Any]) -> dict[str, Any]:
    classes = list(delta.get("classes") or [])
    forbidden = [c for c in classes if c in FORBIDDEN]
    return {
        "result": "FAIL" if forbidden else "PASS",
        "forbidden_classes_present": forbidden,
        "widens_lock": bool(forbidden),
    }


def propose(
    workspace: Path,
    *,
    revision_id: str,
    program_id: str,
    trigger_evidence_ids: list[str],
    affected_future_task_ids: list[str],
    delta: dict[str, Any],
    expected_validation_effect: str,
    proposer_actor: str,
) -> dict[str, Any]:
    workspace = workspace.resolve()
    lock_digest = _lock_digest(workspace)
    plan = current_plan_revision(workspace)
    containment = _containment(delta)
    if containment["result"] == "FAIL":
        raise ControllerError(
            "authority containment failed: " + ", ".join(containment["forbidden_classes_present"])
        )
    payload: dict[str, Any] = {
        "schema": "program-execution.replan.revision.v1",
        "revision_id": revision_id,
        "program_id": program_id,
        "program_lock_digest": lock_digest,
        "previous_plan_revision": plan["plan_revision"],
        "proposed_plan_revision": f"{plan['plan_revision']}+{revision_id}",
        "trigger_evidence_ids": list(trigger_evidence_ids),
        "affected_future_task_ids": list(affected_future_task_ids),
        "delta": delta,
        "authority_containment": containment,
        "expected_validation_effect": expected_validation_effect,
        "proposer_actor": proposer_actor,
        "verifier_actor": None,
        "status": "proposed",
        "created_at": utc_now(),
        "activated_at": None,
        "rejected_reason": None,
    }
    payload["revision_digest"] = digest_object(payload)
    _validate_revision_payload(payload)
    target = workspace / REVISIONS_REL / f"{revision_id}.json"
    if target.exists():
        raise ControllerError(f"replan revision already exists: {revision_id}")
    write_json(target, payload)
    db, ledger = open_runtime(workspace)
    try:
        ledger.append(
            "REPLAN_PROPOSED",
            proposer_actor,
            {"revision_id": revision_id, "digest": payload["revision_digest"]},
        )
    finally:
        db.close()
    return payload


def verify(workspace: Path, revision_id: str, *, verifier_actor: str) -> dict[str, Any]:
    workspace = workspace.resolve()
    path = workspace / REVISIONS_REL / f"{revision_id}.json"
    revision = load_json(path)
    if revision["status"] != "proposed":
        raise ControllerError(f"revision {revision_id} is not proposed")
    if verifier_actor == revision["proposer_actor"]:
        raise ControllerError("proposer may not verify the same revision")
    lock_digest = _lock_digest(workspace)
    plan = current_plan_revision(workspace)
    if revision["program_lock_digest"] != lock_digest:
        revision["status"] = "stale"
        revision["rejected_reason"] = "program_lock_digest_mismatch"
        write_json(path, revision)
        raise ControllerError("revision is stale: program lock digest mismatch")
    if revision["previous_plan_revision"] != plan["plan_revision"]:
        revision["status"] = "stale"
        revision["rejected_reason"] = "previous_plan_revision_mismatch"
        write_json(path, revision)
        raise ControllerError("revision is stale: previous plan revision mismatch")
    if revision["authority_containment"]["result"] != "PASS":
        raise ControllerError("authority containment failed")
    if not revision.get("trigger_evidence_ids"):
        raise ControllerError("trigger evidence required")
    revision["verifier_actor"] = verifier_actor
    revision["status"] = "verified"
    body = {k: v for k, v in revision.items() if k != "revision_digest"}
    revision["revision_digest"] = digest_object(body)
    write_json(path, revision)
    db, ledger = open_runtime(workspace)
    try:
        ledger.append(
            "REPLAN_VERIFIED",
            verifier_actor,
            {"revision_id": revision_id, "digest": revision["revision_digest"]},
        )
    finally:
        db.close()
    return revision


def activate(workspace: Path, revision_id: str, *, actor: str) -> dict[str, Any]:
    workspace = workspace.resolve()
    config = _runtime_config(workspace)
    if actor != config.get("controller_id") and actor != "controller":
        raise ControllerError("only the Controller may activate a Replan Revision")
    path = workspace / REVISIONS_REL / f"{revision_id}.json"
    revision = load_json(path)
    if revision["status"] != "verified":
        raise ControllerError(f"revision {revision_id} is not verified")
    plan = current_plan_revision(workspace)
    if revision["previous_plan_revision"] != plan["plan_revision"]:
        revision["status"] = "stale"
        revision["rejected_reason"] = "previous_plan_revision_mismatch"
        write_json(path, revision)
        raise ControllerError("stale revision; previous plan preserved")
    extra = " ".join(str(item) for item in (revision.get("affected_future_task_ids") or []))
    extra += " " + json.dumps(revision.get("delta") or {}, sort_keys=True)
    _require_stack_proof_reentry(workspace, extra)
    revision["status"] = "activated"
    revision["activated_at"] = utc_now()
    body = {k: v for k, v in revision.items() if k != "revision_digest"}
    revision["revision_digest"] = digest_object(body)
    write_json(path, revision)
    _write_plan_revision(
        workspace,
        {
            "schema": "program-execution.replan.plan-revision.v1",
            "plan_revision": revision["proposed_plan_revision"],
            "program_lock_digest": revision["program_lock_digest"],
            "active_replan_revision_id": revision_id,
            "updated_at": revision["activated_at"],
        },
    )
    db, ledger = open_runtime(workspace)
    try:
        ledger.append(
            "REPLAN_ACTIVATED",
            actor,
            {"revision_id": revision_id, "plan_revision": revision["proposed_plan_revision"]},
        )
    finally:
        db.close()
    return revision


def reject(workspace: Path, revision_id: str, *, actor: str, reason: str) -> dict[str, Any]:
    workspace = workspace.resolve()
    path = workspace / REVISIONS_REL / f"{revision_id}.json"
    revision = load_json(path)
    if revision["status"] == "activated":
        raise ControllerError("activated revision cannot be rejected")
    previous = current_plan_revision(workspace)
    revision["status"] = "rejected"
    revision["rejected_reason"] = reason
    body = {k: v for k, v in revision.items() if k != "revision_digest"}
    revision["revision_digest"] = digest_object(body)
    write_json(path, revision)
    db, ledger = open_runtime(workspace)
    try:
        ledger.append(
            "REPLAN_REJECTED",
            actor,
            {
                "revision_id": revision_id,
                "reason": reason,
                "preserved_plan_revision": previous["plan_revision"],
            },
        )
    finally:
        db.close()
    return revision


def list_revisions(workspace: Path) -> list[dict[str, Any]]:
    root = workspace.resolve() / REVISIONS_REL
    if not root.is_dir():
        return []
    items = []
    for path in sorted(root.glob("*.json")):
        items.append(json.loads(path.read_text(encoding="utf-8")))
    return items


def plan_adaptation(workspace: Path) -> dict[str, Any]:
    """Future-plan adaptation view derived from the active Replan Revision.

    The Program Lock never mutates; the Controller computes the current future
    execution plan as locked dependencies plus the active revision's bounded
    operations. Returns dependency overrides, runtime-only split children, and
    scoped runtime Unknowns — all reversible, all outside git.
    """
    workspace = workspace.resolve()
    plan = current_plan_revision(workspace)
    revision_id = plan.get("active_replan_revision_id")
    empty: dict[str, Any] = {
        "dependency_overrides": {},
        "runtime_child_tasks": {},
        "scoped_unknowns": [],
        "active_replan_revision_id": None,
    }
    if not revision_id:
        return empty
    path = workspace / REVISIONS_REL / f"{revision_id}.json"
    if not path.is_file():
        raise ControllerError(f"active Replan Revision missing: {revision_id}")
    revision = load_json(path)
    if revision["status"] != "activated":
        raise ControllerError(f"active Replan Revision is not activated: {revision_id}")
    overrides: dict[str, dict[str, list[str]]] = {}
    children: dict[str, list[str]] = {}
    unknowns: list[dict[str, Any]] = []
    for operation in (revision.get("delta") or {}).get("operations") or []:
        opcode = operation.get("op")
        target = operation.get("target_task_id")
        if not target:
            continue
        if opcode == "reorder":
            overrides[target] = {
                "add": list(operation.get("add_dependencies") or []),
                "remove": list(operation.get("remove_dependencies") or []),
            }
        elif opcode == "split":
            children[target] = list(operation.get("child_task_ids") or [])
        elif opcode == "add_unknown":
            unknowns.append(
                {
                    "unknown_id": operation.get("unknown_id"),
                    "blocked_task_ids": list(operation.get("blocked_task_ids") or []),
                    "note": operation.get("note"),
                }
            )
    return {
        "dependency_overrides": overrides,
        "runtime_child_tasks": children,
        "scoped_unknowns": unknowns,
        "active_replan_revision_id": revision_id,
    }


def project(
    workspace: Path, *, repository_root: Path, actor: str, replan_revision_id: str | None = None
) -> dict[str, Any]:
    """Project the canonical semantic revision of the active Replan Revision
    to every registered execution peer through the shared projection seam.

    The seam is the canonical peer_execution module resolved from the
    repository root; the Controller never owns a second copy of projection
    semantics.
    """
    import sys

    workspace = workspace.resolve()
    plan = current_plan_revision(workspace)
    if replan_revision_id is None:
        replan_revision_id = plan.get("active_replan_revision_id")
    if not replan_revision_id:
        raise ControllerError("no active Replan Revision to project")
    revision = load_json(workspace / REVISIONS_REL / f"{replan_revision_id}.json")
    if revision["status"] != "activated":
        raise ControllerError("only an activated Replan Revision may be projected")
    root = Path(repository_root).resolve()
    pe_root = root / "environment/program-execution"
    if not pe_root.is_dir():
        raise ControllerError(f"program-execution seam not found under repository root: {pe_root}")
    # APPEND, never insert(0): `scripts` is a top-level name Program Execution
    # SHARES with the repository root, so a prepend hands PE's `scripts/` that
    # name process-wide. See peer_execution.imports.pe_script.
    if str(pe_root) not in sys.path:
        sys.path.append(str(pe_root))
    from peer_execution.replan_projection import (  # canonical shared seam
        build_semantic_revision,
        project_to_peers,
    )

    semantic = build_semantic_revision(
        pe_root / "core/shared/REPLAN_CONTRACT.yaml",
        pe_root / "core/shared/schemas/replan-revision.schema.json",
        replan_revision_id=replan_revision_id,
        plan_revision=plan["plan_revision"],
        activated_at=revision["activated_at"],
        actor=actor,
    )
    return project_to_peers(root, workspace, semantic_revision=semantic, actor=actor)

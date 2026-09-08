"""Workspace-level runtime accessors, below both `controller` and `replan`.

These five functions used to live in `controller.py`. `replan` needed three of
them and could only reach them through deferred (function-local) imports of
`controller`, because a module-level import would have closed a cycle:

    controller -> replan -> controller
    controller -> contracts -> replan -> controller

That deferral was the workaround, not the fix -- it made `replan` unimportable
in isolation and left the package logically cyclic (CodeQL `py/cyclic-import`).
Hoisting the shared functions into this leaf module removes the back-edge
entirely, so the package is acyclic at module level and the deferrals are gone.

This module must stay in `pec/`: `_require_stack_proof_reentry` resolves
`parents[4]` to reach `environment/program-execution/scripts/`, so its depth is
load-bearing. It may only import from `common`, `ledger`, and `state`, none of
which import back into `controller` -- that is what keeps it a leaf.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

from .common import ControllerError, digest_object, load_json, write_json
from .ledger import EventLedger, LedgerError, verify_chain
from .state import StateDB, StateError


def campaign_status_path(workspace: Path) -> Path:
    return workspace.resolve() / "runtime" / "campaign-status.json"


def read_campaign_status(workspace: Path) -> dict[str, Any] | None:
    path = campaign_status_path(workspace)
    if not path.is_file():
        return None
    return load_json(path)


def open_runtime(workspace: Path) -> tuple[StateDB, EventLedger]:
    workspace = workspace.resolve()
    if not (workspace / "runtime" / "state.sqlite").is_file():
        raise ControllerError(f"Controller runtime not bootstrapped: {workspace}")
    try:
        db = StateDB(workspace / "runtime" / "state.sqlite")
    except StateError as exc:
        raise ControllerError(str(exc), error_code=exc.error_code) from exc
    ledger = EventLedger(workspace / "ledger" / "events.jsonl", anchor_store=db)
    try:
        reconcile_runtime(db, ledger, workspace)
    except Exception:
        db.close()
        raise
    return db, ledger


def reconcile_runtime(db: StateDB, ledger: EventLedger, workspace: Path) -> dict[str, Any]:
    """Converge the runtime's durable surfaces after any interruption (R8 §12.8).

    Runs at every open, before any command. Deterministic and idempotent:

    * a pre-R8 runtime (no canonical events) imports its file chain once,
      only if that chain verifies -- an unverifiable legacy ledger fails
      closed rather than being adopted;
    * receipt files already on disk with no canonical record are imported
      only when their own digest proves their content (verification, gate
      and closure receipts); anything else is left alone and never adopted;
    * committed-but-unprojected events are appended to the file;
    * canonical receipts whose artifact is missing or differs from the
      recorded content are rematerialized from the record.
    """
    report: dict[str, Any] = {"imported_events": 0, "projected_events": 0, "receipts": 0}
    if db.event_count() == 0:
        try:
            legacy = ledger.file_events()
        except LedgerError as exc:
            raise ControllerError(
                f"legacy ledger cannot be adopted: {exc}",
                error_code="RUNTIME_RECONCILIATION_REQUIRED",
            ) from exc
        if legacy:
            ok, message = verify_chain(legacy)
            if not ok:
                raise ControllerError(
                    f"legacy ledger chain does not verify ({message}); refusing to adopt it",
                    error_code="RUNTIME_RECONCILIATION_REQUIRED",
                )
            with db.controller_transaction():
                for event in legacy:
                    db.import_event(event, projected=True)
            report["imported_events"] = len(legacy)
    report["projected_events"] = ledger.project_pending()
    report["receipts"] = _reconcile_receipts(db, workspace)
    return report


#: Receipt files a pre-R8 runtime may hold with no canonical record, and the
#: (type, entity id field) that describes them. Imported only when the file's
#: own digest proves its content.
_LEGACY_RECEIPT_GLOBS = (
    ("receipts/verification/*.json", "verification", "task_id"),
    ("receipts/gates/*/*.json", "gate_evaluation", "gate_id"),
    ("receipts/closure/*.json", "closure", "campaign_id"),
)


def _self_consistent(payload: Any) -> bool:
    if not isinstance(payload, dict) or not payload.get("receipt_digest"):
        return False
    body = dict(payload)
    claimed = body.pop("receipt_digest", None)
    body.pop("signal", None)
    return digest_object(body) == claimed


def _reconcile_receipts(db: StateDB, workspace: Path) -> int:
    touched = 0
    for pattern, receipt_type, entity_field in _LEGACY_RECEIPT_GLOBS:
        for path in sorted(workspace.glob(pattern)):
            if db.receipt_by_artifact(str(path)) is not None:
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if not _self_consistent(payload):
                continue
            receipt_id = str(
                payload.get("verification_id")
                or payload.get("evaluation_id")
                or payload.get("closure_id")
                or payload["receipt_digest"]
            )
            if db.receipt(receipt_id) is not None:
                continue
            db.record_receipt(
                receipt_id=receipt_id,
                receipt_type=receipt_type,
                entity_id=str(payload.get(entity_field) or ""),
                payload={k: v for k, v in payload.items() if k != "signal"},
                artifact_path=str(path),
                projected=True,
            )
            touched += 1
    for record in db.receipts():
        artifact = Path(str(record["artifact_path"]))
        expected = record["payload"]
        materialize = not record["projected"] or not artifact.is_file()
        if not materialize:
            try:
                on_disk = json.loads(artifact.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                materialize = True
            else:
                on_disk = dict(on_disk) if isinstance(on_disk, dict) else {}
                on_disk.pop("signal", None)
                materialize = on_disk != expected
        if materialize:
            write_json(artifact, expected)
            db.mark_receipt_projected(str(record["receipt_id"]))
            touched += 1
    return touched


def _runtime_config(workspace: Path) -> dict[str, Any]:
    path = workspace / "config" / "controller.json"
    if not path.is_file():
        raise ControllerError("runtime controller config missing")
    return load_json(path)


def _require_stack_proof_reentry(workspace: Path, extra_text: str) -> None:
    proof_path = Path(__file__).resolve().parents[4] / "scripts" / "context7_stack_proof.py"
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

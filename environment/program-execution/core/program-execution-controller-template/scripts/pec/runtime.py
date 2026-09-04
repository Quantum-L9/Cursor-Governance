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
from pathlib import Path
from typing import Any

from .common import ControllerError, load_json
from .ledger import EventLedger
from .state import StateDB


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
    db = StateDB(workspace / "runtime" / "state.sqlite")
    return db, EventLedger(workspace / "ledger" / "events.jsonl", anchor_store=db)


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

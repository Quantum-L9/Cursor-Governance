"""Route a rendered contract, probe a provider, and map a pre-submission receipt.

Render-contract always records a dispatch plan. Live provider invoke happens
only when a provider is bound (tests) or ``L9_PEC_DISPATCH_INVOKE=1``.
Workers must not claim independent verification.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any


class DispatchError(RuntimeError):
    """Dispatch refused a worker self-verify or a corrupt route."""


# pec/dispatch.py → scripts → template → core → program-execution
_PE_ROOT = Path(__file__).resolve().parents[4]
if str(_PE_ROOT) not in sys.path:
    sys.path.insert(0, str(_PE_ROOT))
if str(_PE_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_PE_ROOT / "scripts"))


def pe_root() -> Path:
    return _PE_ROOT


def _bind_router() -> Any:
    from adapters.common.errors import AdapterFailure, CanonicalErrorCode
    from router import route_contract

    return route_contract, AdapterFailure, CanonicalErrorCode


def assert_worker_cannot_self_verify(rendered: Mapping[str, Any]) -> None:
    if rendered.get("independent_verification") is True:
        raise DispatchError("worker_cannot_self_verify: contract claims independent verification")
    if rendered.get("independent_review_claimed_by_worker") is True:
        raise DispatchError("worker_cannot_self_verify: worker claimed independent review")


def map_provider_result_to_presubmission(
    rendered: Mapping[str, Any],
    *,
    status: str,
    structured_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    assert_worker_cannot_self_verify(rendered)
    payload = dict(structured_payload or {})
    if payload.get("independent_verification") is True:
        raise DispatchError("worker_cannot_self_verify: provider result claimed verification")
    return {
        "schema": "program-execution-controller.attempt-receipt.v2",
        "task_id": rendered["task_id"],
        "contract_digest": rendered["contract_digest"],
        "program_digest": rendered["program_digest"],
        "base_sha": rendered["base_sha"],
        "candidate_sha": payload.get("candidate_sha"),
        "changed_files": list(payload.get("changed_files") or []),
        "validation_results": list(payload.get("validation_results") or []),
        "produced_evidence": [],
        "residual_unknowns": list(payload.get("residual_unknowns") or []),
        "claimed_status": "completed" if status == "PASS" else "failed",
        "presubmission": True,
        "independent_verification": False,
    }


def route_rendered(
    rendered: Mapping[str, Any],
    *,
    subsystem_root: Path | None = None,
    capability_receipts: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    route_contract, adapter_failure, codes = _bind_router()
    try:
        routed = route_contract(
            rendered,
            subsystem_root=subsystem_root or _PE_ROOT,
            capability_receipts=capability_receipts,
        )
    except adapter_failure as exc:
        if exc.code != codes.CAPABILITY_UNSUPPORTED:
            raise
        return {
            "status": "UNSUPPORTED",
            "error_code": codes.CAPABILITY_UNSUPPORTED.value,
            "fallback": "manual_worker_brief",
            "detail": str(exc),
        }
    return {"status": "ROUTED", "route": routed}


def dispatch_rendered_contract(
    rendered: Mapping[str, Any],
    *,
    provider: Any | None = None,
    invoke: bool | None = None,
    subsystem_root: Path | None = None,
    probe_context: Any | None = None,
    capability_receipts: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Route, optionally probe/invoke, and map a pre-submission receipt."""

    assert_worker_cannot_self_verify(rendered)
    should_invoke = (
        bool(invoke)
        if invoke is not None
        else os.environ.get("L9_PEC_DISPATCH_INVOKE", "").strip() in {"1", "true", "TRUE"}
    )
    plan = route_rendered(
        rendered,
        subsystem_root=subsystem_root,
        capability_receipts=capability_receipts,
    )
    result: dict[str, Any] = {"dispatch": plan}
    if plan.get("status") != "ROUTED":
        return result
    if provider is None:
        return result
    from peer_execution.models import ProbeContext

    context = probe_context or ProbeContext(
        repository_root=str(subsystem_root or _PE_ROOT),
        runtime_root=str(rendered.get("worktree") or "."),
        program_lock_digest=str(rendered.get("program_digest") or ""),
        requested_capabilities=tuple(rendered.get("requested_actions") or ()),
    )
    probe = provider.probe(context)
    result["probe"] = {
        "status": probe.status,
        "observed_capabilities": list(getattr(probe, "observed_capabilities", ()) or ()),
    }
    if probe.status != "PASS" or not should_invoke:
        return result

    class _InvokeRequest:
        execution_id = f"dispatch-{rendered['task_id']}-{rendered.get('attempt_number') or 1}"
        rendered_contract = dict(rendered)
        adapter_id = str((plan.get("route") or {}).get("adapter_id") or "unknown")

    invocation = provider.invoke(_InvokeRequest())
    provider_result = getattr(invocation, "result", None)
    status = getattr(provider_result, "status", None) or invocation.status
    payload = dict(getattr(provider_result, "structured_payload", None) or {})
    result["provider_result"] = {"status": status, "structured_payload": payload}
    result["attempt_receipt_presubmission"] = map_provider_result_to_presubmission(
        rendered, status=str(status), structured_payload=payload
    )
    return result

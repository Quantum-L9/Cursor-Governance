from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from environment.agents.lifecycle import receipts as lifecycle_receipts
from environment.agents.results import receipts as result_receipts
from environment.agents.results.adapters import cursor_subagent

_REPO_ROOT = Path(__file__).resolve().parents[3]
_INGEST_PATH = _REPO_ROOT / "environment/agents/generated-data/ingress/ingest.py"


def _load_ingest_module():
    ingress_dir = _INGEST_PATH.parent
    if str(ingress_dir) not in sys.path:
        sys.path.insert(0, str(ingress_dir))
    spec = importlib.util.spec_from_file_location("l9_generated_data_ingest", _INGEST_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {_INGEST_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["l9_generated_data_ingest"] = module
    spec.loader.exec_module(module)
    return module


# Host stop verdicts that count as a normal completion. Anything else the host
# reports (cancelled, error, timeout, killed, failed, ...) is a terminal
# non-success and rejects the result regardless of what the document says.
HOST_SUCCESS_STATUSES = frozenset(
    {"completed", "complete", "success", "succeeded", "done", "finished", "ok"}
)
# Root lease states under which a returned document may still be judged: the
# lease is live, or it ended by normal release (ACTION_COMPLETED). REVOKED,
# EXPIRED, and a missing lease mean root authority withdrew the assignment.
LEASE_ACCEPTABLE_STATUSES = frozenset({"ACTIVE", "RELEASED"})


def _role_alias(value: Any) -> str:
    return cursor_subagent.result_bridge.canonical_cursor_role(value)


def _host_authority_error(return_receipt: Mapping[str, Any]) -> str | None:
    """Reasons the host or the root lease refuse this result before the
    document is even read. A document never out-votes either."""
    host_status = return_receipt.get("host_status")
    if host_status not in (None, ""):
        if str(host_status).strip().lower() not in HOST_SUCCESS_STATUSES:
            return f"host reported terminal status {str(host_status)!r}, not a success"
    database = return_receipt.get("runtime_database")
    lease_id = return_receipt.get("lease_id")
    if database in (None, "") or not lease_id:
        return None
    from autonomy.adapters.cursor import host_bridge  # noqa: PLC0415

    if not Path(str(database)).is_file():
        return f"root runtime database {str(database)!r} is unavailable; lease state undeterminable"
    status = host_bridge.lease_status(database, str(lease_id))
    if status is None:
        return f"root lease {str(lease_id)!r} is missing"
    if status not in LEASE_ACCEPTABLE_STATUSES:
        return f"root lease {str(lease_id)!r} is {status}, not ACTIVE or RELEASED"
    return None


def _rejection(
    *,
    return_receipt: Mapping[str, Any] | None,
    surface_result: Mapping[str, Any],
    adapter: str,
    reason: str,
) -> dict[str, Any]:
    rid = hashlib.sha256(
        json.dumps(surface_result, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    return result_receipts.write_acceptance(
        {
            "assignment_id": (return_receipt or {}).get("assignment_id") or "unknown",
            "agent_id": "cursor",
            "parent_agent_id": (return_receipt or {}).get("parent_agent_id") or "cursor",
            "surface": (return_receipt or {}).get("surface") or "cursor-ide",
            "result_adapter": adapter,
            "result_id": f"reject-{rid}",
            "result_digest": "",
            "status": "REJECTED",
            "reason": reason,
            "campaign_id": (return_receipt or {}).get("campaign_id"),
            "graph_id": (return_receipt or {}).get("graph_id"),
            "action_id": (return_receipt or {}).get("action_id"),
            "lease_id": (return_receipt or {}).get("lease_id"),
            "base_sha": (return_receipt or {}).get("base_sha"),
            "raw_result_path": (return_receipt or {}).get("raw_result_path"),
            "raw_result_digest": (return_receipt or {}).get("raw_result_digest"),
        }
    )


def normalize(
    *,
    return_receipt: Mapping[str, Any],
    surface_result: dict[str, Any],
    adapter: str,
) -> dict[str, Any]:
    if adapter != "cursor_subagent":
        raise ValueError(f"unknown adapter {adapter}")
    assignment_id = str(
        return_receipt.get("assignment_id") or surface_result.get("assignment_id") or ""
    )
    assignment = lifecycle_receipts.load_assignment(assignment_id) if assignment_id else None
    return cursor_subagent.normalize(surface_result, assignment=assignment)


def _correlation_error(
    return_receipt: Mapping[str, Any],
    normalized: Mapping[str, Any],
) -> str | None:
    identity = normalized.get("identity")
    document_assignment = normalized.get("assignment")
    if not isinstance(identity, Mapping) or not isinstance(document_assignment, Mapping):
        return "normalized result lacks identity or assignment"
    for field in ("campaign_id", "graph_id", "action_id", "lease_id", "base_sha"):
        expected = return_receipt.get(field)
        actual = identity.get(field)
        if expected and actual and str(actual) != str(expected):
            return f"wrong {field}"
    expected_agent = return_receipt.get("agent_id")
    if (
        expected_agent
        and identity.get("agent_id")
        and str(identity["agent_id"]) != str(expected_agent)
    ):
        return "wrong agent_id"
    expected_role = _role_alias(
        return_receipt.get("result_role") or return_receipt.get("subagent_role")
    )
    actual_role = _role_alias(document_assignment.get("role"))
    if (
        expected_role
        and expected_role
        in {
            "recon",
            "pr_remediation",
            "test",
            "documentation",
            "verifier_reviewer",
        }
        and actual_role != expected_role
    ):
        return "wrong role"
    return None


def _accept(
    *,
    return_receipt: dict[str, Any] | None,
    surface_result: dict[str, Any],
    adapter: str,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Judge one returned result; every outcome is a durable acceptance receipt.

    Returns ``(receipt, normalized_document)``; the document is ``None`` unless
    the receipt is ACCEPTED. Normalization runs inside this guarded path so an
    adapter or correlation failure is recorded as REJECTED rather than
    escaping as an exception that leaves no receipt behind.
    """
    if not return_receipt or return_receipt.get("status") not in {"RETURNED", None}:
        return (
            _rejection(
                return_receipt=return_receipt,
                surface_result=surface_result,
                adapter=adapter,
                reason="missing SubagentReturnReceipt",
            ),
            None,
        )
    authority_problem = _host_authority_error(return_receipt)
    if authority_problem is not None:
        return (
            _rejection(
                return_receipt=return_receipt,
                surface_result=surface_result,
                adapter=adapter,
                reason=f"host authority refused result: {authority_problem}",
            ),
            None,
        )
    try:
        normalized = normalize(
            return_receipt=return_receipt,
            surface_result=surface_result,
            adapter=adapter,
        )
    except Exception as exc:  # noqa: BLE001
        return (
            _rejection(
                return_receipt=return_receipt,
                surface_result=surface_result,
                adapter=adapter,
                reason=f"adapter validation failed: {exc}",
            ),
            None,
        )

    reason = _correlation_error(return_receipt, normalized)
    status = "REJECTED" if reason else "ACCEPTED"
    reason = reason or "ok"
    identity = normalized["identity"]
    result_digest = hashlib.sha256(
        json.dumps(normalized, sort_keys=True, default=str).encode()
    ).hexdigest()
    result_id = normalized.get("result_id") or result_digest[:16]
    assignment_id = return_receipt.get("assignment_id")
    existing = result_receipts.load_acceptance(str(result_id), assignment_id)
    if existing:
        if existing.get("result_digest") != result_digest:
            raise RuntimeError(f"result_id collision for {result_id}: existing result differs")
        return existing, (normalized if existing.get("status") == "ACCEPTED" else None)
    receipt = result_receipts.write_acceptance(
        {
            "assignment_id": assignment_id,
            "campaign_id": identity.get("campaign_id"),
            "graph_id": identity.get("graph_id"),
            "action_id": identity.get("action_id"),
            "agent_id": identity.get("agent_id") or "cursor",
            "parent_agent_id": return_receipt.get("parent_agent_id") or "cursor",
            "lease_id": identity.get("lease_id"),
            "base_sha": identity.get("base_sha"),
            "surface": return_receipt.get("surface") or "cursor-ide",
            "result_adapter": adapter,
            "result_id": result_id,
            "result_digest": result_digest,
            "document_status": normalized.get("status"),
            "host_status": return_receipt.get("host_status"),
            "raw_result_path": return_receipt.get("raw_result_path"),
            "raw_result_digest": return_receipt.get("raw_result_digest"),
            "status": status,
            "reason": reason,
        }
    )
    return receipt, (normalized if status == "ACCEPTED" else None)


def accept(
    *,
    return_receipt: dict[str, Any] | None,
    surface_result: dict[str, Any],
    adapter: str = "cursor_subagent",
) -> dict[str, Any]:
    receipt, _normalized = _accept(
        return_receipt=return_receipt,
        surface_result=surface_result,
        adapter=adapter,
    )
    return receipt


def accept_and_ingest(
    *,
    return_receipt: dict[str, Any],
    surface_result: dict[str, Any],
    repository: str,
    repository_class: str = "governed_repository",
    adapter: str = "cursor_subagent",
    independent_validation_present: bool = False,
    designated_authority_approval: bool = False,
    recurrence_counts: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    acceptance, normalized = _accept(
        return_receipt=return_receipt,
        surface_result=surface_result,
        adapter=adapter,
    )
    if acceptance.get("status") != "ACCEPTED" or normalized is None:
        return {
            "status": "REJECTED",
            "reason": acceptance.get("reason"),
            "acceptance_receipt": acceptance,
            "ingress_receipt": None,
        }
    packet = cursor_subagent.result_bridge.to_generated_data_packet(
        normalized,
        repository=repository,
        repository_class=repository_class,
    )
    ingest = _load_ingest_module()
    ingress = ingest.ingest_accepted_result(
        accepted_result=normalized,
        generated_data_packet=packet,
        acceptance_receipt=acceptance,
        actor=str(normalized["identity"]["agent_id"]),
        repository_root=_REPO_ROOT,
        independent_validation_present=independent_validation_present,
        designated_authority_approval=designated_authority_approval,
        recurrence_counts=recurrence_counts,
    )
    ingress_outcome = str(ingress.get("outcome") or "UNKNOWN")
    document_status = str(normalized.get("status") or "unknown")
    # The document's own completion status is carried through, never
    # flattened: a partial, blocked, or failed document was accepted as
    # evidence, which is not the same handoff as a completed one.
    if ingress_outcome == "FAILED":
        handoff_status = "FAILED"
    elif document_status != "completed":
        handoff_status = "ACCEPTED_INCOMPLETE"
    else:
        handoff_status = "ACCEPTED"
    return {
        "status": handoff_status,
        "result_acceptance_status": "ACCEPTED",
        "document_status": document_status,
        "generated_data_status": ingress_outcome,
        "packet_id": packet["packet_id"],
        "acceptance_receipt": acceptance,
        "ingress_receipt": ingress,
    }

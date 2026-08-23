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


def _role_alias(value: Any) -> str:
    raw = str(value or "").strip().lower().replace("-", "_")
    aliases = {
        "l9_recon": "recon",
        "recon": "recon",
        "l9_pr_remediation": "pr_remediation",
        "pr_remediation": "pr_remediation",
        "l9_test": "test",
        "test": "test",
        "l9_documentation": "documentation",
        "documentation": "documentation",
        "l9_verifier": "verifier_reviewer",
        "l9_reviewer": "verifier_reviewer",
        "verifier_reviewer": "verifier_reviewer",
    }
    return aliases.get(raw, raw)


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


def accept(
    *,
    return_receipt: dict[str, Any] | None,
    surface_result: dict[str, Any],
    adapter: str = "cursor_subagent",
) -> dict[str, Any]:
    if not return_receipt or return_receipt.get("status") not in {"RETURNED", None}:
        return _rejection(
            return_receipt=return_receipt,
            surface_result=surface_result,
            adapter=adapter,
            reason="missing SubagentReturnReceipt",
        )
    try:
        normalized = normalize(
            return_receipt=return_receipt,
            surface_result=surface_result,
            adapter=adapter,
        )
    except Exception as exc:  # noqa: BLE001
        return _rejection(
            return_receipt=return_receipt,
            surface_result=surface_result,
            adapter=adapter,
            reason=f"adapter validation failed: {exc}",
        )

    reason = _correlation_error(return_receipt, normalized)
    status = "REJECTED" if reason else "ACCEPTED"
    reason = reason or "ok"
    identity = normalized["identity"]
    result_digest = hashlib.sha256(
        json.dumps(normalized, sort_keys=True, default=str).encode()
    ).hexdigest()
    result_id = normalized.get("result_id") or result_digest[:16]
    existing = result_receipts.load_acceptance(str(result_id))
    if existing:
        if existing.get("result_digest") != result_digest:
            raise RuntimeError(f"result_id collision for {result_id}: existing result differs")
        return existing
    return result_receipts.write_acceptance(
        {
            "assignment_id": return_receipt.get("assignment_id"),
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
            "raw_result_path": return_receipt.get("raw_result_path"),
            "raw_result_digest": return_receipt.get("raw_result_digest"),
            "status": status,
            "reason": reason,
        }
    )


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
    normalized = normalize(
        return_receipt=return_receipt,
        surface_result=surface_result,
        adapter=adapter,
    )
    acceptance = accept(
        return_receipt=return_receipt,
        surface_result=normalized,
        adapter=adapter,
    )
    if acceptance.get("status") != "ACCEPTED":
        return {
            "status": "REJECTED",
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
    handoff_status = "FAILED" if ingress_outcome == "FAILED" else "ACCEPTED"
    return {
        "status": handoff_status,
        "result_acceptance_status": "ACCEPTED",
        "generated_data_status": ingress_outcome,
        "packet_id": packet["packet_id"],
        "acceptance_receipt": acceptance,
        "ingress_receipt": ingress,
    }

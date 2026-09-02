from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from adapters.common.errors import AdapterFailure, CanonicalErrorCode
from peer_execution.models import CapabilityReceipt

KIND_BY_ACTION_CLASS = {
    "repository_implementation": "worker_host",
    "interactive_local_repair": "worker_host",
    "read_only_architecture_or_artifact_work": "worker_host",
    "tightly_scoped_mechanical": "worker_host",
    "verification": "verifier",
    "remote_repository_action": "remote_action",
    "check_read_or_publication": "remote_action",
    "deployment_record": "deployment_record",
    "target_deployment": "target_deployment",
}


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"YAML document must be an object: {path}")
    return value


def _adapter_rejection_reasons(
    *,
    root: Path,
    entry: Mapping[str, Any],
    required_kind: str,
    requested_actions: set[str],
    target_kind: str,
    capability_receipts: Mapping[str, Mapping[str, Any]] | None,
    program_lock_digest: str | None = None,
) -> list[str]:
    reasons: list[str] = []
    if entry.get("status") in {"dormant", "non_routable"}:
        reasons.append(f"status:{entry.get('status')}")
    if entry.get("adapter_kind") != required_kind:
        reasons.append("adapter_kind_mismatch")
    descriptor = _load_yaml(root / str(entry["descriptor"]))
    capabilities = descriptor.get("capabilities") or {}
    supported_actions = {str(item) for item in capabilities.get("actions") or []}
    if not requested_actions <= supported_actions:
        reasons.append("action_capability_mismatch")
    target_kinds = {str(item) for item in capabilities.get("target_kinds") or []}
    if target_kind and target_kind not in target_kinds and "*" not in target_kinds:
        reasons.append("target_kind_mismatch")
    if entry.get("status") == "conditional":
        receipt = (capability_receipts or {}).get(str(entry.get("adapter_id")))
        reasons.extend(_capability_receipt_rejections(receipt, program_lock_digest))
    return reasons


def _capability_receipt_rejections(
    receipt: Mapping[str, Any] | None, program_lock_digest: str | None
) -> list[str]:
    """Why a stored capability receipt does not make a conditional adapter routable.

    "Fresh" is judged, not assumed: the receipt must verify its own digest,
    carry PASS, be inside its TTL, and be bound to the Program Lock the
    contract names. A `status: PASS` file alone proved nothing.
    """
    if not receipt or receipt.get("status") != "PASS":
        return ["fresh_capability_receipt_required"]
    try:
        parsed = CapabilityReceipt.from_dict(dict(receipt))
    except (KeyError, TypeError, ValueError):
        return ["capability_receipt_malformed"]
    if not parsed.is_valid():
        return ["capability_receipt_digest_mismatch"]
    if not parsed.is_fresh():
        return ["capability_receipt_expired"]
    if program_lock_digest and parsed.program_lock_digest != program_lock_digest:
        return ["capability_receipt_program_lock_mismatch"]
    return []


def route_contract(
    contract: Mapping[str, Any],
    *,
    subsystem_root: str | Path,
    capability_receipts: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    root = Path(subsystem_root).resolve()
    registry = _load_yaml(root / "registry/EXECUTION_ADAPTER_REGISTRY.yaml")
    policy = _load_yaml(root / "registry/EXECUTION_ROUTING_POLICY.yaml")
    action_class = str(contract.get("action_class") or "")
    required_kind = KIND_BY_ACTION_CLASS.get(action_class)
    if required_kind is None:
        raise AdapterFailure(
            CanonicalErrorCode.CAPABILITY_UNSUPPORTED,
            f"unsupported action class: {action_class}",
            "ROUTING_ACTION_CLASS_UNSUPPORTED",
        )
    requested_actions = {str(item) for item in contract.get("requested_actions") or []}
    target_kind = str(contract.get("target_kind") or "")
    program_lock_digest = (
        str(contract.get("program_lock_digest") or contract.get("program_digest") or "") or None
    )
    preferences = policy.get("preference", {}).get(action_class) or []
    entries = {str(item["adapter_id"]): dict(item) for item in registry.get("adapters") or []}
    reasons: dict[str, list[str]] = {}
    for adapter_id in preferences:
        entry = entries.get(str(adapter_id))
        if entry is None:
            continue
        adapter_reasons = _adapter_rejection_reasons(
            root=root,
            entry=entry,
            required_kind=required_kind,
            requested_actions=requested_actions,
            target_kind=target_kind,
            capability_receipts=capability_receipts,
            program_lock_digest=program_lock_digest,
        )
        if not adapter_reasons:
            return {
                "status": "PASS",
                "adapter_id": str(adapter_id),
                "action_class": action_class,
                "requested_actions": sorted(requested_actions),
            }
        reasons[str(adapter_id)] = adapter_reasons
    raise AdapterFailure(
        CanonicalErrorCode.CAPABILITY_UNSUPPORTED,
        "no eligible adapter satisfies the contract",
        "NO_ELIGIBLE_ADAPTER",
        evidence=[{"routing_rejections": reasons}],
    )

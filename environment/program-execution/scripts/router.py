from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from adapters.common.errors import AdapterFailure, CanonicalErrorCode

KIND_BY_ACTION_CLASS = {
    "repository_implementation": "worker_host",
    "interactive_local_repair": "worker_host",
    "read_only_architecture_or_artifact_work": "worker_host",
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
        if not receipt or receipt.get("status") != "PASS":
            reasons.append("fresh_capability_receipt_required")
    return reasons


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

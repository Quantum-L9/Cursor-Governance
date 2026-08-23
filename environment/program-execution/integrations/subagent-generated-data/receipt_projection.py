from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any


def _completion_status(receipt: Mapping[str, Any]) -> str:
    raw = (
        str(
            receipt.get("completion_status")
            or receipt.get("verdict")
            or receipt.get("claimed_status")
            or receipt.get("status")
            or "partial"
        )
        .strip()
        .lower()
    )
    if raw in {"pass", "passed", "passed_local", "complete", "completed", "success"}:
        return "completed"
    if raw in {"fail", "failed", "failure", "rejected"}:
        return "failed"
    if raw in {"blocked", "incomplete"}:
        return "blocked"
    return "partial"


def _packet_id(seed: Mapping[str, Any]) -> str:
    digest = hashlib.sha256(
        json.dumps(seed, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()
    return f"pes:{digest[:32]}"


def generated_data_packet(
    receipt: Mapping[str, Any],
    *,
    repository: str,
    base_sha: str,
    agent_id: str,
    campaign_id: str | None = None,
    graph_id: str | None = None,
    repository_class: str = "governed_repository",
) -> dict[str, Any]:
    """Project a PE task outcome into the canonical SubagentDataPacket shape."""

    task_id = str(receipt.get("task_id") or receipt.get("action_id") or "unknown-task")
    campaign = str(campaign_id or receipt.get("campaign_id") or f"pes-{task_id}")
    graph = str(graph_id or receipt.get("graph_id") or f"{campaign}-graph")
    generated_at = str(
        receipt.get("generated_at")
        or receipt.get("verified_at")
        or receipt.get("completed_at")
        or receipt.get("created_at")
        or receipt.get("observed_at")
        or ""
    ).strip()
    if not generated_at:
        raise ValueError("PE outcome receipt requires a stable generated_at/verified_at timestamp")
    artifact_id = str(receipt.get("evidence_id") or receipt.get("receipt_id") or task_id)
    raw_units = receipt.get("generated_data_units") or receipt.get("reusable_findings") or []
    visibility = str(receipt.get("visibility") or "campaign_local")
    generated_units = []
    for item in raw_units:
        if not isinstance(item, Mapping):
            continue
        unit = dict(item)
        unit.setdefault("visibility", visibility)
        generated_units.append(unit)
    reusable = bool(generated_units)
    reuse = receipt.get("reuse_assessment")
    if isinstance(reuse, Mapping):
        reusable = bool(reuse.get("reusable_data_found", reusable))
        confidence = float(reuse.get("confidence", 1.0 if reusable else 0.0))
        reason = str(
            reuse.get("reason")
            or ("PE outcome contains reusable findings" if reusable else "No reusable PE finding")
        )
        reuse_assessment = {
            "reusable_data_found": reusable,
            "task_local_value": int(reuse.get("task_local_value", 0)),
            "cross_task_value": int(reuse.get("cross_task_value", 0)),
            "cross_repository_value": int(reuse.get("cross_repository_value", 0)),
            "confidence": max(0.0, min(1.0, confidence)),
            "reason": reason,
        }
    else:
        reuse_assessment = {
            "reusable_data_found": reusable,
            "task_local_value": 1 if reusable else 0,
            "cross_task_value": 1 if reusable else 0,
            "cross_repository_value": 0,
            "confidence": 1.0 if reusable else 0.0,
            "reason": (
                "PE outcome contains reusable findings"
                if reusable
                else "PE outcome contained no reusable generated-data units"
            ),
        }
    seed = {
        "campaign_id": campaign,
        "task_id": task_id,
        "artifact_id": artifact_id,
        "base_sha": base_sha,
    }
    unresolved = receipt.get("unresolved_unknowns") or receipt.get("residual_unknowns") or []
    return {
        "schema_version": "1.0.0",
        "packet_id": _packet_id(seed),
        "identity": {
            "campaign_id": campaign,
            "graph_id": graph,
            "repository": repository,
            "repository_class": repository_class,
            "base_sha": base_sha,
            "action_id": task_id,
            "agent_id": agent_id,
            "role": "executor",
            "lease_id": str(receipt.get("lease_id") or "program-controller"),
        },
        "primary_result": {
            "artifact_id": artifact_id,
            "artifact_kind": str(receipt.get("schema") or "execution_receipt"),
            "completion_status": _completion_status(receipt),
        },
        "generated_data_units": generated_units,
        "generated_data_assessment": {
            "reusable_data_found": reusable,
            "reason": reuse_assessment["reason"],
        },
        "unresolved_unknowns": [dict(item) for item in unresolved if isinstance(item, Mapping)],
        "provenance": {
            "repository": repository,
            "repository_class": repository_class,
            "base_sha": base_sha,
            "input_artifacts": [str(item) for item in receipt.get("input_artifacts", []) if item],
            "evidence_artifacts": [artifact_id],
            "inspected_paths": [str(item) for item in receipt.get("inspected_paths", []) if item],
            "executed_commands": [
                str(item) for item in receipt.get("executed_commands", []) if item
            ],
            "generated_at": generated_at,
        },
        "reuse_assessment": reuse_assessment,
        "visibility": visibility,
        "generated_at": generated_at,
    }

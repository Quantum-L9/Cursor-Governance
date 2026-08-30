from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

_MEMORY_CLASSES = frozenset(
    {
        "repository_fact",
        "dependency_finding",
        "implementation_surface",
        "rejected_approach",
        "context_requirement",
        "artifact_lineage",
    }
)

_PASSED = frozenset({"passed_local", "pass", "passed", "completed", "success"})


def _as_str_list(value: object) -> list[str]:
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    items: list[str] = []
    for item in value:
        text = str(item).strip() if item is not None else ""
        if text and text not in items:
            items.append(text)
    return items


def _verdict(receipt: Mapping[str, Any], verification: Mapping[str, Any] | None) -> str:
    raw = ""
    if isinstance(verification, Mapping):
        raw = str(verification.get("verdict") or verification.get("status") or "")
    if not raw:
        raw = str(
            receipt.get("verdict")
            or receipt.get("claimed_status")
            or receipt.get("completion_status")
            or receipt.get("status")
            or ""
        )
    return raw.strip().lower()


def _passed_local(receipt: Mapping[str, Any], verification: Mapping[str, Any] | None) -> bool:
    if _verdict(receipt, verification) in _PASSED:
        return True
    if isinstance(verification, Mapping):
        gates = verification.get("gates")
        if isinstance(gates, Mapping) and gates and all(str(v) == "PASS" for v in gates.values()):
            return True
    return False


def _unit_id(prefix: str, index: int) -> str:
    return f"pes-{prefix}-{index:03d}"


def _path_evidence(
    *,
    source_id: str,
    path: str,
    repository: str,
    base_sha: str,
) -> dict[str, str]:
    return {
        "source_id": source_id,
        "source_type": "repository_path",
        "repository": repository,
        "path": path,
        "base_sha": base_sha,
        "locator": "file",
    }


def _scope(*, repository: str, paths: list[str], task_id: str) -> dict[str, Any]:
    scope: dict[str, Any] = {"repositories": [repository], "task_id": task_id}
    if paths:
        scope["paths"] = paths
    return scope


def _freshness(*, generated_at: str, base_sha: str) -> dict[str, Any]:
    return {"observed_at": generated_at, "base_sha": base_sha, "expires_at": None}


def compile_generated_data_units(
    receipt: Mapping[str, Any],
    *,
    repository: str,
    base_sha: str,
    generated_at: str,
    verification: Mapping[str, Any] | None = None,
    failure_reason: str | None = None,
) -> dict[str, Any]:
    """Compile PacketValidator-valid units from observed PE evidence only.

    Provider-authored ``generated_data_units`` are returned unchanged when the
    list is non-empty. An empty result is an explicit empty assessment, not a
    silent success.
    """

    existing = receipt.get("generated_data_units") or receipt.get("reusable_findings") or []
    if isinstance(existing, list) and any(isinstance(item, Mapping) for item in existing):
        units = [dict(item) for item in existing if isinstance(item, Mapping)]
        return {
            "units": units,
            "compiled": False,
            "reuse_assessment": {
                "reusable_data_found": bool(units),
                "task_local_value": 1 if units else 0,
                "cross_task_value": 1 if units else 0,
                "cross_repository_value": 0,
                "confidence": 1.0 if units else 0.0,
                "reason": "PE outcome contains reusable findings"
                if units
                else "PE outcome contained no reusable generated-data units",
            },
        }

    task_id = str(receipt.get("task_id") or receipt.get("action_id") or "unknown-task")
    changed = _as_str_list(receipt.get("changed_files"))
    if isinstance(verification, Mapping):
        changed = _as_str_list(verification.get("observed_changed_files")) or changed
        changed = changed or _as_str_list(verification.get("declared_changed_files"))
    validations = []
    for key in ("validation_results",):
        raw = receipt.get(key)
        if isinstance(raw, list):
            validations.extend(item for item in raw if isinstance(item, Mapping))
    if isinstance(verification, Mapping):
        raw_validations = verification.get("validations")
        if isinstance(raw_validations, list):
            validations.extend(item for item in raw_validations if isinstance(item, Mapping))
        gates = verification.get("gates")
        if isinstance(gates, Mapping) and gates:
            validations.append({"gates": dict(gates), "status": "PASS" if _passed_local(receipt, verification) else "FAIL"})
    produced = []
    raw_evidence = receipt.get("produced_evidence")
    if isinstance(raw_evidence, list):
        produced.extend(item for item in raw_evidence if isinstance(item, Mapping) or str(item).strip())
    unknowns: list[object] = []
    for key in ("residual_unknowns", "unresolved_unknowns"):
        raw = receipt.get(key)
        if isinstance(raw, list):
            unknowns.extend(raw)
        if isinstance(verification, Mapping):
            extra = verification.get(key)
            if isinstance(extra, list):
                unknowns.extend(extra)
    reason = failure_reason or (str(receipt.get("failure_reason") or "").strip() or None)
    passed = _passed_local(receipt, verification)
    units: list[dict[str, Any]] = []
    index = 1

    if changed:
        primary = "implementation_surface"
        routes = ["memory"] if passed and primary in _MEMORY_CLASSES else ["evidence"]
        units.append(
            {
                "unit_id": _unit_id("changed", index),
                "primary_class": primary,
                "epistemic_status": "observed",
                "statement": f"Task {task_id} changed files: {', '.join(changed)}",
                "source_evidence": [
                    _path_evidence(
                        source_id=f"changed-{n}",
                        path=path,
                        repository=repository,
                        base_sha=base_sha,
                    )
                    for n, path in enumerate(changed, start=1)
                ],
                "scope": _scope(repository=repository, paths=changed, task_id=task_id),
                "confidence": 0.9 if passed else 0.8,
                "freshness": _freshness(generated_at=generated_at, base_sha=base_sha),
                "proposed_routes": routes,
                "expected_reuse": {
                    "task_local": True,
                    "cross_task": True,
                    "cross_campaign": False,
                    "cross_repository": False,
                    "description": "Later tasks should treat these paths as the observed write set.",
                },
                "invalidation_conditions": [
                    {"condition_type": "relevant_path_changed", "selector": path} for path in changed
                ],
                "self_promoted": False,
                "visibility": str(receipt.get("visibility") or "campaign_local"),
            }
        )
        index += 1

    if validations:
        gate_bits: list[str] = []
        for item in validations:
            if "gates" in item and isinstance(item["gates"], Mapping):
                gate_bits.extend(f"{name}={value}" for name, value in item["gates"].items())
            else:
                name = str(item.get("name") or item.get("id") or item.get("check") or "check")
                status = str(item.get("status") or item.get("result") or "UNKNOWN")
                gate_bits.append(f"{name}={status}")
        statement = f"Task {task_id} validations: {', '.join(gate_bits) if gate_bits else 'recorded'}"
        units.append(
            {
                "unit_id": _unit_id("validation", index),
                "primary_class": "validation_procedure",
                "epistemic_status": "observed",
                "statement": statement,
                "source_evidence": [
                    {
                        "source_id": "verification",
                        "source_type": "test_result",
                        "repository": repository,
                        "base_sha": base_sha,
                        "test_id": task_id,
                        "description": statement,
                    }
                ],
                "scope": _scope(repository=repository, paths=changed, task_id=task_id),
                "confidence": 0.85,
                "freshness": _freshness(generated_at=generated_at, base_sha=base_sha),
                "proposed_routes": ["validation", "evidence"],
                "self_promoted": False,
                "visibility": str(receipt.get("visibility") or "campaign_local"),
            }
        )
        index += 1

    for item in produced:
        label = ""
        if isinstance(item, Mapping):
            label = str(item.get("id") or item.get("path") or item.get("kind") or "").strip()
        else:
            label = str(item).strip()
        if not label:
            continue
        units.append(
            {
                "unit_id": _unit_id("evidence", index),
                "primary_class": "evidence_only",
                "epistemic_status": "observed",
                "statement": f"Task {task_id} produced evidence: {label}",
                "source_evidence": [
                    {
                        "source_id": f"produced-{index}",
                        "source_type": "typed_artifact",
                        "repository": repository,
                        "base_sha": base_sha,
                        "description": label,
                    }
                ],
                "scope": _scope(repository=repository, paths=changed, task_id=task_id),
                "confidence": 0.8,
                "freshness": _freshness(generated_at=generated_at, base_sha=base_sha),
                "proposed_routes": ["evidence"],
                "self_promoted": False,
                "visibility": str(receipt.get("visibility") or "campaign_local"),
            }
        )
        index += 1

    for item in unknowns:
        if isinstance(item, Mapping):
            text = str(item.get("description") or item.get("unknown_id") or "").strip()
        else:
            text = str(item).strip()
        if not text:
            continue
        units.append(
            {
                "unit_id": _unit_id("unknown", index),
                "primary_class": "unresolved_unknown",
                "epistemic_status": "unresolved",
                "statement": f"Task {task_id} unresolved: {text}",
                "source_evidence": [
                    {
                        "source_id": f"unknown-{index}",
                        "source_type": "review_finding",
                        "repository": repository,
                        "base_sha": base_sha,
                        "description": text,
                    }
                ],
                "scope": _scope(repository=repository, paths=changed, task_id=task_id),
                "confidence": 0.5,
                "freshness": _freshness(generated_at=generated_at, base_sha=base_sha),
                "proposed_routes": ["unknowns"],
                "self_promoted": False,
                "visibility": str(receipt.get("visibility") or "campaign_local"),
            }
        )
        index += 1

    if reason:
        units.append(
            {
                "unit_id": _unit_id("failure", index),
                "primary_class": "failure_pattern",
                "epistemic_status": "observed",
                "statement": f"Task {task_id} failed: {reason}",
                "source_evidence": [
                    {
                        "source_id": "failure-reason",
                        "source_type": "command_receipt",
                        "repository": repository,
                        "base_sha": base_sha,
                        "command": "peer-execution",
                        "description": reason,
                    }
                ],
                "scope": _scope(repository=repository, paths=changed, task_id=task_id),
                "confidence": 0.85,
                "freshness": _freshness(generated_at=generated_at, base_sha=base_sha),
                "proposed_routes": ["evidence"],
                "self_promoted": False,
                "visibility": str(receipt.get("visibility") or "campaign_local"),
            }
        )

    reusable = bool(units)
    if reusable:
        reason_text = "Compiled reusable PE findings from observed attempt and verification evidence"
    else:
        reason_text = (
            "PE task supplied no extractable evidence "
            "(no changed_files, validations, produced_evidence, unknowns, or failure_reason)"
        )
    return {
        "units": units,
        "compiled": True,
        "inspected_paths": changed,
        "reuse_assessment": {
            "reusable_data_found": reusable,
            "task_local_value": 1 if reusable else 0,
            "cross_task_value": 1 if reusable else 0,
            "cross_repository_value": 0,
            "confidence": 0.9 if reusable else 0.0,
            "reason": reason_text,
        },
    }

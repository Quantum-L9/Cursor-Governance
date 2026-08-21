#!/usr/bin/env python3
"""PLAN window: nuggets.json plus seal check. No essay. No pass counts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

SEALABLE = frozenset({"Ready", "ConditionallyReady"})


class NuggetError(RuntimeError):
    pass


def _task_ready(item: dict[str, Any]) -> bool:
    return bool(
        item.get("actions")
        and item.get("nugget_id")
        and item.get("consumers")
        and item.get("entrypoints")
        and item.get("validation")
    )


def _task_conditionally_ready(item: dict[str, Any]) -> bool:
    """Compiled memo/plan tasks carry title + objective. Kernel fields come later."""
    return bool(str(item.get("title") or "").strip() and str(item.get("objective") or "").strip())


def infer_plan_status(seed: dict[str, Any]) -> str:
    explicit = str(seed.get("plan_status") or "").strip()
    if explicit in {"Ready", "ConditionallyReady", "Partial", "Blocked", "Failed", "Draft"}:
        return "Partial" if explicit == "Draft" else explicit
    tasks = [item for item in (seed.get("tasks") or []) if isinstance(item, dict)]
    if tasks and all(_task_ready(item) for item in tasks):
        return "Ready"
    if tasks and all(_task_conditionally_ready(item) for item in tasks):
        return "ConditionallyReady"
    if tasks:
        return "Partial"
    return "Blocked"


def extract_nuggets(
    seed: dict[str, Any],
    primed_campaign_dir: Path,
    stack_proof_path: Path | None = None,
) -> dict[str, Any]:
    campaign_id = str(seed.get("campaign_id") or primed_campaign_dir.name).strip()
    if not campaign_id:
        raise NuggetError("campaign_id required")
    stack_proof = (
        Path(stack_proof_path) if stack_proof_path else primed_campaign_dir / "stack-proof.json"
    )
    if not stack_proof.is_file():
        parent_proof = primed_campaign_dir.parent / campaign_id / "stack-proof.json"
        if parent_proof.is_file():
            stack_proof = parent_proof
    nuggets: list[dict[str, Any]] = []
    projected_tasks: list[dict[str, Any]] = []
    for index, item in enumerate(seed.get("tasks") or [], start=1):
        if not isinstance(item, dict):
            continue
        nugget_id = str(item.get("nugget_id") or f"NUG-{index:03d}").strip()
        projected = dict(item)
        projected["nugget_id"] = nugget_id
        projected_tasks.append(projected)
        record = {
            "id": nugget_id,
            "nugget_id": nugget_id,
            "kind": "task",
            "task_title": str(item.get("title") or ""),
            "claim": str(item.get("objective") or item.get("title") or "").strip(),
        }
        if stack_proof.is_file():
            record["cites"] = "stack-proof.json"
            record["stack_proof"] = str(stack_proof)
        nuggets.append(record)
    if stack_proof.is_file():
        nuggets.append(
            {
                "id": f"nugget-stack-{campaign_id}",
                "kind": "stack",
                "cites": "stack-proof.json",
                "path": str(stack_proof),
            }
        )
    if not nuggets:
        raise NuggetError("no nuggets; refuse empty PLAN window")
    target = primed_campaign_dir / "nuggets.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "l9.program-execution.nuggets.v1",
        "campaign_id": campaign_id,
        "nuggets": nuggets,
    }
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    projected_seed = dict(seed)
    projected_seed["tasks"] = projected_tasks
    projected_seed["plan_status"] = infer_plan_status(projected_seed)
    return {
        "path": str(target),
        "count": len(nuggets),
        "seed": projected_seed,
        "stack_cited": stack_proof.is_file(),
    }


def project_plan_window(
    seed: dict[str, Any], primed_dir: Path, stack_proof_path: Path
) -> dict[str, Any]:
    primed_dir.mkdir(parents=True, exist_ok=True)
    result = extract_nuggets(seed, primed_dir, stack_proof_path)
    projected = result["seed"]
    intent_path = primed_dir / "activate-seed.yaml"
    if yaml is None:
        raise NuggetError("PyYAML required")
    intent_path.write_text(
        yaml.safe_dump(projected, sort_keys=False, allow_unicode=True, width=88),
        encoding="utf-8",
    )
    return {
        "plan_status": projected.get("plan_status"),
        "intent_path": str(intent_path),
        "stack_proof": str(stack_proof_path),
        "nuggets": result["path"],
        "path": result["path"],
        "seed": projected,
        "stack_cited": result["stack_cited"],
    }

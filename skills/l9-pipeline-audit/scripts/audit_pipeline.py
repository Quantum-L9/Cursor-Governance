#!/usr/bin/env python3
"""Classify plans, WIP, and PE campaigns with the same component verdicts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

PLAN_AUDIT = Path(__file__).resolve().parents[2] / "l9-plan-audit" / "scripts"
if str(PLAN_AUDIT) not in sys.path:
    sys.path.insert(0, str(PLAN_AUDIT))
from audit_plans import audit  # noqa: E402

SPENT_CAMPAIGN = frozenset({"complete", "completed", "cancelled", "spent", "converged"})
STALE_WIP = frozenset({"possible-landed", "landed", "pruned"})


def _load_yaml(path: Path) -> dict[str, Any]:
    if yaml is None or not path.is_file():
        return {}
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def scan_plans(workspace: Path, window_days: float) -> list[dict[str, Any]]:
    plans_dir = workspace / "docs" / "plans"
    if not plans_dir.is_dir():
        return []
    findings, _meta = audit(
        plans_dir=plans_dir,
        workspace=workspace,
        window_days=window_days,
        limit=50,
        deadline=1e18,
    )
    rows: list[dict[str, Any]] = []
    for finding in findings:
        rows.append(
            {
                "surface": "plans",
                "path": finding.path,
                "name": finding.name,
                "flags": list(finding.flags),
                "harvestable": "harvestable" in finding.flags,
            }
        )
    return rows


def scan_wip(workspace: Path) -> list[dict[str, Any]]:
    inventory = _load_yaml(workspace / "WIP" / "INVENTORY.yaml")
    entries = inventory.get("entries") or []
    rows: list[dict[str, Any]] = []
    for item in entries:
        if not isinstance(item, dict):
            continue
        rel = str(item.get("path") or "")
        if not rel.startswith("WIP/") or "Legal Defense" in rel:
            continue
        status = str(item.get("status") or "active").lower()
        stale = status in STALE_WIP
        live = status == "active" or status == "possible-landed"
        harvestable = status == "possible-landed"
        flags: list[str] = []
        if live:
            flags.append("live_invariant")
        if stale:
            flags.append("stale_wiring")
        if harvestable:
            flags.append("harvestable")
        rows.append(
            {
                "surface": "wip",
                "path": str(workspace / rel),
                "name": Path(rel).name,
                "flags": flags,
                "harvestable": harvestable,
                "status": status,
            }
        )
    return rows


def scan_campaigns(workspace: Path) -> list[dict[str, Any]]:
    root = workspace / "environment" / "program-execution" / "campaigns"
    if not root.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for source in sorted(root.glob("*/CAMPAIGN_SOURCE.yaml")):
        if "environment/program-execution/environment" in source.as_posix():
            continue
        data = _load_yaml(source)
        meta = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
        name = str(meta.get("campaign_id") or source.parent.name)
        status = str(meta.get("status") or "").lower()
        plan_status = str(data.get("plan_status") or "").lower()
        lifecycle = str(meta.get("lifecycle") or "").lower()
        spent = any(token in SPENT_CAMPAIGN for token in (status, plan_status, lifecycle))
        objective = ""
        directive = data.get("operator_directive")
        if isinstance(directive, dict):
            objective = str(directive.get("objective") or "")
        live = bool(objective) or not spent
        harvestable = live and spent
        flags: list[str] = []
        if live:
            flags.append("live_invariant")
        if spent:
            flags.append("superseded_mission")
        if harvestable:
            flags.append("harvestable")
        rows.append(
            {
                "surface": "campaigns",
                "path": str(source),
                "name": name,
                "flags": flags,
                "harvestable": harvestable,
                "status": status or plan_status or lifecycle,
            }
        )
    return rows


def run(workspace: Path, window_days: float) -> dict[str, Any]:
    findings = [
        *scan_plans(workspace, window_days),
        *scan_wip(workspace),
        *scan_campaigns(workspace),
    ]
    return {
        "workspace": str(workspace),
        "findings": findings,
        "harvestable": [row for row in findings if row.get("harvestable")],
        "counts": {
            "plans": sum(1 for row in findings if row["surface"] == "plans"),
            "wip": sum(1 for row in findings if row["surface"] == "wip"),
            "campaigns": sum(1 for row in findings if row["surface"] == "campaigns"),
            "harvestable": sum(1 for row in findings if row.get("harvestable")),
        },
    }


def format_markdown(payload: dict[str, Any]) -> str:
    counts = payload.get("counts") or {}
    lines = [
        f"- pipeline audit: plans={counts.get('plans', 0)} "
        f"wip={counts.get('wip', 0)} campaigns={counts.get('campaigns', 0)} "
        f"harvestable={counts.get('harvestable', 0)}"
    ]
    harvestable = payload.get("harvestable") or []
    if not harvestable:
        lines.append("- none: no harvestable components")
        return "\n".join(lines)
    for row in harvestable[:30]:
        flags = ",".join(row.get("flags") or []) or "unbuilt"
        lines.append(
            f"- HARVESTABLE: {row.get('surface')} / {row.get('name')} — {flags}; "
            f"`{Path(str(row.get('path'))).name}`"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--window-days", type=float, default=7.0)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args(argv)
    workspace = Path(args.workspace).expanduser().resolve()
    payload = run(workspace, float(args.window_days))
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    print(format_markdown(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

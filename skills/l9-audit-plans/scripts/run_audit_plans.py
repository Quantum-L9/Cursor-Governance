#!/usr/bin/env python3
"""Single /l9-audit-plans invoke: shelf → refine → shelf → README."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
AUDIT_SCRIPTS = SCRIPTS.parents[2] / "l9-pipeline-audit" / "scripts"
if str(AUDIT_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(AUDIT_SCRIPTS))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from audit_plans import resolve_plans_dir  # noqa: E402
from refine_plans import refine, rewrite_live_queue  # noqa: E402
from shelf_plans import TEMPLATE_NAME, _iter_plan_mds, format_markdown, shelf  # noqa: E402


def invoke(plans_dir: Path, workspace: Path, today: date) -> dict:
    first = shelf(plans_dir, workspace, today)
    refine_skipped = os.environ.get("L9_AUDIT_PLANS_REFINE", "1").strip() == "0"
    refined: dict = {"actions": [], "root_now": first.get("root_now") or [], "readme": False}
    if not refine_skipped:
        refined = refine(plans_dir)
        second = shelf(plans_dir, workspace, today)
        root_now = sorted(p.name for p in _iter_plan_mds(plans_dir) if p.name != TEMPLATE_NAME)
        readme = rewrite_live_queue(plans_dir, root_now)
        refined["root_now"] = root_now
        refined["readme"] = bool(refined.get("readme") or readme)
        first = {
            **first,
            "actions": list(first.get("actions") or []) + list(second.get("actions") or []),
        }
        first["root_now"] = root_now
    return {
        "shelf": first,
        "refine": refined,
        "refine_skipped": refine_skipped,
        "root_now": first.get("root_now") or [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=os.environ.get("CURSOR_PROJECT_DIR") or os.getcwd())
    parser.add_argument("--plans-dir", default=None)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--today", default=None)
    args = parser.parse_args(argv)
    workspace = Path(args.workspace).expanduser().resolve()
    plans_dir = resolve_plans_dir(workspace, args.plans_dir)
    if args.plans_dir:
        plans_dir = Path(args.plans_dir).expanduser().resolve()
    today = date.fromisoformat(args.today) if args.today else datetime.now().date()
    if not plans_dir.is_dir():
        print("plan audit: no plans dir")
        return 0
    payload = invoke(plans_dir, workspace, today)
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    print(format_markdown(payload["shelf"]))
    if payload["refine_skipped"]:
        print("- refine skipped (L9_AUDIT_PLANS_REFINE=0)")
    else:
        for action in payload["refine"].get("actions") or []:
            print(f"- refine: {action}")
        if payload["refine"].get("readme"):
            print("- README live-queue rewritten")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

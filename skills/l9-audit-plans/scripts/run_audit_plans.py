#!/usr/bin/env python3
"""Single /l9-audit-plans invoke: refine, then rewrite the README live queue.

shelf_plans.py is retired and is not imported. This command does not move plans.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
AUDIT_SCRIPTS = SCRIPTS.parents[1] / "l9-pipeline-audit" / "scripts"
if str(AUDIT_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(AUDIT_SCRIPTS))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from audit_plans import TEMPLATE_NAME, resolve_plans_dir  # noqa: E402
from refine_plans import _iter_plan_mds, format_markdown, refine  # noqa: E402


def invoke(plans_dir: Path, workspace: Path) -> dict:
    del workspace  # retained so callers keep the old signature
    refine_skipped = os.environ.get("L9_AUDIT_PLANS_REFINE", "1").strip() == "0"
    if refine_skipped:
        root_now = sorted(p.name for p in _iter_plan_mds(plans_dir) if p.name != TEMPLATE_NAME)
        return {
            "refine": {"actions": [], "root_now": root_now, "readme": False},
            "refine_skipped": True,
            "root_now": root_now,
        }
    refined = refine(plans_dir)
    return {
        "refine": refined,
        "refine_skipped": False,
        "root_now": refined.get("root_now") or [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=os.environ.get("CURSOR_PROJECT_DIR") or os.getcwd())
    parser.add_argument("--plans-dir", default=None)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--today", default=None, help="Ignored. Kept so older invokes still parse.")
    args = parser.parse_args(argv)
    del args.today
    workspace = Path(args.workspace).expanduser().resolve()
    plans_dir = resolve_plans_dir(workspace, args.plans_dir)
    if args.plans_dir:
        plans_dir = Path(args.plans_dir).expanduser().resolve()
    if not plans_dir.is_dir():
        print("plan audit: no plans dir")
        return 0
    payload = invoke(plans_dir, workspace)
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if payload["refine_skipped"]:
        print("- refine skipped (L9_AUDIT_PLANS_REFINE=0)")
        return 0
    print(format_markdown(payload["refine"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

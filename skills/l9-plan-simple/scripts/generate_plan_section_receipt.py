#!/usr/bin/env python3
"""Write a section-completeness receipt for a simple plan pair."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from paths import is_under, safe_cli_path
from plan_sections import (
    GAR_SKILL_REF,
    PLAN_SCHEMA_REL,
    REPO_ROOT,
    TEMPLATE_REL,
    execute_swap_presence,
    frontmatter_presence,
    handoff_mode,
    json_section_presence,
    md_section_presence,
    projection_marker_errors,
    receipt_status,
    unfilled_parameters,
    workspace_root,
)

RECEIPT_KIND = "simple_plan_section_receipt"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rel(path: Path) -> str:
    """Workspace-relative when inside the planned repository, else absolute.

    Never a bare filename: the validator must find the file again from any
    directory of the same workspace.
    """
    resolved = path.resolve()
    workspace = workspace_root()
    if is_under(resolved, workspace):
        return resolved.relative_to(workspace).as_posix()
    return resolved.as_posix()


def _gar_module():
    script_dir = REPO_ROOT / "skills" / "l9-global-architect" / "scripts"
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    import write_plan_run

    return write_plan_run


def build_receipt(
    plan_json_path: Path,
    plan_md_path: Path,
    *,
    gar_invoked: bool,
    gar_run_id: str | None,
    gar_run: Path | None = None,
) -> dict[str, Any]:
    plan = json.loads(plan_json_path.read_text(encoding="utf-8"))
    if not isinstance(plan, dict):
        raise ValueError("plan JSON root must be an object")
    md_text = plan_md_path.read_text(encoding="utf-8")
    json_sections = json_section_presence(plan)
    md_sections = md_section_presence(md_text)
    frontmatter = frontmatter_presence(md_text)
    execute_swap = execute_swap_presence(md_text)
    mode = handoff_mode(md_text)
    unfilled = unfilled_parameters(md_text, plan)
    markers = projection_marker_errors(md_text)
    run_rel = None
    run_sha = None
    run_id = gar_run_id
    gar_run_ok = False
    if gar_run is not None and gar_run.is_file():
        problems = _gar_module().verify_run(gar_run)
        gar_run_ok = not problems
        run_sha = _sha256(gar_run)
        run_rel = _rel(gar_run)
        try:
            payload = json.loads(gar_run.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
        if isinstance(payload, dict) and payload.get("run_id"):
            run_id = str(payload["run_id"])
    claimed = bool(gar_invoked) or gar_run is not None
    return {
        "schema_version": "1.0.0",
        "kind": RECEIPT_KIND,
        "generated_at": datetime.now(UTC).isoformat(),
        "plan_json_path": _rel(plan_json_path),
        "plan_md_path": _rel(plan_md_path),
        "plan_json_sha256": _sha256(plan_json_path),
        "plan_md_sha256": _sha256(plan_md_path),
        "section_schema_ref": PLAN_SCHEMA_REL,
        "template_ref": TEMPLATE_REL,
        "handoff_mode": mode,
        "gar_upstream": {
            "invoked": claimed,
            "skill_ref": GAR_SKILL_REF,
            "run_id": run_id,
            "run_path": run_rel,
            "run_sha256": run_sha,
        },
        "json_sections": json_sections,
        "md_sections": md_sections,
        "frontmatter": frontmatter,
        "execute_swap": execute_swap,
        "unfilled_parameters": unfilled,
        "status": receipt_status(
            json_sections,
            md_sections,
            frontmatter,
            execute_swap,
            gar_run_ok,
            unfilled,
            markers,
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-json", required=True, help="PLAN_DOCUMENT JSON")
    parser.add_argument("--plan-md", required=True, help="projected .plan.md")
    parser.add_argument("--out", required=True, help="receipt JSON path")
    parser.add_argument(
        "--gar-invoked",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="record that l9-global-architect ran upstream (default: false; pass evidence)",
    )
    parser.add_argument("--gar-run-id", default=None, help="optional GAR run id")
    parser.add_argument(
        "--gar-run",
        default=None,
        help="GAR run file written by write_plan_run.py; required for status pass",
    )
    args = parser.parse_args(argv)
    plan_json = safe_cli_path(args.plan_json)
    plan_md = safe_cli_path(args.plan_md)
    out = safe_cli_path(args.out)
    gar_run = safe_cli_path(args.gar_run) if args.gar_run else None
    try:
        receipt = build_receipt(
            plan_json,
            plan_md,
            gar_invoked=bool(args.gar_invoked),
            gar_run_id=args.gar_run_id,
            gar_run=gar_run,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: cannot build receipt: {exc}", file=sys.stderr)
        return 2
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"{receipt['status'].upper()}: wrote {out}")
    return 0 if receipt["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

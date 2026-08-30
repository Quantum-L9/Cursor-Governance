#!/usr/bin/env python3
"""Bind and inventory donors through l9-intelligence-harvest, then emit packets.

Does not call l9-harvest-pipeline. Does not execute donor code.
Does not implement beneficiary product changes.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).resolve().parent
HARVEST = Path(__file__).resolve().parents[2] / "l9-intelligence-harvest" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from harvest_plan_invariants import (  # noqa: E402
    compile_by_concern,
    emit_compiled_plan,
    extract_invariants,
    reject_implementation,
)


def _run_harvest_script(name: str, *argv: str) -> dict[str, Any]:
    script = HARVEST / name
    if not script.is_file():
        raise SystemExit(f"missing l9-intelligence-harvest script: {script}")
    proc = subprocess.run(
        [sys.executable, str(script), *argv],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(f"{name} failed ({proc.returncode}): {proc.stderr or proc.stdout}")
    if not proc.stdout.strip():
        return {}
    return json.loads(proc.stdout)


def bind_request(request_path: Path, bound_path: Path) -> dict[str, Any]:
    return _run_harvest_script("bind_request.py", str(request_path), str(bound_path))


def inventory_donor(donor: Path) -> dict[str, Any]:
    return _run_harvest_script("inventory_source.py", str(donor))


def emit_wip(concern: str, invariants: list[dict[str, str]], dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Harvested {concern} invariants",
        "",
        "Emitted by l9-pipeline-audit via l9-intelligence-harvest.",
        "Execute via /gmp. Do not run `make campaign`.",
        "",
    ]
    for item in invariants:
        lines.append(f"- {item.get('text')}")
    (dest / "HARVEST.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def emit_campaign_intent(concern: str, invariants: list[dict[str, str]], dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# HARVEST_INTENT — {concern}",
        "",
        "Compiled invariants only. Not a Program Lock. Not CAMPAIGN_SOURCE.yaml.",
        "Execute via /gmp. Do not run `make campaign` from this file.",
        "",
    ]
    for item in invariants:
        lines.append(f"- {item.get('text')}")
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("donors", nargs="+", type=Path)
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--beneficiary", required=True)
    parser.add_argument("--harvest-target", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--concern", default="compiled")
    parser.add_argument(
        "--emit-dest",
        choices=("plan", "wip", "campaign"),
        default="plan",
    )
    parser.add_argument("--emit-path", default=None, type=Path)
    args = parser.parse_args(argv)

    request = {
        "request_id": args.request_id,
        "donor": str(args.donors[0].resolve()),
        "beneficiary": args.beneficiary,
        "harvest_target": args.harvest_target,
        "access_mode": "read-only",
        "depth": "standard",
        "secrets_policy": "redact",
        "language": "as-donor",
        "brief": False,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    request_path = args.out.with_suffix(".request.json")
    bound_path = args.out.with_suffix(".bound.json")
    request_path.write_text(json.dumps(request, indent=2, sort_keys=True) + "\n")
    bind = bind_request(request_path, bound_path)
    inventories = [inventory_donor(path) for path in args.donors]
    extractions = [extract_invariants(path) for path in args.donors]
    grouped = compile_by_concern(extractions)
    concern = args.concern
    invariants = grouped.get(concern) or grouped.get("uncategorized") or []
    payload = {
        "kernel": "skills/l9-intelligence-harvest/SKILL.md",
        "harvest_skill": "l9-intelligence-harvest",
        "implementation": False,
        "bind": bind,
        "inventories": inventories,
        "donors": [path.name for path in args.donors],
        "concerns": grouped,
    }
    reject_implementation(payload)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if args.emit_path:
        if args.emit_dest == "plan":
            emit_compiled_plan(
                concern=concern,
                invariants=invariants,
                donors=[path.name for path in args.donors],
                dest=args.emit_path,
            )
        elif args.emit_dest == "wip":
            emit_wip(concern, invariants, args.emit_path)
        else:
            emit_campaign_intent(concern, invariants, args.emit_path)
    print(f"wrote {args.out} dest={args.emit_dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

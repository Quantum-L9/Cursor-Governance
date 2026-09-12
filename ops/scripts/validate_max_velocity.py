#!/usr/bin/env python3
"""Fail closed if this repo's execution personality leaves maximum_velocity.

Repo invariant (INVARIANTS.md): Cursor and Claude saturate at the same
provider worker target. A committed ``constrained`` Cursor profile, a
``max_parallel`` below 480, or a ``cursor_default`` other than
``maximum_velocity`` is a regression, not a surface preference.

This check is static — it reads the files in the checkout under test, never
``$HOME/.cursor-governance``. Runtime env caps are a different defect class
(``execution_profile.py --fail-on-defect``).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

PROFILE = "maximum_velocity"
MIN_PARALLEL = 480
MIN_MUTATION_LANES = 128
MIN_NATIVE = 480
POLICY_REL = Path("ops/autonomy/claude-execution-profiles.json")
SURFACE_REL = Path("ops/autonomy/surface_profile.yaml")


def _int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def collect_defects(root: Path) -> list[str]:
    defects: list[str] = []
    policy_path = root / POLICY_REL
    surface_path = root / SURFACE_REL
    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{POLICY_REL}: unreadable ({exc})"]
    try:
        surface = yaml.safe_load(surface_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        return [f"{SURFACE_REL}: unreadable ({exc})"]

    # Well-formed JSON/YAML is not necessarily a MAPPING. A top-level list
    # parses cleanly and then raises AttributeError on the first `.get`,
    # crashing the gate instead of failing it closed with a named defect —
    # the opposite of what a fail-closed checker owes its caller.
    for label, doc in ((POLICY_REL, policy), (SURFACE_REL, surface)):
        if not isinstance(doc, dict):
            defects.append(f"{label}: top level is {type(doc).__name__}, expected a mapping")
    if defects:
        return defects

    profiles = policy.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        defects.append(f"{POLICY_REL}: profiles map missing")
        return defects
    for name, row in profiles.items():
        if not isinstance(row, dict):
            defects.append(f"{POLICY_REL}: profiles.{name} is not an object")
            continue
        label = f"{POLICY_REL}: profiles.{name}"
        if row.get("execution_profile") != PROFILE:
            defects.append(
                f"{label}.execution_profile={row.get('execution_profile')!r} (required {PROFILE})"
            )
        parallel = _int(row.get("max_parallel"))
        if parallel is None or parallel < MIN_PARALLEL:
            defects.append(f"{label}.max_parallel={row.get('max_parallel')!r} (min {MIN_PARALLEL})")
        lanes = _int(row.get("max_mutation_lanes"))
        if lanes is None or lanes < MIN_MUTATION_LANES:
            defects.append(
                f"{label}.max_mutation_lanes={row.get('max_mutation_lanes')!r} "
                f"(min {MIN_MUTATION_LANES})"
            )
        native = _int(row.get("native_subagent_limit"))
        if native is None or native < MIN_NATIVE:
            defects.append(
                f"{label}.native_subagent_limit={row.get('native_subagent_limit')!r} "
                f"(min {MIN_NATIVE})"
            )
        if row.get("concurrency_policy") != "saturate":
            defects.append(
                f"{label}.concurrency_policy={row.get('concurrency_policy')!r} (required saturate)"
            )

    block = surface.get("claude_execution_profiles")
    if not isinstance(block, dict):
        defects.append(f"{SURFACE_REL}: claude_execution_profiles missing")
        return defects
    for key in ("cursor_default", "claude_default"):
        if block.get(key) != PROFILE:
            defects.append(
                f"{SURFACE_REL}: claude_execution_profiles.{key}="
                f"{block.get(key)!r} (required {PROFILE})"
            )
    return defects


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None)
    args = parser.parse_args(argv)
    root = (args.root or Path(__file__).resolve().parents[2]).resolve()
    defects = collect_defects(root)
    if defects:
        print("FAIL: maximum-velocity invariant", file=sys.stderr)
        for item in defects:
            print(f"  {item}", file=sys.stderr)
        return 1
    print(
        f"OK: maximum-velocity invariant "
        f"(profile={PROFILE} max_parallel>={MIN_PARALLEL} "
        f"max_mutation_lanes>={MIN_MUTATION_LANES})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Sync local Cursor plan template mirror from first-class git SSOT.

`.cursor/plans/` is gitignored in this repo. Agents/humans MUST run this after
pulling tip so `_TEMPLATE.plan.md` matches:

  environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md

Exit 0 on write/check success; 1 on drift in --check mode; 2 on missing SSOT.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from paths import safe_cli_path

SSOT_REL = Path(
    "environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md"
)
MIRROR_REL = Path(".cursor/plans/_TEMPLATE.plan.md")


def _repo_root_from_skill(skill_root: Path) -> Path:
    # skills/l9-plan -> repo root
    if skill_root.name == "l9-plan" and skill_root.parent.name == "skills":
        return skill_root.parent.parent
    return skill_root.resolve()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "skill_root",
        nargs="?",
        default=".",
        help="Path to skills/l9-plan (default: cwd)",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=None,
        help="Governance repo root (default: parent of skills/)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if mirror exists and differs from SSOT (do not write)",
    )
    args = parser.parse_args()

    skill_root = safe_cli_path(args.skill_root)
    repo = args.repo.resolve() if args.repo else _repo_root_from_skill(skill_root)
    ssot = repo / SSOT_REL
    mirror = repo / MIRROR_REL
    if not ssot.is_file():
        print(f"ERROR: missing SSOT template: {ssot}", file=sys.stderr)
        return 2

    ssot_hash = _sha256(ssot)
    if args.check:
        if not mirror.is_file():
            print(f"OK: mirror absent (optional): {mirror}")
            return 0
        if _sha256(mirror) != ssot_hash:
            print(
                f"FAIL: {mirror} drifted from SSOT {ssot} "
                f"(run: python3 skills/l9-plan/scripts/sync_cursor_plan_template.py)",
                file=sys.stderr,
            )
            return 1
        print(f"PASS: mirror matches SSOT ({ssot_hash[:12]})")
        return 0

    mirror.parent.mkdir(parents=True, exist_ok=True)
    mirror.write_bytes(ssot.read_bytes())
    print(f"WROTE: {mirror} (sha256={ssot_hash})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

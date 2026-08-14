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
import os
import sys
from pathlib import Path

from paths import safe_cli_path

SSOT_REL = "environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md"
MIRROR_REL_PARTS = (".cursor", "plans", "_TEMPLATE.plan.md")


def _repo_root_from_skill(skill_root: Path) -> Path:
    # skills/l9-plan -> repo root
    if skill_root.name == "l9-plan" and skill_root.parent.name == "skills":
        return skill_root.parent.parent
    return skill_root.resolve()


def _under_repo(repo: Path, *parts: str) -> Path:
    """Confine *parts under repo without rejecting governed symlink mirrors.

    Sonar S2083: reject ``..`` / absolute segments and require the *logical*
    join (``os.path.abspath``, no symlink follow) stays under the realpath
    repo root. Using ``realpath`` on the final target incorrectly fails when
    ``.cursor/plans`` is the governed home symlink ``→ ~/.cursor/plans``.
    I/O still goes through the symlink path (write lands in the mirror).
    """
    root = os.path.realpath(str(repo))
    for part in parts:
        if not part or part == os.curdir:
            continue
        if part == os.pardir or os.path.isabs(part):
            raise SystemExit(f"path escapes repo root: invalid segment {part!r}")
        if os.sep in part or (os.altsep and os.altsep in part):
            # Allow nested rel segments only as separate *parts args.
            raise SystemExit(f"path escapes repo root: nested segment {part!r}")
    joined = os.path.join(root, *parts)
    logical = os.path.abspath(joined)
    if os.path.commonpath([root, logical]) != root:
        raise SystemExit(f"path escapes repo root: {logical}")
    return Path(joined)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_mirror(repo: Path, payload: bytes) -> Path:
    mirror = _under_repo(repo, *MIRROR_REL_PARTS)
    plans_dir = _under_repo(repo, ".cursor", "plans")
    os.makedirs(plans_dir, exist_ok=True)
    with open(mirror, "wb") as handle:
        handle.write(payload)
    return mirror


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
    # Repo root is the confinement base for all later joins (_under_repo).
    repo = (
        Path(args.repo).expanduser().resolve() if args.repo else _repo_root_from_skill(skill_root)
    )
    if not repo.is_dir():
        print(f"ERROR: repo root is not a directory: {repo}", file=sys.stderr)
        return 2

    ssot = _under_repo(repo, *SSOT_REL.split("/"))
    mirror = _under_repo(repo, *MIRROR_REL_PARTS)
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

    written = _write_mirror(repo, ssot.read_bytes())
    print(f"WROTE: {written} (sha256={ssot_hash})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

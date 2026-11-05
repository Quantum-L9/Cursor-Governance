#!/usr/bin/env python3
"""Admit a simple plan only when the pipeline section receipt passes.

A title and a paragraph, a ``kind: simple`` plan with no receipt, and a
receipt whose GAR run file is missing all exit non-zero. ``_TEMPLATE.plan.md``
and plans already filed under built or archive shelves are exempt. This
script does not delete a plan file.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from paths import safe_cli_path
from plan_sections import projection_marker_errors
from validate_plan_section_receipt import check_receipt

EXEMPT_NAMES = {"_TEMPLATE.plan.md"}
SHELVED = ("/built/", "/archive/", "/superseded/")


def check_plan(path: Path) -> list[str]:
    if path.name in EXEMPT_NAMES:
        return []
    posix = path.as_posix()
    if any(part in posix for part in SHELVED):
        return []
    if not path.is_file():
        return [f"G_ADMIT: plan file missing: {path}"]
    receipt = path.with_name(path.name.replace(".plan.md", ".section-receipt.json"))
    if not receipt.is_file():
        return [f"G_ADMIT: no section receipt beside {path.name}"]
    errors = check_receipt(receipt)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [*errors, f"G_ADMIT: cannot read plan: {exc}"]
    return [*errors, *projection_marker_errors(text)]


def _git_tracks(path: Path) -> bool:
    """True when the path is in the index. Untracked local plans are not a publish."""
    cwd = Path.cwd().resolve()
    try:
        rel = path.resolve().relative_to(cwd)
    except ValueError:
        return True
    proc = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", rel.as_posix()],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plans", nargs="+", help=".plan.md files to admit")
    parser.add_argument(
        "--all",
        action="store_true",
        help="also check plans git does not track",
    )
    args = parser.parse_args(argv)
    failed = False
    for raw in args.plans:
        path = safe_cli_path(raw)
        if not args.all and not _git_tracks(path):
            print(f"SKIP: {path} is not in the git index")
            continue
        errors = check_plan(path)
        if errors:
            failed = True
            print(f"FAIL: {path}")
            for err in errors:
                print(f"  {err}")
        else:
            print(f"PASS: {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

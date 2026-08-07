#!/usr/bin/env python3
"""Unified CLI for l9-code-maintenance modes with --dry-run support.

Purpose: single entry for refactor-sweep / migrate / lint-fix / status.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
WORKFLOWS = REPO_ROOT / "workflows"


def _run(cmd: list[str]) -> int:
    print("+", " ".join(cmd), file=sys.stderr)
    proc = subprocess.run(cmd, cwd=REPO_ROOT, check=False)
    return int(proc.returncode)


def cmd_refactor_sweep(args: argparse.Namespace) -> int:
    # Always dry-run for this mode.
    if not args.dry_run:
        print("refactor-sweep is analysis-only; forcing --dry-run", file=sys.stderr)
    intent = args.intent or (args.extra[0] if args.extra else "")
    if not intent:
        print("error: refactor-sweep requires an intent string", file=sys.stderr)
        return 2
    sweep = SCRIPT_DIR / "refactor_sweep.py"
    cmd = [sys.executable, str(sweep), intent]
    if args.json:
        cmd.append("--json")
    return _run(cmd)


def cmd_migrate(args: argparse.Namespace) -> int:
    exe = WORKFLOWS / "migrate_executor.py"
    cmd = [sys.executable, str(exe)]
    if args.dry_run:
        cmd.append("--dry-run")
    if args.status:
        cmd.append("--status")
        return _run(cmd)
    # patterns: from --extra or positional leftover
    pats = list(args.extra)
    if len(pats) < 2:
        print('error: migrate requires "old_pattern" "new_pattern"', file=sys.stderr)
        return 2
    cmd.extend(pats[:2])
    return _run(cmd)


def cmd_lint_fix(args: argparse.Namespace) -> int:
    exe = WORKFLOWS / "lint_fix_executor.py"
    cmd = [sys.executable, str(exe)]
    if args.dry_run:
        cmd.append("--dry-run")
    if args.status:
        cmd.append("--status")
        return _run(cmd)
    if args.only:
        cmd.append("--only")
        cmd.extend(args.only)
    return _run(cmd)


def cmd_status(_args: argparse.Namespace) -> int:
    print("l9-code-maintenance CLI")
    print(f"  repo: {REPO_ROOT}")
    print(f"  workflows: {WORKFLOWS}")
    print("  modes: refactor-sweep | migrate | lint-fix | status")
    print("  dry-run: supported (required/default for refactor-sweep)")
    rc1 = _run([sys.executable, str(WORKFLOWS / "migrate_executor.py"), "--status"])
    rc2 = _run([sys.executable, str(WORKFLOWS / "lint_fix_executor.py"), "--status"])
    return 0 if rc1 == 0 and rc2 == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="l9-code-maintenance unified CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 skills/l9-code-maintenance/scripts/code_maintenance.py \\
    --mode refactor-sweep --dry-run "rename foo to bar"
  python3 skills/l9-code-maintenance/scripts/code_maintenance.py \\
    --mode migrate --dry-run -- old_pat new_pat
  python3 skills/l9-code-maintenance/scripts/code_maintenance.py \\
    --mode lint-fix --dry-run
        """,
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=["refactor-sweep", "migrate", "lint-fix", "status"],
        help="Maintenance mode",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analysis only — no writes/commits (default required for refactor-sweep)",
    )
    parser.add_argument("--json", action="store_true", help="JSON output for refactor-sweep")
    parser.add_argument("--intent", default="", help="Intent string for refactor-sweep")
    parser.add_argument("--only", nargs="+", help="lint-fix error codes")
    parser.add_argument("--status", action="store_true", help="Show executor status")
    parser.add_argument("extra", nargs="*", help="Mode-specific args (patterns, intent)")
    args = parser.parse_args(argv)

    # refactor-sweep always dry-run
    if args.mode == "refactor-sweep":
        args.dry_run = True

    handlers = {
        "refactor-sweep": cmd_refactor_sweep,
        "migrate": cmd_migrate,
        "lint-fix": cmd_lint_fix,
        "status": cmd_status,
    }
    return handlers[args.mode](args)


if __name__ == "__main__":
    raise SystemExit(main())

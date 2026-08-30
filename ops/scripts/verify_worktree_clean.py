#!/usr/bin/env python3
"""Verify a workspace meets Claude Code / plan preflight clean criteria.

Hard checks (exit 1 on failure):
  - origin/main resolves after fetch (warn-only if fetch fails offline)
  - HEAD equals origin/main
  - no commits on current branch ahead of origin/main
  - session_end_dirt_close dirty_unique == 0

Soft checks (warn on stderr, still exit 0 unless --strict):
  - current branch is main
  - local feat/ff-shelf-* branches without open PR (requires gh)

Does not prune unreachable objects or re-lock plans.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).resolve().parent
REPO = SCRIPTS.parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _run_dirt_status(root: Path, baseline: str) -> dict[str, Any]:
    proc = subprocess.run(  # noqa: S603
        [
            sys.executable,
            str(SCRIPTS / "session_end_dirt_close.py"),
            "--workspace",
            str(root),
            "--status",
            "--baseline",
            baseline,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return {"dirty_unique": -1, "error": proc.stderr.strip() or proc.stdout.strip()}
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return {"dirty_unique": -1, "error": f"invalid dirt-close json: {exc}"}
    status = payload.get("status") if isinstance(payload.get("status"), dict) else payload
    if not isinstance(status, dict):
        return {"dirty_unique": -1, "error": "unexpected dirt-close shape"}
    return status


def verify(
    root: Path,
    *,
    baseline: str = "origin/main",
    fetch: bool = True,
    strict: bool = False,
) -> tuple[bool, list[str], list[str]]:
    """Return (ok, errors, warnings)."""
    errors: list[str] = []
    warnings: list[str] = []

    if fetch:
        fetch_proc = _git(root, "fetch", "origin")
        if fetch_proc.returncode != 0:
            warnings.append("fetch origin failed (offline?) — comparing to last-known origin/main")

    head_proc = _git(root, "rev-parse", "HEAD")
    base_proc = _git(root, "rev-parse", baseline)
    if head_proc.returncode != 0:
        errors.append("cannot rev-parse HEAD")
        return False, errors, warnings
    if base_proc.returncode != 0:
        errors.append(f"cannot rev-parse {baseline}")
        return False, errors, warnings

    head = head_proc.stdout.strip()
    base = base_proc.stdout.strip()
    if head != base:
        errors.append(f"HEAD {head[:12]} != {baseline} {base[:12]}")

    ahead_proc = _git(root, "rev-list", "--count", f"{baseline}..HEAD")
    if ahead_proc.returncode == 0:
        try:
            ahead = int(ahead_proc.stdout.strip() or "0")
        except ValueError:
            ahead = -1
        if ahead > 0:
            errors.append(f"{ahead} commit(s) ahead of {baseline} (unpushed local work)")
    else:
        warnings.append(f"could not count commits ahead of {baseline}")

    branch_proc = _git(root, "symbolic-ref", "--short", "HEAD")
    branch = branch_proc.stdout.strip() if branch_proc.returncode == 0 else ""
    if branch and branch != "main":
        msg = f"HEAD is branch {branch!r}, not main (plan work may need agent_worktree_start.sh)"
        if strict:
            errors.append(msg)
        else:
            warnings.append(msg)

    dirt = _run_dirt_status(root, baseline)
    dirty_unique = dirt.get("dirty_unique")
    if dirty_unique is None:
        dirty_unique = len(dirt.get("dirty_files") or [])
    if dirty_unique == -1:
        errors.append(
            f"dirt-close status unavailable: {dirt.get('error', 'unknown')}"
        )
    elif dirty_unique != 0:
        errors.append(
            f"dirty_unique={dirty_unique} (run session_end_dirt_close --status for paths)"
        )

    try:
        gh_proc = subprocess.run(  # noqa: S603
            [
                "gh",
                "pr",
                "list",
                "--state",
                "open",
                "--search",
                "head:feat/ff-shelf-",
                "--json",
                "headRefName",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        warnings.append("gh unavailable — skipped feat/ff-shelf-* PR check")
        gh_proc = None
    if gh_proc is not None and gh_proc.returncode == 0:
        try:
            open_shelf = {row["headRefName"] for row in json.loads(gh_proc.stdout or "[]")}
        except (json.JSONDecodeError, KeyError, TypeError):
            open_shelf = set()
        local_proc = _git(root, "branch", "--list", "feat/ff-shelf-*")
        if local_proc.returncode == 0:
            for line in local_proc.stdout.splitlines():
                name = line.strip().lstrip("* ").strip()
                if name.startswith("feat/ff-shelf-") and name not in open_shelf:
                    warnings.append(f"local shelf branch {name!r} has no open PR")
    elif gh_proc is not None:
        warnings.append("gh unavailable — skipped feat/ff-shelf-* PR check")

    ok = not errors
    return ok, errors, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=".", help="git repository root")
    parser.add_argument("--baseline", default="origin/main")
    parser.add_argument("--no-fetch", action="store_true")
    parser.add_argument("--strict", action="store_true", help="treat branch!=main as failure")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.workspace).expanduser().resolve()
    ok, errors, warnings = verify(
        root,
        baseline=args.baseline,
        fetch=not args.no_fetch,
        strict=args.strict,
    )
    report = {"ok": ok, "workspace": str(root), "errors": errors, "warnings": warnings}
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for warn in warnings:
            print(f"WARN: {warn}", file=sys.stderr)
        if ok:
            print(f"OK: worktree clean ({root})")
        else:
            for err in errors:
                print(f"FAIL: {err}", file=sys.stderr)
            print(
                "Remediation: finish /ff shelf publish (PR_REMEDIATE=0 make pr), "
                "run ops/scripts/run_ff_post_shelf.sh, or FF_SHELF_PUBLISH=0 to shelf-only",
                file=sys.stderr,
            )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

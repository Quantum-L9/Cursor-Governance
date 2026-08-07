#!/usr/bin/env python3
"""Point Claude Code `.claude/rules` at the governance rules SSOT.

SSOT: governance `rules/` (== `.cursor-commands/rules`).
Claude adapters get a **directory symlink** to that folder — one rules tree to maintain.

This is intentional for Claude only. Cursor continues to load `rules/` via the
`l9-governance` plugin (rule 84 forbids recreating `~/.cursor/rules` or repo
`.cursor/rules` whole-dir symlinks).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path


def same_link(path: Path, source: Path) -> bool:
    if not path.is_symlink():
        return False
    try:
        return path.resolve(strict=False) == source.resolve(strict=False)
    except OSError:
        return False


def remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path)


def reconcile_one(target: Path, ssot: Path, *, check: bool) -> dict:
    result = {
        "target": str(target),
        "ssot": str(ssot),
        "status": "ok",
        "action": None,
    }
    if not ssot.is_dir():
        result["status"] = "error"
        result["action"] = f"missing SSOT: {ssot}"
        return result

    if same_link(target, ssot):
        result["action"] = "current"
        return result

    if check:
        if target.exists() or target.is_symlink():
            result["status"] = "drift"
            result["action"] = "would-replace-with-ssot-symlink"
        else:
            result["status"] = "drift"
            result["action"] = "would-create-ssot-symlink"
        return result

    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        remove_path(target)
        result["action"] = "replaced-with-ssot-symlink"
    else:
        result["action"] = "created-ssot-symlink"
    target.symlink_to(ssot.resolve(), target_is_directory=True)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.home() / ".cursor-governance")
    parser.add_argument("--workspace", type=Path, default=None)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    ssot = root / "rules"
    targets = [Path.home() / ".claude" / "rules"]
    if args.workspace is not None:
        targets.append(args.workspace.resolve() / ".claude" / "rules")
    elif (Path.cwd() / ".claude").is_dir():
        targets.append(Path.cwd() / ".claude" / "rules")

    # de-dupe
    seen: set[str] = set()
    uniq: list[Path] = []
    for t in targets:
        key = str(t)
        if key not in seen:
            seen.add(key)
            uniq.append(t)

    results = [reconcile_one(t, ssot, check=args.check) for t in uniq]
    payload = {
        "ssot": str(ssot),
        "mode": "directory-symlink",
        "results": results,
    }
    if not args.quiet:
        print(json.dumps(payload, indent=2, sort_keys=True))

    bad = any(r["status"] in {"error", "drift"} for r in results)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Reconcile governance skills into every configured LLM adapter.

SSOT: governance `skills/` (same tree as `.cursor-commands/skills`).
Adapters get per-skill symlinks only. Manifest/registry updates drive refresh.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from reconcile_claude_l9_skills import (  # noqa: E402
    REGISTRY_REL,
    reconcile_scope,
)

ADAPTER_CONFIG_REL = Path("environment/skill-adapters/SKILL_ADAPTER_ROOTS.yaml")


def expand_path(raw: str, workspace: Path) -> Path:
    expanded = os.path.expanduser(raw)
    path = Path(expanded)
    if path.is_absolute():
        return path
    return (workspace / path).resolve()


def load_config(root: Path) -> dict[str, Any]:
    path = root / ADAPTER_CONFIG_REL
    if not path.is_file():
        raise FileNotFoundError(f"missing adapter config: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("SKILL_ADAPTER_ROOTS.yaml must be a mapping")
    return data


def reconcile_adapters(
    root: Path,
    *,
    workspace: Path | None,
    check: bool = False,
    quiet: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    workspace = (workspace or Path.cwd()).resolve()
    config = load_config(root)
    mode = str(config.get("mode") or "symlink")
    if mode != "symlink":
        raise ValueError("skill adapters must use mode: symlink (copies are forbidden)")
    replace_dupes = bool(config.get("replace_l9_duplicates", True))

    registry_path = root / REGISTRY_REL
    if not registry_path.is_file():
        raise FileNotFoundError(f"registry missing: {registry_path}")
    registry = json.loads(registry_path.read_text(encoding="utf-8"))

    results = []
    skipped = []
    for adapter in config.get("adapters") or []:
        if not isinstance(adapter, dict):
            continue
        adapter_id = str(adapter.get("id") or "unknown")
        kind = str(adapter.get("kind") or "")
        raw_path = adapter.get("path")
        if raw_path in (None, "", "null"):
            skipped.append({"id": adapter_id, "reason": "plugin-or-null-path"})
            continue
        if kind == "project" and workspace is None:
            skipped.append({"id": adapter_id, "reason": "workspace-required"})
            continue

        target = expand_path(str(raw_path), workspace)
        # Rules are whole-dir symlinked separately (reconcile_claude_rules.py).
        scope = "project" if kind == "project" else "user"
        result = reconcile_scope(
            root,
            registry,
            scope,
            workspace,
            mode,
            check,
            target_override=target,
            replace_l9_duplicates=replace_dupes,
            install_project_rule=False,
        )
        payload = result.as_dict()
        payload["adapter_id"] = adapter_id
        payload["surface"] = adapter.get("surface")
        results.append(payload)

    return {
        "ssot": str((root / str(config.get("ssot_relative") or "skills")).resolve()),
        "mode": mode,
        "results": results,
        "skipped": skipped,
    }


def run_orphan_migration(workspace: Path, *, check: bool, quiet: bool) -> dict[str, Any] | None:
    migrate = SCRIPT_DIR / "migrate_claude_orphan_skills.py"
    if not migrate.is_file():
        return None
    cmd = [
        sys.executable,
        str(migrate),
        "--workspace",
        str(workspace),
        "--json",
    ]
    if check:
        cmd.append("--check")
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        payload = {"raw": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
    if not quiet and result.stdout.strip():
        # Keep adapter JSON as primary stdout; attach migration under key later.
        pass
    payload["returncode"] = result.returncode
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.home() / ".cursor-governance")
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="Consumer workspace for project-scoped adapters (default: cwd)",
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument(
        "--skip-orphan-migration",
        action="store_true",
        help="Do not move misplaced .claude/* skill packs into .claude/skills/",
    )
    args = parser.parse_args()

    workspace = (args.workspace or Path.cwd()).resolve()
    migration = None
    if not args.skip_orphan_migration:
        migration = run_orphan_migration(workspace, check=args.check, quiet=args.quiet)

    try:
        payload = reconcile_adapters(
            args.root,
            workspace=workspace,
            check=args.check,
            quiet=args.quiet,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if migration is not None:
        payload["orphan_migration"] = migration

    # Claude rules: whole-dir symlink → governance rules/ (== .cursor-commands/rules)
    rules_script = SCRIPT_DIR / "reconcile_claude_rules.py"
    if rules_script.is_file():
        rules_cmd = [
            sys.executable,
            str(rules_script),
            "--root",
            str(args.root.resolve()),
            "--workspace",
            str(workspace),
            "--quiet",
        ]
        if args.check:
            rules_cmd.append("--check")
        rules_proc = subprocess.run(rules_cmd, capture_output=True, text=True)
        try:
            payload["claude_rules"] = json.loads(rules_proc.stdout or "{}")
        except json.JSONDecodeError:
            payload["claude_rules"] = {
                "returncode": rules_proc.returncode,
                "stdout": rules_proc.stdout,
                "stderr": rules_proc.stderr,
            }
        payload["claude_rules"]["returncode"] = rules_proc.returncode

    if not args.quiet:
        print(json.dumps(payload, indent=2, sort_keys=True))

    has_problem = any(
        result.get("conflicts") or result.get("drift") for result in payload["results"]
    )
    if migration and migration.get("returncode", 0) != 0:
        has_problem = True
    if payload.get("claude_rules", {}).get("returncode", 0) != 0:
        has_problem = True
    return 1 if has_problem else 0


if __name__ == "__main__":
    raise SystemExit(main())

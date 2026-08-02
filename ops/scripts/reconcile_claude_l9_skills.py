#!/usr/bin/env python3
"""Reconcile L9 skills into Claude Code's native discovery directories.

Managed entries are per-skill links or copies. Unmanaged consumer skills are
never overwritten or removed. The governance clone remains the source of truth.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REGISTRY_REL = Path("environment/claude-code/generated/skill-registry.json")
RULE_REL = Path("environment/claude-code/rules/l9-skill-routing.md")
STATE_NAME = ".l9-managed-skills.json"


@dataclass
class Result:
    scope: str
    target: str
    created: list[str]
    current: list[str]
    removed: list[str]
    conflicts: list[str]
    drift: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "scope": self.scope,
            "target": self.target,
            "created": self.created,
            "current": self.current,
            "removed": self.removed,
            "conflicts": self.conflicts,
            "drift": self.drift,
        }


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name, dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def read_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"schema_version": 1, "skills": [], "rules": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema_version": 1, "skills": [], "rules": []}
    return data if isinstance(data, dict) else {"schema_version": 1, "skills": [], "rules": []}


def same_link(path: Path, source: Path) -> bool:
    if not path.is_symlink():
        return False
    try:
        return path.resolve(strict=False) == source.resolve(strict=False)
    except OSError:
        return False


def same_copy(path: Path, source: Path) -> bool:
    marker = path / ".l9-source.json"
    if not path.is_dir() or not marker.is_file():
        return False
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return data.get("source") == str(source.resolve())


def install_entry(source: Path, destination: Path, mode: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if mode == "symlink":
        destination.symlink_to(source.resolve(), target_is_directory=source.is_dir())
        return
    if source.is_dir():
        shutil.copytree(source, destination)
        atomic_json(destination / ".l9-source.json", {"source": str(source.resolve())})
    else:
        shutil.copy2(source, destination)


def remove_managed(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path)


def scope_target(scope: str, workspace: Path) -> Path:
    if scope == "user":
        return Path.home() / ".claude" / "skills"
    return workspace / ".claude" / "skills"


def reconcile_scope(
    root: Path,
    registry: dict[str, Any],
    scope: str,
    workspace: Path,
    mode: str,
    check: bool,
) -> Result:
    target = scope_target(scope, workspace)
    state_path = target / STATE_NAME
    old_state = read_state(state_path)
    previous = set(str(name) for name in old_state.get("skills", []))
    desired = {str(record["name"]): root / str(record["path"]) for record in registry["skills"]}

    result = Result(scope, str(target), [], [], [], [], [])
    for name, source in sorted(desired.items()):
        destination = target / name
        if not source.is_dir() or not (source / "SKILL.md").is_file():
            result.conflicts.append(f"missing-source:{name}")
            continue
        matches = (
            same_link(destination, source) if mode == "symlink" else same_copy(destination, source)
        )
        if matches:
            result.current.append(name)
            continue
        if destination.exists() or destination.is_symlink():
            if name in previous:
                if check:
                    result.drift.append(f"stale-managed:{name}")
                else:
                    remove_managed(destination)
                    install_entry(source, destination, mode)
                    result.created.append(name)
            else:
                result.conflicts.append(f"unmanaged-conflict:{name}")
            continue
        if check:
            result.drift.append(f"missing:{name}")
        else:
            install_entry(source, destination, mode)
            result.created.append(name)

    for stale in sorted(previous - set(desired)):
        stale_path = target / stale
        if check:
            if stale_path.exists() or stale_path.is_symlink():
                result.drift.append(f"obsolete:{stale}")
        else:
            remove_managed(stale_path)
            result.removed.append(stale)

    managed_rules: list[str] = []
    if scope == "project":
        rule_source = root / RULE_REL
        rule_target = workspace / ".claude" / "rules" / rule_source.name
        if rule_source.is_file():
            if same_link(rule_target, rule_source):
                managed_rules.append(str(rule_target))
            elif rule_target.exists() or rule_target.is_symlink():
                previous_rules = set(str(item) for item in old_state.get("rules", []))
                if str(rule_target) in previous_rules:
                    if check:
                        result.drift.append("stale-managed-rule")
                    else:
                        remove_managed(rule_target)
                        install_entry(rule_source, rule_target, mode)
                        managed_rules.append(str(rule_target))
                else:
                    result.conflicts.append("unmanaged-conflict:l9-skill-routing.md")
            elif check:
                result.drift.append("missing-rule:l9-skill-routing.md")
            else:
                install_entry(rule_source, rule_target, mode)
                managed_rules.append(str(rule_target))

    if not check and not result.conflicts:
        atomic_json(
            state_path,
            {
                "schema_version": 1,
                "governance_root": str(root),
                "registry_manifest_sha256": registry.get("source_manifest_sha256", ""),
                "mode": mode,
                "skills": sorted(desired),
                "rules": managed_rules,
            },
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.home() / ".cursor-governance")
    parser.add_argument("--scope", action="append", choices=("user", "project"), required=True)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--mode", choices=("symlink", "copy"), default="symlink")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    registry_path = root / REGISTRY_REL
    if not registry_path.is_file():
        print(f"ERROR: registry missing: {registry_path}", file=sys.stderr)
        return 2
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    results = [
        reconcile_scope(root, registry, scope, args.workspace.resolve(), args.mode, args.check)
        for scope in dict.fromkeys(args.scope)
    ]
    payload = {"results": [result.as_dict() for result in results]}
    if not args.quiet:
        print(json.dumps(payload, indent=2, sort_keys=True))
    has_problem = any(result.conflicts or result.drift for result in results)
    return 1 if has_problem else 0


if __name__ == "__main__":
    raise SystemExit(main())

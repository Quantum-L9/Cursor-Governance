#!/usr/bin/env python3
"""Project enabled slash commands into Claude Code discovery directories.

Registry: `commands/COMMANDS_MANIFEST.yaml` — the only command registry.
Managed entries are per-command symlinks (`<target>/<name>.md`) into the
governance SSOT `commands/` tree. Unmanaged consumer commands are never
overwritten or removed. A command whose name collides with a projected skill
is rejected (fail-closed) and reported: skills and commands share the `/name`
namespace in Claude Code, so projecting both would be ambiguous.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from reconcile_claude_l9_skills import (  # noqa: E402
    REGISTRY_REL,
    atomic_json,
    link_outside_ssot,
    read_state,
    remove_managed,
    same_link,
)

MANIFEST_REL = Path("commands/COMMANDS_MANIFEST.yaml")
STATE_NAME = ".l9-managed-commands.json"


@dataclass
class CommandResult:
    scope: str
    target: str
    created: list[str] = field(default_factory=list)
    current: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    drift: list[str] = field(default_factory=list)
    collisions: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "scope": self.scope,
            "target": self.target,
            "created": self.created,
            "current": self.current,
            "removed": self.removed,
            "conflicts": self.conflicts,
            "drift": self.drift,
            "collisions": self.collisions,
        }


def load_manifest(root: Path) -> dict[str, Any]:
    path = root / MANIFEST_REL
    if not path.is_file():
        raise FileNotFoundError(f"missing command manifest: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("COMMANDS_MANIFEST.yaml must be a mapping")
    return data


def load_skill_names(root: Path) -> set[str]:
    registry_path = root / REGISTRY_REL
    if not registry_path.is_file():
        return set()
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    return {
        str(record.get("name"))
        for record in registry.get("skills", [])
        if isinstance(record, dict) and record.get("name")
    }


def desired_commands(
    manifest: dict[str, Any], root: Path, skill_names: set[str]
) -> tuple[dict[str, Path], list[str], list[str]]:
    """Return (name → source path, collisions, conflicts) for enabled entries.

    A name that matches a projected skill is a namespace collision: the skill
    stays authoritative (its SKILL.md already carries the protocol) and the
    command is not projected. Duplicate manifest names fail closed entirely.
    """
    desired: dict[str, Path] = {}
    collisions: list[str] = []
    conflicts: list[str] = []
    seen: set[str] = set()
    for entry in manifest.get("commands") or []:
        if not isinstance(entry, dict):
            conflicts.append(f"invalid-entry:{entry!r}")
            continue
        if not entry.get("enabled", True):
            continue
        slash = str(entry.get("slash") or "")
        rel = str(entry.get("file") or "")
        name = slash.lstrip("/")
        if not name or not rel:
            conflicts.append(f"invalid-entry:{slash or rel}")
            continue
        if name in seen:
            conflicts.append(f"duplicate-command:{name}")
            continue
        seen.add(name)
        if name in skill_names:
            collisions.append(f"command-skill-collision:{name}")
            continue
        desired[name] = root / rel
    return desired, collisions, conflicts


def reconcile_commands_scope(
    root: Path,
    manifest: dict[str, Any],
    scope: str,
    workspace: Path,
    check: bool,
    *,
    target_override: Path | None = None,
) -> CommandResult:
    if target_override is not None:
        target = target_override
    elif scope == "user":
        target = Path.home() / ".claude" / "commands"
    else:
        target = workspace / ".claude" / "commands"

    state_path = target / STATE_NAME
    old_state = read_state(state_path)
    previous = {str(name) for name in old_state.get("commands", [])}

    skill_names = load_skill_names(root)
    desired, collisions, entry_conflicts = desired_commands(manifest, root, skill_names)

    result = CommandResult(scope, str(target))
    result.collisions.extend(collisions)
    result.conflicts.extend(entry_conflicts)

    for name, source in sorted(desired.items()):
        destination = target / f"{name}.md"
        if not source.is_file():
            result.conflicts.append(f"missing-source:{name}")
            continue
        if same_link(destination, source):
            result.current.append(name)
            continue
        if destination.exists() or destination.is_symlink():
            # Repair only what is provably ours: a name in our recorded state,
            # or a symlink that already resolves inside the SSOT commands tree
            # (same content we would install — e.g. state lost to a cache
            # reset). Anything else is consumer-owned and preserved fail-closed.
            ssot_equivalent = destination.is_symlink() and not link_outside_ssot(
                destination, root / "commands"
            )
            if name in previous or ssot_equivalent:
                if check:
                    result.drift.append(f"stale-managed:{name}")
                else:
                    remove_managed(destination)
                    install_command_link(source, destination)
                    result.created.append(name)
            else:
                result.conflicts.append(f"unmanaged-conflict:{name}")
            continue
        if check:
            result.drift.append(f"missing:{name}")
        else:
            install_command_link(source, destination)
            result.created.append(name)

    for stale in sorted(previous - set(desired)):
        stale_path = target / f"{stale}.md"
        if not (stale_path.exists() or stale_path.is_symlink()):
            continue
        if check:
            result.drift.append(f"obsolete:{stale}")
        else:
            remove_managed(stale_path)
            result.removed.append(stale)

    if not check and not result.conflicts:
        atomic_json(
            state_path,
            {
                "schema_version": 1,
                "governance_root": str(root),
                "commands": sorted(desired),
                "collisions": sorted(collisions),
            },
        )
    return result


def install_command_link(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.symlink_to(source.resolve())


def reconcile(
    root: Path,
    *,
    workspace: Path,
    scopes: tuple[str, ...] = ("user", "project"),
    check: bool = False,
    target_override: Path | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    manifest = load_manifest(root)
    results = [
        reconcile_commands_scope(
            root,
            manifest,
            scope,
            workspace.resolve(),
            check,
            target_override=target_override,
        )
        for scope in dict.fromkeys(scopes)
    ]
    return {
        "manifest": str(root / MANIFEST_REL),
        "results": [result.as_dict() for result in results],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.home() / ".cursor-governance")
    parser.add_argument("--scope", action="append", choices=("user", "project"))
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--target", type=Path, default=None, help="Override discovery directory")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    try:
        payload = reconcile(
            args.root.resolve(),
            workspace=args.workspace,
            scopes=tuple(args.scope) if args.scope else ("user", "project"),
            check=args.check,
            target_override=args.target.resolve() if args.target else None,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if not args.quiet:
        print(json.dumps(payload, indent=2, sort_keys=True))
    has_problem = any(r["conflicts"] or r["drift"] for r in payload["results"])
    return 1 if has_problem else 0


if __name__ == "__main__":
    raise SystemExit(main())

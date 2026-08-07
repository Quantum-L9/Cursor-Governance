#!/usr/bin/env python3
"""Move skill packs misplaced under .claude/ into .claude/skills/.

Claude discovers user/project skills from `.claude/skills/<name>/SKILL.md`.
Packs that sit as siblings under `.claude/` (or other non-skills paths) are
orphans — this script relocates them into `.claude/skills/` and optionally
renames legacy `agents/openai.yaml` → `agents/meta.yaml`.

Never touches plugin/cache/marketplace trees.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

SKIP_DIR_NAMES = {
    "skills",
    "rules",
    "plugins",
    "cache",
    "backups",
    "debug",
    "downloads",
    "ide",
    "projects",
    "session-env",
    "sessions",
    "shell-snapshots",
    "telemetry",
    "stats-cache.json",
}


def is_skill_dir(path: Path) -> bool:
    return path.is_dir() and (path / "SKILL.md").is_file()


def normalize_agents_meta(skill_dir: Path) -> list[str]:
    actions: list[str] = []
    openai = skill_dir / "agents" / "openai.yaml"
    meta = skill_dir / "agents" / "meta.yaml"
    if openai.is_file():
        meta.parent.mkdir(parents=True, exist_ok=True)
        if meta.exists():
            openai.unlink()
            actions.append(f"removed duplicate {openai}")
        else:
            openai.rename(meta)
            actions.append(f"renamed {openai.name} -> meta.yaml")
    return actions


def find_orphans(claude_root: Path) -> list[Path]:
    if not claude_root.is_dir():
        return []
    orphans: list[Path] = []
    for child in sorted(claude_root.iterdir()):
        if child.name.startswith("."):
            continue
        if child.name in SKIP_DIR_NAMES:
            continue
        if child.is_symlink():
            continue
        if is_skill_dir(child):
            orphans.append(child)
    return orphans


def migrate_one(orphan: Path, skills_root: Path, *, check: bool) -> dict:
    name = orphan.name
    dest = skills_root / name
    record = {"name": name, "from": str(orphan), "to": str(dest), "actions": []}
    if dest.exists() or dest.is_symlink():
        record["status"] = "conflict"
        record["actions"].append("destination already exists")
        return record
    if check:
        record["status"] = "would-migrate"
        return record
    skills_root.mkdir(parents=True, exist_ok=True)
    shutil.move(str(orphan), str(dest))
    record["actions"].extend(normalize_agents_meta(dest))
    record["status"] = "migrated"
    return record


def migrate_claude_root(claude_root: Path, *, check: bool) -> dict:
    skills_root = claude_root / "skills"
    orphans = find_orphans(claude_root)
    results = [migrate_one(orphan, skills_root, check=check) for orphan in orphans]
    # Also normalize meta.yaml inside already-correct skills trees (local real dirs only).
    normalized = []
    if skills_root.is_dir():
        for child in sorted(skills_root.iterdir()):
            if child.is_symlink() or not is_skill_dir(child):
                continue
            actions = [] if check else normalize_agents_meta(child)
            if actions:
                normalized.append({"name": child.name, "actions": actions})
    return {
        "claude_root": str(claude_root),
        "orphan_count": len(orphans),
        "results": results,
        "normalized_in_skills": normalized,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--claude-root",
        action="append",
        type=Path,
        help="Path to a .claude directory (repeatable). Defaults to ~/.claude",
    )
    parser.add_argument("--workspace", type=Path, default=None, help="Also scan <workspace>/.claude")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    roots: list[Path] = []
    if args.claude_root:
        roots.extend(args.claude_root)
    else:
        roots.append(Path.home() / ".claude")
    if args.workspace is not None:
        roots.append(args.workspace.resolve() / ".claude")

    payloads = [migrate_claude_root(root.resolve(), check=args.check) for root in roots]
    summary = {"check": args.check, "roots": payloads}
    if args.json or True:
        print(json.dumps(summary, indent=2, sort_keys=True))

    conflicts = any(
        item.get("status") == "conflict" for payload in payloads for item in payload["results"]
    )
    return 1 if conflicts else 0


if __name__ == "__main__":
    raise SystemExit(main())

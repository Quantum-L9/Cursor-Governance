#!/usr/bin/env python3
"""Validate commands/COMMANDS_MANIFEST.yaml against commands/*.md on disk."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

# Reuse generator model for drift compare.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_commands_manifest import build_manifest, is_excluded  # noqa: E402


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    path = root / "commands" / "COMMANDS_MANIFEST.yaml"
    if not path.is_file():
        return [f"missing {path.relative_to(root)}"]
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return ["COMMANDS_MANIFEST.yaml must be a mapping"]

    expected = build_manifest(root)
    got_files = {entry.get("file") for entry in data.get("commands", []) if isinstance(entry, dict)}
    want_files = {entry.get("file") for entry in expected["commands"]}
    missing = sorted(want_files - got_files)
    extra = sorted(got_files - want_files)
    if missing:
        errors.append(f"manifest missing command files: {missing}")
    if extra:
        errors.append(f"manifest references missing/extra command files: {extra}")

    excluded = list(data.get("excluded") or [])
    for entry in data.get("commands", []) or []:
        if not isinstance(entry, dict):
            errors.append(f"invalid command entry: {entry!r}")
            continue
        rel = str(entry.get("file") or "")
        slash = str(entry.get("slash") or "")
        if not rel.startswith("commands/") or not rel.endswith(".md"):
            errors.append(f"bad file path: {rel}")
        if not (root / rel).is_file():
            errors.append(f"command file missing on disk: {rel}")
        if is_excluded(rel, excluded):
            errors.append(f"command listed but excluded: {rel}")
        if not slash.startswith("/"):
            errors.append(f"slash must start with /: {slash!r} ({rel})")

    slashes = [str(e.get("slash")) for e in data.get("commands", []) if isinstance(e, dict)]
    dupes = sorted({s for s in slashes if slashes.count(s) > 1})
    if dupes:
        errors.append(f"duplicate slash commands: {dupes}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    root = args.root.resolve()
    errors = validate(root)
    if errors:
        for err in errors:
            print(f"FAIL: {err}")
        print(f"RESULT: FAIL - {len(errors)} issue(s)")
        return 1
    print("RESULT: PASS - COMMANDS_MANIFEST matches commands/*.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

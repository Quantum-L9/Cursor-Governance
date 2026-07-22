#!/usr/bin/env python3
"""Check or project selected shared rules as individual symlinks into a repo overlay."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml


def die(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def load_selection(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("selection file must be a mapping")
    required = {"schema", "enabled", "shared", "local", "delivery"}
    missing = sorted(required - set(data))
    if missing:
        raise ValueError(f"selection file missing fields: {', '.join(missing)}")
    if data["schema"] != "l9.cursor-rules-selection/v1":
        raise ValueError(f"unsupported selection schema: {data['schema']}")
    if data["local"].get("preserve_unknown_files") is not True:
        raise ValueError("preserve_unknown_files must be true")
    if data["delivery"].get("mode") != "individual_symlink":
        raise ValueError("only individual_symlink delivery is supported")
    if data["delivery"].get("collision_policy") != "fail_closed":
        raise ValueError("collision_policy must be fail_closed")
    return data


def manifest_index(governance_root: Path) -> dict[str, Path]:
    manifest_path = governance_root / "rules/RULES-MANIFEST.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    index: dict[str, Path] = {}
    for entry in data.get("rules", []):
        source = governance_root / "rules" / entry["file"]
        keys = {entry["id"], source.stem, entry["file"]}
        for key in keys:
            if key in index and index[key] != source:
                raise ValueError(f"ambiguous shared rule selector: {key}")
            index[key] = source
    return index


def check_activation_gate(workspace: Path, config: dict[str, Any]) -> None:
    gate = config.get("activation_gate") or {}
    report = gate.get("required_report")
    status = gate.get("required_status")
    if not report or not status:
        return
    path = workspace / report
    if not path.is_file():
        raise ValueError(f"activation evidence report is missing: {report}")
    text = path.read_text(encoding="utf-8")
    markers = (f"Status: {status}", f"status: {status}", f"**Status:** {status}")
    if not any(marker in text for marker in markers):
        raise ValueError(f"activation evidence report has not reached {status}: {report}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace", type=Path, nargs="?", default=Path.cwd())
    parser.add_argument("--governance-root", type=Path)
    parser.add_argument("--selection", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    selection = args.selection or workspace / ".cursor/governance/rules.yaml"
    if not selection.is_file():
        return die(f"selection file not found: {selection}")
    try:
        config = load_selection(selection)
    except (OSError, ValueError) as exc:
        return die(str(exc))
    if config.get("enabled") is not True:
        print("DISABLED: selective shared-rule delivery remains phase-gated")
        return 0

    governance_root = args.governance_root
    if governance_root is None:
        entry = workspace / ".cursor-commands"
        if not entry.is_symlink():
            return die(".cursor-commands must be a symlink before shared rules can be selected")
        governance_root = entry.resolve()
    governance_root = governance_root.resolve()

    overlay = workspace / ".cursor/rules"
    if overlay.is_symlink() or not overlay.is_dir():
        return die(".cursor/rules must be a real repository-owned directory")

    try:
        check_activation_gate(workspace, config)
        index = manifest_index(governance_root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return die(str(exc))

    selected: list[str] = []
    shared = config["shared"]
    for bucket in ("required", "optional"):
        for selector in shared.get(bucket, []):
            if selector not in selected:
                selected.append(selector)

    operations: list[tuple[Path, Path]] = []
    for selector in selected:
        source = index.get(selector)
        if source is None or not source.is_file():
            return die(f"selected shared rule not found: {selector}")
        destination = overlay / source.name
        if destination.is_symlink():
            if destination.resolve() == source.resolve():
                continue
            return die(f"collision: {destination} points to an unexpected target")
        if destination.exists():
            return die(f"collision: local file already owns {destination.name}")
        operations.append((source, destination))

    if not args.apply:
        for source, destination in operations:
            print(f"WOULD LINK: {destination} -> {source}")
        print(f"RESULT: PASS ({len(operations)} changes pending)")
        return 0

    for source, destination in operations:
        destination.symlink_to(source)
        if not destination.is_symlink() or destination.resolve() != source.resolve():
            return die(f"failed to create verified symlink: {destination}")
        print(f"LINKED: {destination.name} -> {source}")
    print(f"RESULT: PASS ({len(operations)} links created; unknown local files preserved)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

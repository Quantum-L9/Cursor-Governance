#!/usr/bin/env python3
"""Normalize rules/*.mdc frontmatter to Cursor-native fields only.

Dry-run by default. Pass --apply to write. Pass --archive PATH to dump
original frontmatter first (required before --apply).

Uses ops/scripts/lib/rule_frontmatter.py so YAML parsing matches the
manifest generator and llm-rules projection.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import yaml  # noqa: E402
from lib.rule_frontmatter import (  # noqa: E402
    always_apply_is_true,
    emit_native_frontmatter,
    parse_rule,
)

NATIVE = ("description", "globs", "alwaysApply")


def _iter_rules(rules_dir: Path) -> list[Path]:
    return [
        path
        for path in sorted(rules_dir.glob("*.mdc"))
        if not path.name.startswith("RULES-MANIFEST")
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rules-dir", default="rules")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--archive")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()

    root = args.root.resolve()
    rules_dir = Path(args.rules_dir)
    if not rules_dir.is_absolute():
        rules_dir = (root / rules_dir).resolve()
    else:
        rules_dir = rules_dir.resolve()
    if not rules_dir.is_dir():
        print(f"not found: {rules_dir}", file=sys.stderr)
        return 1

    if args.apply and not args.archive:
        print("refusing --apply without --archive (undo record required)", file=sys.stderr)
        return 2

    dropped: dict[str, int] = {}
    changed: list[tuple[str, int]] = []
    failed: list[str] = []
    archive: list[tuple[str, dict[str, Any]]] = []
    before = after = 0

    pending: list[tuple[Path, str, str, bool, int]] = []

    for path in _iter_rules(rules_dir):
        try:
            parsed = parse_rule(path)
        except (ValueError, yaml.YAMLError) as exc:
            failed.append(f"{path.name}: {exc}")
            continue
        if not parsed.has_frontmatter:
            failed.append(path.name)
            continue

        fields = dict(parsed.metadata)
        archive.append((path.name, fields))
        aa = always_apply_is_true(fields)
        original = path.read_text(encoding="utf-8")
        size = len(original.encode())
        if aa:
            before += size

        for key in fields:
            if key not in NATIVE:
                dropped[key] = dropped.get(key, 0) + 1
        if aa and fields.get("globs") not in (None, "", [], {}):
            dropped["globs (ignored under alwaysApply)"] = (
                dropped.get("globs (ignored under alwaysApply)", 0) + 1
            )

        body = parsed.body.lstrip("\n")
        new = emit_native_frontmatter(fields) + "\n" + body
        if not new.endswith("\n"):
            new += "\n"
        pending.append((path, original, new, aa, size))

    if failed:
        print("FAILED TO PARSE: " + ", ".join(failed), file=sys.stderr)
        return 1

    if args.archive:
        archive_path = Path(args.archive)
        if not archive_path.is_absolute():
            archive_path = root / archive_path
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "note": "Original frontmatter, pre-normalization. Undo record.",
            "files": {name: fields for name, fields in archive},
        }
        archive_path.write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, width=1000),
            encoding="utf-8",
        )
        print(f"archived {len(archive)} files -> {archive_path}")

    for path, original, new, aa, size in pending:
        if new != original:
            changed.append((path.name, len(original) - len(new)))
            if args.apply:
                path.write_text(new, encoding="utf-8")
            if aa:
                after += len(new.encode())
        elif aa:
            after += size

    print(f"mode: {'APPLY' if args.apply else 'DRY-RUN'}")
    print(f"files scanned: {len(archive)}, changed: {len(changed)}, unparseable: {len(failed)}")
    if dropped:
        print("\nnon-native fields removed:")
        for key, count in sorted(dropped.items(), key=lambda item: -item[1]):
            print(f"  {key:<40} {count} file(s)")
    if failed:
        print("\nFAILED TO PARSE: " + ", ".join(failed))
    print(
        f"\nalways-apply bytes: {before} -> {after} "
        f"(delta {after - before:+d}, ~{(after - before) // 4:+d} tokens/turn)"
    )
    if not args.apply:
        print("\nre-run with --apply to write changes")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

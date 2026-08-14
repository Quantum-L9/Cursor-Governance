#!/usr/bin/env python3
"""CI gate for docs/rules-standard.md Section 6.

Ratchet: ALWAYS_BUDGET is the measured always-apply total on first land.
Lower it as Stage 3 retiering lands. Never raise it. Target: 12288 bytes.

Stage 2 hard-fails native-field / glob-shape / .md / budget checks.
Prefix uniqueness, per-file 4096, and 500-line cap are warnings until Stage 3.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from lib.rule_frontmatter import always_apply_is_true, parse_rule  # noqa: E402

NATIVE_FIELDS = {"description", "globs", "alwaysApply"}
# L9 rule-metadata.schema.json extension fields (ignored by Cursor; validated by
# ops/schemas/rule-metadata.schema.json via validate_rules_manifest.py).
L9_METADATA_FIELDS = {
    "id",
    "version",
    "scope",
    "activation",
    "domain",
    "authority",
    "context_cost",
    "deprecated",
    "replacement",
    "removal_plan",
    "extends",
}
ALLOWED_FIELDS = NATIVE_FIELDS | L9_METADATA_FIELDS
# Measured post-Stage-1 always-apply total on origin/main @ cb00181. Target: 12288.
ALWAYS_BUDGET = int(os.environ.get("RULES_ALWAYS_BUDGET", "181203"))
SINGLE_MAX = 4096
LINE_MAX = 500


def check_rules(root: Path) -> tuple[list[str], list[str], int, int]:
    """Return (errors, warnings, always_total_bytes, files_checked)."""
    rules_dir = root / "rules"
    errs: list[str] = []
    warns: list[str] = []
    if not rules_dir.is_dir():
        return [f"rules/ not found under {root}"], [], 0, 0

    md = [
        path.name for path in rules_dir.glob("*.md") if not path.name.startswith("RULES-MANIFEST")
    ]
    if md:
        errs.append("`.md` files in rules/ are ignored by Cursor: " + ", ".join(md))

    prefixes: dict[str, list[str]] = {}
    always_total = 0
    files = 0
    for path in sorted(rules_dir.glob("*.mdc")):
        if path.name.startswith("RULES-MANIFEST"):
            continue
        files += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        size = len(text.encode())
        nlines = text.count("\n") + 1

        if " " in path.name:
            errs.append(f"{path.name}: filename contains a space")
        match = re.match(r"^(\d{2})-", path.name)
        if not match:
            errs.append(f"{path.name}: missing NN- numeric prefix")
        else:
            prefixes.setdefault(match.group(1), []).append(path.name)

        if nlines > LINE_MAX:
            warns.append(f"{path.name}: {nlines} lines exceeds {LINE_MAX} (warn until Stage 3)")

        try:
            parsed = parse_rule(path)
        except (ValueError, OSError) as exc:
            errs.append(f"{path.name}: frontmatter parse failed: {exc}")
            continue
        if not parsed.has_frontmatter:
            errs.append(f"{path.name}: no frontmatter")
            continue

        extra = set(parsed.metadata) - ALLOWED_FIELDS
        if extra:
            errs.append(f"{path.name}: non-native frontmatter fields: " + ", ".join(sorted(extra)))

        aa = always_apply_is_true(parsed.metadata)
        has_globs = "globs" in parsed.metadata
        has_desc = bool(str(parsed.metadata.get("description") or "").strip())
        raw_globs = parsed.metadata.get("globs")

        if aa:
            always_total += size
            if size > SINGLE_MAX:
                warns.append(
                    f"{path.name}: always-apply rule is {size} bytes, over {SINGLE_MAX} "
                    "(warn until Stage 3)"
                )
            if has_globs:
                errs.append(
                    f"{path.name}: globs present with alwaysApply: true (ignored by Cursor)"
                )
        elif not has_globs and not has_desc:
            warns.append(f"{path.name}: manual-only (no globs, no description)")

        if isinstance(raw_globs, list):
            errs.append(f"{path.name}: globs uses YAML list form; use comma-separated string")

    for prefix, names in sorted(prefixes.items()):
        if len(names) > 1:
            joined = ", ".join(sorted(names))
            errs.append(
                f"prefix {prefix}- shared by {len(names)} files: {joined}"
            )

    if always_total > ALWAYS_BUDGET:
        errs.append(
            f"always-apply total {always_total} bytes (~{always_total // 4} tokens/turn) "
            f"exceeds budget {ALWAYS_BUDGET}"
        )

    return errs, warns, always_total, files


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    errs, warns, always_total, files = check_rules(args.root.resolve())
    print(f"rules checked: {files}")
    print(
        f"always-apply: {always_total} bytes (~{always_total // 4} tokens/turn), "
        f"budget {ALWAYS_BUDGET} (target 12288)"
    )
    for warn in warns:
        print(f"  warn: {warn}")
    if errs:
        print(f"\nFAIL ({len(errs)})")
        for err in errs:
            print(f"  - {err}")
        return 1
    print("\nPASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

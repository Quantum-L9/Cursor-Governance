#!/usr/bin/env python3
"""Fail-closed ADR identity integrity for docs/decisions.

Enforces a globally unique numeric ADR namespace, filename/H1 agreement,
contiguous allocation through max(existing), and unambiguous machine
authority references. Historical campaign sources are not rewrite targets
and are not scanned.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - environment guard
    sys.exit("PyYAML is required to validate ADR identity")

FILENAME_RE = re.compile(r"^ADR-(\d{4})-.+\.md$")
H1_RE = re.compile(r"^#\s+ADR-(\d{4})\b")
BARE_ADR_RE = re.compile(r"^ADR-\d{4}$")
CANONICAL_PATH_RE = re.compile(r"^docs/decisions/ADR-\d{4}-.+\.md$")

ACTIVE_MACHINE_CONTRACTS = ("environment/program-execution/core/shared/REPLAN_CONTRACT.yaml",)


def _decisions_dir(root: Path) -> Path:
    return root / "docs" / "decisions"


def inventory(root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    rows: list[dict[str, Any]] = []
    decisions = _decisions_dir(root)
    if not decisions.is_dir():
        return rows, [f"missing decisions directory: {decisions}"]
    for path in sorted(decisions.glob("ADR-*.md")):
        match = FILENAME_RE.match(path.name)
        if not match:
            errors.append(f"{path.relative_to(root)}: filename is not ADR-NNNN-slug.md")
            continue
        number = match.group(1)
        text = path.read_text(encoding="utf-8")
        h1_num = None
        for line in text.splitlines():
            h1 = H1_RE.match(line)
            if h1:
                h1_num = h1.group(1)
                break
        if h1_num is None:
            errors.append(f"{path.relative_to(root)}: missing H1 ADR-NNNN identifier")
        elif h1_num != number:
            errors.append(
                f"{path.relative_to(root)}: filename ADR-{number} does not match H1 ADR-{h1_num}"
            )
        rows.append(
            {
                "path": path.relative_to(root).as_posix(),
                "number": number,
                "h1": h1_num,
            }
        )
    return rows, errors


def check_uniqueness(rows: list[dict[str, Any]]) -> list[str]:
    by_num: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        by_num[row["number"]].append(row["path"])
    errors: list[str] = []
    for number, paths in sorted(by_num.items()):
        if len(paths) > 1:
            listed = ", ".join(paths)
            errors.append(f"duplicate ADR-{number}: {listed}")
    return errors


def check_sequential(rows: list[dict[str, Any]]) -> list[str]:
    numbers = sorted({int(row["number"]) for row in rows})
    if not numbers:
        return ["no ADR files found"]
    expected = list(range(1, numbers[-1] + 1))
    missing = [f"{item:04d}" for item in expected if item not in {int(n) for n in numbers}]
    if missing:
        return [f"ADR allocation is not sequential; missing ADR-{', ADR-'.join(missing)}"]
    return []


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def check_machine_references(root: Path, rows: list[dict[str, Any]]) -> list[str]:
    known = {row["path"] for row in rows}
    errors: list[str] = []
    for rel in ACTIVE_MACHINE_CONTRACTS:
        path = root / rel
        if not path.is_file():
            errors.append(f"{rel}: active machine contract is missing")
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        refs = _as_list(data.get("governing_adrs"))
        if not refs:
            errors.append(f"{rel}: governing_adrs is empty")
            continue
        for ref in refs:
            if not isinstance(ref, str):
                errors.append(f"{rel}: governing_adrs entry is not a string: {ref!r}")
                continue
            if BARE_ADR_RE.match(ref):
                errors.append(f"{rel}: bare numeric ADR reference is ambiguous: {ref}")
                continue
            if not CANONICAL_PATH_RE.match(ref):
                errors.append(f"{rel}: machine ADR reference is not a canonical path: {ref}")
                continue
            if ref not in known:
                errors.append(f"{rel}: unresolved machine ADR reference: {ref}")
    return errors


def validate(root: Path) -> list[str]:
    rows, errors = inventory(root)
    errors.extend(check_uniqueness(rows))
    if not any(item.startswith("duplicate ADR-") for item in errors):
        errors.extend(check_sequential(rows))
    errors.extend(check_machine_references(root, rows))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="repository root (default: Cursor-Governance clone)",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    errors = validate(root)
    if errors:
        print("FAIL: ADR identity integrity")
        for item in errors:
            print(f"  - {item}")
        return 1
    print(f"PASS: ADR identity integrity ({root / 'docs/decisions'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

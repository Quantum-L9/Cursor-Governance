#!/usr/bin/env python3
"""Reject null-filled / empty extract files (D5 regression from cieTrade_export_20260807_183800)."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def nonzero_bytes(path: Path, sample_cap: int = 64 * 1024) -> int:
    """Count non-zero bytes; for large files sample head/mid/tail."""
    size = path.stat().st_size
    if size == 0:
        return 0
    with path.open("rb") as f:
        if size <= sample_cap * 3:
            data = f.read()
            return sum(1 for b in data if b != 0)
        head = f.read(sample_cap)
        mid_off = max(0, size // 2 - sample_cap // 2)
        f.seek(mid_off)
        mid = f.read(sample_cap)
        f.seek(max(0, size - sample_cap))
        tail = f.read(sample_cap)
    return sum(1 for b in head + mid + tail if b != 0)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def check_tree(root: Path, patterns: list[str]) -> list[dict]:
    files: list[Path] = []
    for pat in patterns:
        files.extend(sorted(root.glob(pat)))
    # de-dupe
    seen: set[Path] = set()
    rows: list[dict] = []
    for path in files:
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        size = path.stat().st_size
        nz = nonzero_bytes(path)
        accepted = size > 0 and nz > 0
        rows.append(
            {
                "path": str(path),
                "size": size,
                "nonzero_bytes": nz,
                "sha256": sha256_file(path) if accepted else "",
                "status": "ACCEPT" if accepted else "REJECT",
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract integrity gate")
    parser.add_argument("root", type=Path, help="Extract directory")
    parser.add_argument(
        "--glob",
        action="append",
        dest="globs",
        default=None,
        help="Glob relative to root (repeatable). Default: **/*.csv **/*.tsv **/*.json",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 2
    globs = args.globs or ["**/*.csv", "**/*.tsv", "**/*.json"]
    rows = check_tree(root, globs)
    if args.json:
        print(json.dumps({"root": str(root), "files": rows}, indent=2))
    else:
        for row in rows:
            print(f"{row['status']}\t{row['size']}\tnz={row['nonzero_bytes']}\t{row['path']}")
        accepted = sum(1 for r in rows if r["status"] == "ACCEPT")
        rejected = sum(1 for r in rows if r["status"] == "REJECT")
        print(f"summary accept={accepted} reject={rejected} total={len(rows)}")
    if not rows:
        return 2
    return 0 if all(r["status"] == "ACCEPT" for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())

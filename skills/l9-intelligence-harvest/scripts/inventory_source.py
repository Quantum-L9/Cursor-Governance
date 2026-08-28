#!/usr/bin/env python3
import hashlib
import sys
from pathlib import Path

from _common import dump

SKIP = {".git", "__pycache__", ".DS_Store"}


def inventory(path):
    root = Path(path)
    rows = []
    if not root.exists():
        return None, []
    items = (
        [root]
        if root.is_file()
        else [p for p in root.rglob("*") if p.is_file() and not any(x in SKIP for x in p.parts)]
    )
    for p in sorted(items):
        rel = p.name if root.is_file() else str(p.relative_to(root))
        raw = p.read_bytes()
        rows.append(
            {
                "path": rel,
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "classification": "candidate",
            }
        )
    ident = {
        "kind": "file" if root.is_file() else "directory",
        "path": str(root.resolve()),
        "file_count": len(rows),
    }
    return ident, rows


def main():
    ident, rows = inventory(sys.argv[1])
    if ident is None:
        dump({"status": "BLOCKED", "reason": "donor_inaccessible"})
        return 3
    dump({"status": "PASS", "source_identity": ident, "inventory": rows})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

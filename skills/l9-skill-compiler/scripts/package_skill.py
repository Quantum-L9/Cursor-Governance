#!/usr/bin/env python3
# PACKAGE: deterministic integrity enumeration. Never mutates a registry.
import hashlib
import os
import sys
from datetime import UTC, datetime

from _common import PACK, emit

EXPECTED = ["SKILL.md", "contracts", "policies", "scripts", "references", "tests"]


def enumerate_pack(pack=None):
    pack = pack or str(PACK)
    rows = []
    for root, dirs, files in os.walk(pack):
        dirs[:] = [directory for directory in dirs if directory != "__pycache__"]
        for filename in sorted(files):
            path = os.path.join(root, filename)
            with open(path, "rb") as handle:
                digest = hashlib.sha256(handle.read()).hexdigest()[:16]
            rows.append(
                {
                    "path": os.path.relpath(path, pack),
                    "bytes": os.path.getsize(path),
                    "sha256_16": digest,
                }
            )
    return sorted(rows, key=lambda row: row["path"])


def integrity(pack=None):
    pack = pack or str(PACK)
    missing = [entry for entry in EXPECTED if not os.path.exists(os.path.join(pack, entry))]
    empty = [row["path"] for row in enumerate_pack(pack) if row["bytes"] == 0]
    return missing, empty


def main(argv):
    pack = argv[1] if len(argv) > 1 else None
    missing, empty = integrity(pack)
    rows = enumerate_pack(pack)
    status = "FAIL" if missing or empty else "PASS"
    generated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    return emit(
        {
            "stage": "PACKAGE",
            "status": status,
            "missing": missing,
            "empty_files": empty,
            "file_count": len(rows),
            "generated_at": generated_at,
            "artifacts": rows,
        },
        2 if status == "FAIL" else 0,
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv))

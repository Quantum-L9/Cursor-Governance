#!/usr/bin/env python3
"""Require a wheel file's SHA-256 to equal the admitted digest.

The official bytes are the input. This script does not build or download a wheel.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify an official wheel digest")
    parser.add_argument("wheel", type=Path)
    parser.add_argument(
        "--expect",
        required=True,
        help="admitted sha256 hex, optional sha256: prefix",
    )
    args = parser.parse_args(argv)
    if not args.wheel.is_file():
        print(f"FAIL: wheel not found: {args.wheel}", file=sys.stderr)
        return 2
    expected = args.expect.removeprefix("sha256:").strip().lower()
    if len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected):
        print("FAIL: --expect must be 64 hex characters", file=sys.stderr)
        return 2
    actual = digest(args.wheel)
    if actual != expected:
        print(f"FAIL: {actual} != {expected}", file=sys.stderr)
        return 1
    print(f"PASS: {actual}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

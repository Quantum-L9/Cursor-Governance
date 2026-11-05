#!/usr/bin/env python3
"""Refuse executable Manus Memory drafts until a native owner client is admitted.

Historical APIs and CLI flags are refusal-only compatibility surfaces. They
never inspect an authority file, resolve a checkout, or touch an output.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

AUTHORITY_ENV = "L9_MANUS_MEMORY_AUTHORITY_JSON"
BLOCKED_REASON = (
    "UPSTREAM_BLOCKED: native authenticated Streamable HTTP package/client unavailable; "
    "Manus native client UNBOUND; live admission UNKNOWN. "
    "The stdio/HMAC authority path is retired; no connector draft was written."
)


def _governance_root(value: str) -> Path:
    del value
    raise ValueError(BLOCKED_REASON)


def _scoped_authority(path: Path) -> dict[str, object]:
    """Retired: refuse before reading any caller-selected file."""
    del path
    raise ValueError("retired --authority-file: " + BLOCKED_REASON)


def draft(governance_root: Path, authority: dict[str, object] | None = None) -> dict[str, object]:
    del governance_root, authority
    raise ValueError(BLOCKED_REASON)


def _write_draft(path: Path, payload: dict[str, object], *, contains_authority: bool) -> None:
    del path, payload, contains_authority
    raise ValueError(BLOCKED_REASON)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--governance", required=True, help="Retained refusal-only flag")
    parser.add_argument("--authority-file", type=Path, help="Retired; file is never read")
    parser.add_argument("--output", type=Path, required=True, help="Never created or overwritten")
    args = parser.parse_args(argv)
    if args.authority_file is not None:
        print("retired --authority-file: " + BLOCKED_REASON, file=sys.stderr)
    else:
        print(BLOCKED_REASON, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

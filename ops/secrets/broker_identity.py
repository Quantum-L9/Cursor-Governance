#!/usr/bin/env python3
"""Retired. Implementation: ops/secrets/_archived/capability-broker/"""

from __future__ import annotations

import sys

_MSG = (
    "capability broker experiment retired (never shipped). "
    "See ops/secrets/_archived/capability-broker/RETIRED.md"
)


def main() -> int:
    print(_MSG, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Retired. This module does not move plans.

See RETIRED.md in this directory. Do not restore the mover.
"""

from __future__ import annotations

import sys

RETIRED = (
    "shelf_plans.py is retired (2026-11-03). It does not move plans. Do not restore it."
)


def shelf(*_args: object, **_kwargs: object) -> None:
    raise SystemExit(RETIRED)


def main(_argv: list[str] | None = None) -> int:
    print(RETIRED, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

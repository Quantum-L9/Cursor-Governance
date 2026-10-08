#!/usr/bin/env python3
"""Fail-closed compatibility shim: Program Execution owns no merge authority."""

from __future__ import annotations

import sys


def main() -> int:
    print(
        "DENIED: Program Execution owns no merge authority. "
        "Publish separately with `PR_REMEDIATE=0 make pr`; merge only through "
        "/l9-pr-remediation.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

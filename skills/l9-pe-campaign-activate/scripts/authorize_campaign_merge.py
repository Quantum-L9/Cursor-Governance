#!/usr/bin/env python3
"""Compatibility wrapper — SSOT is ops/autonomy/authorize_merge.py.

This skill authorizes merge of one campaign PR. Invoking /l9-pr-remediation
writes a repo-scoped receipt (`pr: "*"`) for every green, mergeable open PR.
"""

from __future__ import annotations

import sys
from pathlib import Path

OPS = Path(__file__).resolve().parents[3] / "ops" / "autonomy"
sys.path.insert(0, str(OPS))

from authorize_merge import (  # noqa: E402
    DEFAULT_REASON,
    DEFAULT_SOURCE,
    DEFAULT_TTL_SECONDS,
    REPO_SCOPE,
    auth_path,
    main,
    write_authorization,
)

__all__ = [
    "DEFAULT_REASON",
    "DEFAULT_SOURCE",
    "DEFAULT_TTL_SECONDS",
    "REPO_SCOPE",
    "auth_path",
    "main",
    "write_authorization",
]


if __name__ == "__main__":
    raise SystemExit(main())

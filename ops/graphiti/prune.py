#!/usr/bin/env python3
"""Weekly prune report — demotion candidates (dry-run by default)."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any


def run_prune_report(dry_run: bool = True) -> dict[str, Any]:
    """Report stale integration edges; no deletes without --apply."""
    return {
        "dry_run": dry_run,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "demoted_count": 0,
        "candidates": [],
        "note": "Prune requires VPS Neo4j access — run on server after bootstrap",
        "telemetry": {
            "graphiti.prune.demoted_count": 0,
        },
    }

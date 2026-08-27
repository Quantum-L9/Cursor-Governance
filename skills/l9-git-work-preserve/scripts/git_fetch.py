#!/usr/bin/env python3
"""Best-effort origin fetch shared by the inventory and diagnosis scripts."""

from __future__ import annotations

import subprocess
from pathlib import Path


def _run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def fetch_origin(repo: Path, baseline: str = "origin/main") -> dict:
    """Refresh remote-tracking refs so novelty is judged against current origin.

    A stale baseline is half of what makes this pack misjudge branches, so both
    callers ask for a fetch. It is best effort by design: a repo with no origin
    (the self-test fixture) and an origin that cannot be reached both degrade to
    ``fetched: False`` instead of raising, and the caller proceeds against
    whichever local ref it already had. A False is never fatal on its own -- the
    receipt records it, and the baseline-resolution guard decides what it means.
    """
    result: dict = {"fetched": False, "error": None, "baseline_tip": ""}

    if _run(repo, "remote", "get-url", "origin").returncode != 0:
        return result

    proc = _run(repo, "fetch", "origin")
    if proc.returncode != 0:
        result["error"] = proc.stderr.strip() or "git fetch origin failed"
        return result

    result["fetched"] = True
    tip = _run(repo, "rev-parse", "--verify", "--quiet", baseline)
    if tip.returncode == 0:
        result["baseline_tip"] = tip.stdout.strip()
    return result

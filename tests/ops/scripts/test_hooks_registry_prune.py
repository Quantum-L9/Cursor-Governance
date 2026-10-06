"""Carry the hook-registry reconcile shell suite into the pytest catalog.

The suite needs a throwaway $HOME and real symlinks, so it stays shell; this
wrapper is what makes it run in CI and in the changed-file selector.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SUITE = ROOT / "ops" / "scripts" / "tests" / "test_hooks_registry_prune.sh"


def test_hook_registry_prune_suite() -> None:
    proc = subprocess.run(
        ["bash", str(SUITE)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr

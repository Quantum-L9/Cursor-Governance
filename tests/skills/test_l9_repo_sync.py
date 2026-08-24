"""Root pytest wrapper for the l9-repo-sync pack self-test."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SELF_TEST = (
    Path(__file__).resolve().parents[2] / "skills" / "l9-repo-sync" / "scripts" / "self_test.py"
)


def test_l9_repo_sync_self_test() -> None:
    proc = subprocess.run(
        [sys.executable, str(SELF_TEST)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "PASS: self_test" in proc.stdout

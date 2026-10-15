"""repo_write_lock must not silence the caller's stderr.

Regression: ``exec 9>"$dir/owner.flock" 2>/dev/null`` made the ``2>/dev/null``
permanent for the calling shell, so the SessionStart installer launched under
the lock lost every diagnostic (the bootstrap log carried no ``agent bootstrap:``
or ``UV:`` lines at all). The redirect must be scoped to opening fd 9.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
LIB = ROOT / "ops" / "scripts" / "lib" / "repo_write_lock.sh"

SCRIPT = r"""
source "$1"
repo_write_lock_acquire "$2" 2 || echo "NOT-ACQUIRED" >&2
echo "STDERR-AFTER-ACQUIRE" >&2
repo_write_lock_release
echo "STDERR-AFTER-RELEASE" >&2
"""


@pytest.mark.skipif(shutil.which("flock") is None, reason="flock(1) absent: fd 9 is never opened")
def test_stderr_survives_acquire_and_release(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    proc = subprocess.run(
        ["bash", "-c", SCRIPT, "lockcheck", str(LIB), str(tmp_path / "ws")],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        env={"HOME": str(home), "PATH": "/usr/bin:/bin:/usr/local/bin"},
    )
    assert proc.returncode == 0, proc.stderr
    assert "NOT-ACQUIRED" not in proc.stderr
    assert "STDERR-AFTER-ACQUIRE" in proc.stderr
    assert "STDERR-AFTER-RELEASE" in proc.stderr

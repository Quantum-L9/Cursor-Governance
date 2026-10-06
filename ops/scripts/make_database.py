"""GNU Make database reader that stays on Apple's Make 3.81.

``--eval`` is a GNU Make 4 option. ``/usr/bin/make`` on macOS is 3.81 and
rejects it, so a probe that uses it reports every target absent. ``-p``
prints the composed database for any goal, and ``help`` is a declared goal
that does not require the governance interpreter.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


def make_database(repo: Path) -> subprocess.CompletedProcess[str]:
    """Return Make's composed database for ``repo`` without running a recipe."""
    return subprocess.run(
        ["make", "--no-print-directory", "-rRpn", "help"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )


def makefile_has_target(repo: Path, name: str) -> bool:
    """True when ``name`` is a rule in the composed database."""
    result = make_database(repo)
    return (
        result.returncode == 0 and re.search(rf"(?m)^{re.escape(name)}:", result.stdout) is not None
    )

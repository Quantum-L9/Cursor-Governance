"""GMP report location and naming — the machine form of ``rules/81-gmp-audit.mdc``.

Reports are optional. When one exists it lives in ``reports/gmp/`` of the work
clone (``ops/reports/publish.py`` owns the folder) and is named
``GMP-Report-<NNN>-<Description>.md``. Content is the author's choice; only the
name is checked, so reports stay consistent and findable.
"""

from __future__ import annotations

import re
from pathlib import Path

NAME_RE = re.compile(r"^GMP-Report-(\d{3,})-[A-Za-z0-9][A-Za-z0-9-]*\.md$")
NAME_PATTERN = "GMP-Report-<NNN>-<Description>.md"

#: Every place a GMP report has been written in a clone, newest first. The
#: legacy executor name ``GMP-<n>-<slug>.md`` is still counted for numbering.
SCAN_DIRS: tuple[Path, ...] = (
    Path("reports") / "gmp",
    Path("reports") / "GMP Reports",
    Path("reports"),
)
_NUMBER_RE = re.compile(r"^GMP-(?:Report-)?(\d+)\b")


def next_gmp_number(root: Path, floor: int = 1) -> int:
    """Highest GMP number already in the clone + 1 (never below ``floor``)."""
    highest = floor - 1
    for rel in SCAN_DIRS:
        folder = Path(root) / rel
        if not folder.is_dir():
            continue
        for path in folder.glob("GMP-*.md"):
            match = _NUMBER_RE.match(path.name)
            if match:
                highest = max(highest, int(match.group(1)))
    return highest + 1


def format_gmp_id(number: int) -> str:
    return f"GMP-{number:03d}"


def describe(text: str, limit: int = 60) -> str:
    """``<Description>`` from free text: letters, digits and hyphens."""
    return re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")[:limit].strip("-") or "Report"


def report_name(number: int, description: str) -> str:
    return f"GMP-Report-{number:03d}-{describe(description)}.md"


def name_error(path: Path) -> str:
    """Why ``path`` does not follow the name pattern, or "" when it does."""
    name = Path(path).name
    return "" if NAME_RE.match(name) else f"expected {NAME_PATTERN}, got {name}"

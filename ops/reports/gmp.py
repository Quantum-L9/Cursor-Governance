"""GMP report contract — the machine form of ``rules/83-gmp-contracts.mdc``.

Rule 83 states the contract; this module is the only code that checks it, so
the rule and the check cannot drift:

* location  ``reports/gmp/`` in the work clone (``ops/reports/publish.py``)
* name      ``GMP-Report-<NNN>-<Description>.md`` (3-digit, zero-padded)
* header    one line: ``**ID:** GMP-NNN | **Task:** … | **Tier:** …_TIER |
            **Date:** YYYY-MM-DD | **Status:** …``
* sections  the seven ``## `` sections below, in order; the forbidden ones absent

Reports the ``/gmp`` executor writes itself (``GMP-<n>-<slug>.md``) are its
own receipt format and are not held to the hand-authored contract.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

REQUIRED_SECTIONS: tuple[str, ...] = (
    "TODO PLAN",
    "PHASES",
    "CHANGES",
    "TODO → CHANGE MAP",
    "VALIDATION",
    "VERIFICATION",
    "DECLARATION",
)
FORBIDDEN_SECTIONS: tuple[str, ...] = ("YNP RECOMMENDATION", "NEXT STEPS")

NAME_RE = re.compile(r"^GMP-Report-(\d{3,})-[A-Za-z0-9][A-Za-z0-9._-]*\.md$")
HEADER_RE = re.compile(
    r"^\*\*ID:\*\* GMP-(?P<id>\d{3,}) \| \*\*Task:\*\* (?P<task>.+?) \| "
    r"\*\*Tier:\*\* (?P<tier>[A-Z_]+_TIER) \| \*\*Date:\*\* (?P<date>\d{4}-\d{2}-\d{2}) \| "
    r"\*\*Status:\*\* (?P<status>.+)$"
)
#: Every place a GMP report has ever been written in a clone, newest first.
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


def is_contract_report(path: Path) -> bool:
    """Hand-authored reports (``GMP-Report-*``) are held to the contract."""
    return Path(path).name.startswith("GMP-Report-")


def validate(path: Path) -> list[str]:
    """Contract errors for one report; empty means it conforms."""
    path = Path(path)
    errors: list[str] = []
    name = NAME_RE.match(path.name)
    if not name:
        errors.append(f"name: expected GMP-Report-NNN-Description.md, got {path.name}")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return errors + [f"unreadable: {type(exc).__name__}"]
    lines = text.splitlines()
    first = next((line.strip() for line in lines if line.strip()), "")
    header = HEADER_RE.match(first)
    if not header:
        errors.append(
            "header: first line must be '**ID:** GMP-NNN | **Task:** … | **Tier:** …_TIER | "
            "**Date:** YYYY-MM-DD | **Status:** …'"
        )
    else:
        try:
            date.fromisoformat(header["date"])
        except ValueError:
            errors.append(f"header: Date {header['date']} is not a valid ISO date")
        if name and int(header["id"]) != int(name.group(1)):
            errors.append(f"header: ID GMP-{header['id']} does not match file name")
    headings = [line[3:].strip() for line in lines if line.startswith("## ")]
    upper = [h.upper() for h in headings]
    missing = [s for s in REQUIRED_SECTIONS if s not in upper]
    if missing:
        errors.append(f"sections: missing {', '.join('## ' + s for s in missing)}")
    else:
        order = [upper.index(s) for s in REQUIRED_SECTIONS]
        if order != sorted(order):
            errors.append("sections: required sections are out of order")
    for forbidden in FORBIDDEN_SECTIONS:
        if forbidden in upper:
            errors.append(f"sections: '## {forbidden}' is forbidden")
    return errors

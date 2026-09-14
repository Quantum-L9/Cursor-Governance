"""Admit writes only for missing files or skill-owned generated files.

An existing file without this skill's generator marker is unowned. The skill
may create a missing target and may refresh a marked generated file whose
bytes are stale. It must not overwrite unowned content.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

Admission = Literal["create", "refresh", "preserve", "unchanged", "skipped"]


def admit_owned_write(existing: str | None, rendered: str, marker: str) -> Admission:
    if existing is None:
        return "create"
    if existing == rendered:
        return "unchanged"
    if marker in existing:
        return "refresh"
    return "preserve"


def apply_owned_write(path: Path, rendered: str, marker: str) -> tuple[bool, Admission]:
    existing = path.read_text(encoding="utf-8") if path.is_file() else None
    admission = admit_owned_write(existing, rendered, marker)
    if admission in {"create", "refresh"}:
        path.write_text(rendered, encoding="utf-8")
        return True, admission
    return False, admission

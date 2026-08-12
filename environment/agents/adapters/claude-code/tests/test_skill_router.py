#!/usr/bin/env python3
"""Compatibility shim — canonical scorer tests live under ops/skill_routing/tests/."""

from __future__ import annotations

import runpy
from pathlib import Path


def _repo_root(start: Path) -> Path:
    for parent in [start, *start.parents]:
        if (parent / "CANONICAL_LAW.md").is_file() or (parent / ".git").exists():
            return parent
    raise RuntimeError(f"repo root not found from {start}")


CANONICAL = (
    _repo_root(Path(__file__).resolve().parent)
    / "ops"
    / "skill_routing"
    / "tests"
    / "test_route_prompt.py"
)

if __name__ == "__main__":
    runpy.run_path(str(CANONICAL), run_name="__main__")

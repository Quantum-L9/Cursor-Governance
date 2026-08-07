#!/usr/bin/env python3
"""Compatibility shim — canonical scorer tests live under ops/skill_routing/tests/."""

from __future__ import annotations

import runpy
from pathlib import Path

CANONICAL = (
    Path(__file__).resolve().parents[3] / "ops" / "skill_routing" / "tests" / "test_route_prompt.py"
)

if __name__ == "__main__":
    runpy.run_path(str(CANONICAL), run_name="__main__")

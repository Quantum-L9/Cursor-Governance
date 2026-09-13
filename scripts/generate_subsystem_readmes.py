#!/usr/bin/env python3
"""Compatibility wrapper for the skill-owned AST module README generator.

Implementation lives in skills/l9-update-agent-docs/scripts/generate_module_readmes.py.
This module re-exports that API so DAG, tests, and existing CLI paths keep working.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SKILL_SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "l9-update-agent-docs" / "scripts"
if str(_SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SKILL_SCRIPTS))

from generate_module_readmes import *  # noqa: E402,F403
from generate_module_readmes import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())

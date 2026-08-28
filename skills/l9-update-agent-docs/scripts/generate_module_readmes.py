#!/usr/bin/env python3
"""Skill-pack entry that delegates to the wired repo generator.

readme-pipeline-v1 and this skill both call
`scripts/generate_subsystem_readmes.py`. Keep one implementation.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

REPO_GENERATOR = (
    Path(__file__).resolve().parents[3] / "scripts" / "generate_subsystem_readmes.py"
)


def main() -> int:
    if not REPO_GENERATOR.is_file():
        print(f"missing wired generator: {REPO_GENERATOR}", file=sys.stderr)
        return 1
    sys.argv = [str(REPO_GENERATOR), *sys.argv[1:]]
    runpy.run_path(str(REPO_GENERATOR), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

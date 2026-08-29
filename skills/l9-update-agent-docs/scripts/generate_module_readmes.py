#!/usr/bin/env python3
"""Skill-pack entry that delegates to the wired repo generator.

readme-pipeline-v1 and this skill both call
`scripts/generate_subsystem_readmes.py`. Keep one implementation.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def find_repo_generator() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "scripts" / "generate_subsystem_readmes.py"
        config = parent / "config" / "subsystems" / "readme_config.yaml"
        if candidate.is_file() and config.is_file():
            return candidate
    raise FileNotFoundError(
        "wired generator not found (scripts/generate_subsystem_readmes.py "
        "+ config/subsystems/readme_config.yaml)"
    )


def main(argv: list[str] | None = None) -> int:
    generator = find_repo_generator()
    spec = importlib.util.spec_from_file_location("l9_generate_subsystem_readmes", generator)
    if spec is None or spec.loader is None:
        print(f"cannot load wired generator: {generator}", file=sys.stderr)
        return 1
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return int(module.main(argv))


if __name__ == "__main__":
    raise SystemExit(main())

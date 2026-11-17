"""Load a sibling script by file path.

The skill directory name is not a Python package, so callers execute each
script from its own path. Tests import this module after ``conftest.py`` puts
the directory on ``sys.path``.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_sibling(stem: str):
    name = f"l9_strategic_plan_scripts.{stem}"
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    path = Path(__file__).resolve().parent / f"{stem}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(stem)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

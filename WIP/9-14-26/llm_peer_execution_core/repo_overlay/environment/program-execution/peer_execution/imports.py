from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def load_module(path: str | Path, name: str) -> ModuleType:
    source = Path(path).expanduser()
    if source.is_symlink():
        raise ImportError(f"refusing symlinked module source: {source}")
    source = source.resolve()
    if not source.is_file():
        raise ImportError(f"module source does not exist: {source}")
    spec = importlib.util.spec_from_file_location(name, source)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to load module: {source}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module

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


# --- Program Execution's own `scripts/` package -----------------------------
#
# `scripts` is NOT a name Program Execution owns. The repository root ships a
# `scripts/` package of its own, and the root pytest suite runs with
# PYTHONPATH=${REPO_ROOT} (ops/config/python-contract.json, suite `repo-root`),
# so both providers are importable in one interpreter.
#
# Python binds a top-level package name once per process. Whichever provider is
# imported first owns `sys.modules["scripts"]` for the rest of that process, and
# its `__path__` is fixed at that moment. A later `sys.path.insert(0, PE_ROOT)`
# cannot rebind it: the name already resolves, so the finders are never
# consulted again and `scripts.provider_loader` raises ModuleNotFoundError.
# Presence on sys.path was never the same thing as precedence, and precedence
# itself is not enough once a foreign binding exists.
#
# So Program Execution resolves its own package by FILE LOCATION and registers
# it under a name it owns exclusively. No sys.path mutation, no eviction of
# another subsystem's `scripts` binding, and no dependence on which suite,
# module, or test happened to import first.

PE_SCRIPTS_PACKAGE = "pe_scripts"


def _pe_scripts_dir() -> Path:
    """Absolute path of `environment/program-execution/scripts`.

    Derived from this file's own location, so it is correct under direct CLI
    execution, `import peer_execution.imports`, and
    `spec_from_file_location` loading alike.
    """
    return Path(__file__).resolve().parents[1] / "scripts"


def bind_pe_scripts() -> ModuleType:
    """Bind Program Execution's `scripts/` package as `pe_scripts` and return it.

    Idempotent: a second call returns the already-bound package rather than
    re-executing it, so every caller shares one module instance (identity
    checks and module-level state stay coherent).
    """
    existing = sys.modules.get(PE_SCRIPTS_PACKAGE)
    directory = _pe_scripts_dir()
    if existing is not None:
        bound = [Path(entry).resolve() for entry in getattr(existing, "__path__", [])]
        if bound == [directory]:
            return existing
        raise ImportError(f"{PE_SCRIPTS_PACKAGE} is already bound to {bound}, not {directory}")

    init = directory / "__init__.py"
    if not init.is_file():
        raise ImportError(f"Program Execution scripts package is missing: {init}")
    spec = importlib.util.spec_from_file_location(
        PE_SCRIPTS_PACKAGE,
        init,
        submodule_search_locations=[str(directory)],
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to load package: {directory}")
    package = importlib.util.module_from_spec(spec)
    sys.modules[PE_SCRIPTS_PACKAGE] = package
    try:
        spec.loader.exec_module(package)
    except Exception:
        sys.modules.pop(PE_SCRIPTS_PACKAGE, None)
        raise
    return package


def pe_script(module_name: str) -> ModuleType:
    """Import one module from Program Execution's own `scripts/` package.

    Use instead of `from scripts.<module> import ...` anywhere inside Program
    Execution. `module_name` is the bare sibling name, e.g. "provider_loader".
    """
    if not module_name or module_name.startswith(".") or "/" in module_name:
        raise ValueError(f"not a Program Execution script module: {module_name!r}")
    bind_pe_scripts()
    return importlib.import_module(f"{PE_SCRIPTS_PACKAGE}.{module_name}")

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


def load_package(directory: str | Path, name: str) -> ModuleType:
    """Bind a package DIRECTORY under `name`, resolved by location only.

    The location-based twin of `load_module`: submodules of the result import
    normally through `__path__`, so callers use ordinary `import_module` rather
    than loading each file by hand. Idempotent -- a second call for the same
    directory returns the bound package instead of re-executing it, so every
    caller shares one instance and module-level state stays coherent. A name
    already bound to a DIFFERENT directory is an error, never a silent
    overwrite of somebody else's package. A symlinked package directory or
    `__init__.py` is refused, the same control `load_module` applies to a
    single source.
    """
    directory = Path(directory).expanduser()
    # A symlinked package directory or `__init__.py` would execute code from
    # outside the subsystem under a name the subsystem vouches for. Checked
    # BEFORE resolve(), because resolve() follows the link and erases the
    # evidence.
    if directory.is_symlink() or (directory / "__init__.py").is_symlink():
        raise ImportError(f"refusing symlinked package source: {directory}")
    directory = directory.resolve()
    existing = sys.modules.get(name)
    if existing is not None:
        bound = [Path(entry).resolve() for entry in getattr(existing, "__path__", [])]
        if bound == [directory]:
            return existing
        raise ImportError(f"{name} is already bound to {bound}, not {directory}")

    init = directory / "__init__.py"
    if not init.is_file():
        raise ImportError(f"not a package: {directory}")
    spec = importlib.util.spec_from_file_location(
        name, init, submodule_search_locations=[str(directory)]
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to load package: {directory}")
    package = importlib.util.module_from_spec(spec)
    sys.modules[name] = package
    try:
        spec.loader.exec_module(package)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return package


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
#
# This accessor lives in `peer_execution` because that is the only PE-exclusive
# namespace a module inside `scripts/` can import WITHOUT first binding the
# ambiguous name -- the constraint is Python's import model, not a layering
# preference. The generic half above carries no knowledge of `scripts`.

PE_SCRIPTS_PACKAGE = "pe_scripts"


def _pe_scripts_dir() -> Path:
    """Absolute path of `environment/program-execution/scripts`.

    Derived from this file's own location, so it is correct under direct CLI
    execution, `import peer_execution.imports`, and `spec_from_file_location`
    loading alike.
    """
    return Path(__file__).resolve().parents[1] / "scripts"


def bind_pe_scripts() -> ModuleType:
    """Bind Program Execution's `scripts/` package as `pe_scripts`."""
    return load_package(_pe_scripts_dir(), PE_SCRIPTS_PACKAGE)


def pe_script(module_name: str) -> ModuleType:
    """Import one module from Program Execution's own `scripts/` package.

    Use instead of `from scripts.<module> import ...` anywhere inside Program
    Execution. `module_name` is the bare sibling name, e.g. "provider_loader".
    """
    if not module_name or module_name.startswith(".") or "/" in module_name or "\\" in module_name:
        raise ValueError(f"not a Program Execution script module: {module_name!r}")
    bind_pe_scripts()
    return importlib.import_module(f"{PE_SCRIPTS_PACKAGE}.{module_name}")

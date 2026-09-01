#!/usr/bin/env python3
"""CLI path confinement for SonarCloud pythonsecurity:S8707."""

from __future__ import annotations

import os
from pathlib import Path


def plans_store_root() -> Path | None:
    """Machine Cursor plans store (``~/.cursor/plans`` or ``L9_PLANS_STORE``)."""
    override = os.environ.get("L9_PLANS_STORE", "").strip()
    if override:
        try:
            return Path(override).expanduser().resolve()
        except OSError:
            return None
    home = Path.home() / ".cursor" / "plans"
    try:
        if home.exists():
            return home.resolve()
    except OSError:
        return None
    return None


def is_under(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def confined_roots(*extra: Path) -> list[Path]:
    roots = [Path.cwd().resolve(), *extra]
    store = plans_store_root()
    if store is not None:
        roots.append(store)
    out: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if root not in seen:
            seen.add(root)
            out.append(root)
    return out


def safe_cli_path(value: str | Path) -> Path:
    """Resolve a CLI path; require cwd or the canonical plans store."""
    base = Path.cwd().resolve()
    raw = Path(value)
    resolved = raw.resolve() if raw.is_absolute() else (base / raw).resolve()
    if not any(is_under(resolved, root) for root in confined_roots()):
        raise SystemExit(f"path escapes the working directory and plans store: {value}")
    return resolved

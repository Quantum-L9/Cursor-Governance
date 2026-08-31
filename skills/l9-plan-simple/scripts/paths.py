#!/usr/bin/env python3
"""CLI path confinement for SonarCloud pythonsecurity:S8707."""

from __future__ import annotations

from pathlib import Path


def safe_cli_path(value: str | Path) -> Path:
    """Resolve a CLI-supplied path and require it to stay within cwd."""
    base = Path.cwd().resolve()
    resolved = (base / Path(value)).resolve()
    if resolved != base and base not in resolved.parents:
        raise SystemExit(f"path escapes the working directory: {value}")
    return resolved

#!/usr/bin/env python3
"""Render the Manus adapter capability manifest from the canonical registry.

``infisical_capabilities.json`` is a derived artefact. Editing it by hand is
pointless: the next render overwrites the edit, and ``--check`` fails the build
while the edit is still on disk. The only supported change path is an edit to
``ops/secrets/capabilities.yaml`` plus — when a *new* endpoint is wanted — a
reviewed projection in ``capability_source.py``.

Usage::

    python environment/agents/adapters/manus/render_infisical_capabilities.py
    python environment/agents/adapters/manus/render_infisical_capabilities.py --check

``--check`` exits 1 when the file on disk differs from a fresh render, which is
what makes "no drift" a build failure instead of an aspiration.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml

ADAPTER_ROOT = Path(__file__).resolve().parent
if str(ADAPTER_ROOT) not in sys.path:
    sys.path.insert(0, str(ADAPTER_ROOT))

import capability_source  # noqa: E402  (sibling module, path fixed above)

MANIFEST_RELATIVE = Path("environment/agents/adapters/manus/infisical_capabilities.json")
MAX_DIFF_LINES = 40


def _load_registry(repo_root: Path) -> tuple[Any, str]:
    """Return the canonical registry object and its declared schema version."""
    root = str(repo_root)
    if root not in sys.path:
        sys.path.insert(0, root)
    from ops.secrets.capability_registry import load_registry

    registry_path = repo_root / capability_source.REGISTRY_RELATIVE
    raw = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    schema_version = str(raw.get("schema_version") or "")
    if not schema_version:
        raise capability_source.DerivationError(
            f"{capability_source.REGISTRY_RELATIVE.as_posix()} declares no schema_version"
        )
    return load_registry(registry_path), schema_version


def render(repo_root: Path) -> str:
    """Render the manifest text for ``repo_root``. Pure function of the registry."""
    registry, schema_version = _load_registry(repo_root)
    derivation = capability_source.derive(
        registry,
        source_sha256=capability_source.source_digest(
            repo_root / capability_source.REGISTRY_RELATIVE
        ),
        source_schema_version=schema_version,
    )
    return json.dumps(derivation.manifest(), indent=2, sort_keys=False) + "\n"


def manifest_path(repo_root: Path) -> Path:
    return repo_root / MANIFEST_RELATIVE


def _diff(on_disk: str, rendered: str, path: Path) -> str:
    diff = list(
        difflib.unified_diff(
            on_disk.splitlines(keepends=True),
            rendered.splitlines(keepends=True),
            fromfile=f"{path} (on disk)",
            tofile="freshly rendered from ops/secrets/capabilities.yaml",
            n=0,
        )
    )
    if len(diff) > MAX_DIFF_LINES:
        diff = diff[:MAX_DIFF_LINES] + [f"... diff truncated at {MAX_DIFF_LINES} lines\n"]
    return "".join(diff)


def check(repo_root: Path) -> int:
    """Exit 0 when the committed manifest matches the registry, 1 when stale."""
    path = manifest_path(repo_root)
    rendered = render(repo_root)
    try:
        on_disk = path.read_text(encoding="utf-8")
    except OSError:
        on_disk = ""
    if on_disk == rendered:
        print(f"PASS — {path.name} is derived from and current with the canonical registry")
        return 0
    print(
        f"FAIL — {path.name} is stale relative to {capability_source.REGISTRY_RELATIVE.as_posix()}",
        file=sys.stderr,
    )
    if on_disk:
        print(_diff(on_disk, rendered, path), file=sys.stderr)
    else:
        print(f"  {path} is missing", file=sys.stderr)
    print(
        "  fix: .venv/bin/python "
        f"{MANIFEST_RELATIVE.parent / 'render_infisical_capabilities.py'} --repo-root {repo_root}",
        file=sys.stderr,
    )
    return 1


def write(repo_root: Path) -> int:
    """Write the manifest atomically, preserving an existing file's mode."""
    path = manifest_path(repo_root)
    rendered = render(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = 0o644
    if path.exists():
        mode = path.stat().st_mode & 0o777
    temporary = path.with_suffix(path.suffix + ".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            fd = -1
            handle.write(rendered)
    except BaseException:
        if fd >= 0:
            os.close(fd)
        temporary.unlink(missing_ok=True)
        raise
    os.chmod(temporary, mode)
    temporary.replace(path)
    print(f"WROTE — {path} ({len(rendered.splitlines())} lines)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[4],
        help="repository root containing ops/secrets/capabilities.yaml",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero when the committed manifest is stale (no write)",
    )
    args = parser.parse_args(argv)
    repo_root = args.repo_root.resolve()
    try:
        return check(repo_root) if args.check else write(repo_root)
    except capability_source.DerivationError as exc:
        print(f"FAIL — derivation refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Render a local stdio Custom MCP draft for signed Manus memory.

With ``--authority-file``, the output carries only the shared agents door and
Manus's own signing key as one encrypted connector environment value.  The
launcher materializes it for one MCP child process and derives the public grant
from the canonical registry.  The authority file and rendered draft are local
operator artifacts, never repository files.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

AUTHORITY_ENV = "L9_MANUS_MEMORY_AUTHORITY_JSON"


def _governance_root(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not (path / "CANONICAL_LAW.md").is_file():
        raise ValueError(f"not a Cursor-Governance checkout: {path}")
    launcher = path / "environment/agents/adapters/manus/serve_memory_mcp.sh"
    materializer = path / "environment/agents/adapters/manus/materialize_memory_authority.py"
    if not launcher.is_file() or not materializer.is_file():
        raise ValueError("signed Manus memory launcher or authority materializer is missing")
    return path


def _scoped_authority(path: Path) -> dict[str, object]:
    from materialize_memory_authority import AuthorityMaterializationError, _scoped_tokens

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return _scoped_tokens(raw)
    except (OSError, json.JSONDecodeError, AuthorityMaterializationError) as exc:
        raise ValueError(f"invalid Manus-scoped authority file: {exc}") from exc


def draft(governance_root: Path, authority: dict[str, object] | None = None) -> dict[str, object]:
    launcher = governance_root / "environment/agents/adapters/manus/serve_memory_mcp.sh"
    server: dict[str, Any] = {
        "command": str(launcher),
        "args": ["--governance", str(governance_root)],
    }
    if authority is not None:
        server["env"] = {
            AUTHORITY_ENV: json.dumps(authority, separators=(",", ":"), sort_keys=True)
        }
    return {"mcpServers": {"l9-memory-manus": server}}


def _write_draft(path: Path, payload: dict[str, object], *, contains_authority: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, indent=2) + "\n")
    if contains_authority:
        os.chmod(path, 0o600)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--governance", required=True, help="Absolute Cursor-Governance checkout")
    parser.add_argument(
        "--authority-file",
        type=Path,
        help="0600 Manus-scoped authority JSON; never use a human or multi-agent map",
    )
    parser.add_argument("--output", type=Path, required=True, help="Destination JSON draft file")
    args = parser.parse_args(argv)
    try:
        governance_root = _governance_root(args.governance)
        authority = _scoped_authority(args.authority_file) if args.authority_file else None
    except ValueError as exc:
        parser.error(str(exc))
        return 2
    _write_draft(
        args.output, draft(governance_root, authority), contains_authority=authority is not None
    )
    print(str(args.output.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

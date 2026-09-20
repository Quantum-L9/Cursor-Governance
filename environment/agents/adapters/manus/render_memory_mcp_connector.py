#!/usr/bin/env python3
"""Render a no-secret local stdio Custom MCP draft for signed Manus memory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _governance_root(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not (path / "CANONICAL_LAW.md").is_file():
        raise ValueError(f"not a Cursor-Governance checkout: {path}")
    launcher = path / "environment/agents/adapters/manus/serve_memory_mcp.sh"
    if not launcher.is_file():
        raise ValueError(f"signed Manus memory launcher is missing: {launcher}")
    return path


def draft(governance_root: Path) -> dict[str, object]:
    launcher = governance_root / "environment/agents/adapters/manus/serve_memory_mcp.sh"
    return {
        "mcpServers": {
            "l9-memory-manus": {
                "command": str(launcher),
                "args": ["--governance", str(governance_root)],
            }
        }
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--governance", required=True, help="Absolute Cursor-Governance checkout")
    parser.add_argument("--output", type=Path, required=True, help="Destination JSON draft file")
    args = parser.parse_args(argv)
    try:
        governance_root = _governance_root(args.governance)
    except ValueError as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(draft(governance_root), indent=2) + "\n", encoding="utf-8")
    print(str(args.output.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

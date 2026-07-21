#!/usr/bin/env python3
# L9_META
#   l9_schema: 1
#   repo: Quantum-L9/L9-Graphite-Memory
#   layer: scripts
#   owner: platform
#   status: active
#   created: 2026-07-05
"""
Generate Cursor MCP configuration for L9 Graphite Memory server.

Writes the mcpServers entry to ~/.cursor/mcp.json so Cursor can connect
to the memory server via stdio transport. Secrets are injected into the
server process env from Infisical bootstrap vars.

Usage:
  python scripts/write_cursor_config.py
  python scripts/write_cursor_config.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def get_server_config() -> dict:
    """Build the MCP server config entry for Cursor."""
    # Resolve the Python interpreter and module path
    python_path = sys.executable
    repo_root = Path(__file__).resolve().parent.parent
    src_path = str(repo_root / "src")

    # Infisical bootstrap vars (must be set on the machine)
    env_vars = {
        "PYTHONPATH": src_path,
    }

    # Only include Infisical vars if they're set (don't leak empty strings)
    for var in ("INFISICAL_CLIENT_ID", "INFISICAL_CLIENT_SECRET", "INFISICAL_PROJECT_ID"):
        val = os.environ.get(var, "").strip()
        if val:
            env_vars[var] = val

    # Allow override of transport and Zep URL
    for var in ("GRAPHITI_TRANSPORT", "ZEP_API_KEY", "ZEP_API_URL", "GRAPHITI_MCP_URL"):
        val = os.environ.get(var, "").strip()
        if val:
            env_vars[var] = val

    return {
        "command": python_path,
        "args": ["-m", "l9_graphite_memory.server"],
        "env": env_vars,
    }


def write_config(dry_run: bool = False) -> dict:
    """Write or update ~/.cursor/mcp.json with the memory server entry."""
    config_path = Path.home() / ".cursor" / "mcp.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    existing: dict = {}
    if config_path.is_file():
        try:
            existing = json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing = {}

    servers = existing.setdefault("mcpServers", {})
    servers["l9-graphite-memory"] = get_server_config()

    if dry_run:
        return {"dry_run": True, "config": existing, "path": str(config_path)}

    config_path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    return {"written": True, "path": str(config_path), "server_name": "l9-graphite-memory"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Write Cursor MCP config for L9 Graphite Memory")
    parser.add_argument("--dry-run", action="store_true", help="Print config without writing")
    args = parser.parse_args()

    result = write_config(dry_run=args.dry_run)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

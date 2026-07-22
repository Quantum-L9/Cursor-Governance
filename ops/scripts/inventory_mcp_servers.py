#!/usr/bin/env python3
"""Read-only MCP inventory with credential values redacted."""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SHELL_NAMES = {"bash", "sh", "zsh", "fish", "powershell", "pwsh", "cmd"}
WRITE_HINTS = re.compile(r"write|create|update|delete|mutat|shell|exec", re.I)
FILESYSTEM_HINTS = re.compile(r"filesystem|file-system|server-filesystem|allowedDirectories|roots", re.I)


def redact_server(name: str, config: dict[str, Any], source: Path) -> dict[str, Any]:
    command = config.get("command")
    args = [str(value) for value in config.get("args", [])] if isinstance(config.get("args"), list) else []
    url = config.get("url") or config.get("serverUrl")
    env = config.get("env") if isinstance(config.get("env"), dict) else {}
    command_name = Path(str(command)).name.lower() if command else None
    serialized = json.dumps(config, sort_keys=True)
    transport = "remote" if url else "local"
    return {
        "name": name,
        "source": str(source),
        "transport": transport,
        "command": str(command) if command else None,
        "args": args,
        "url_host": re.sub(r"^(https?://[^/]+).*$", r"\1", str(url)) if url else None,
        "shell_capability": command_name in SHELL_NAMES or any(Path(arg).name.lower() in SHELL_NAMES for arg in args),
        "filesystem_capability": bool(FILESYSTEM_HINTS.search(serialized)),
        "write_capability_hint": bool(WRITE_HINTS.search(serialized)),
        "credential_sources": sorted(env.keys()),
        "credential_values_redacted": True,
        "startup_behavior": "configured" if config.get("disabled") is not True else "disabled",
        "repository_relevance": "workspace" if "/.cursor/" in str(source) and str(source).startswith(str(Path.cwd())) else "machine_or_unknown",
    }


def extract_servers(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {}
    for key in ("mcpServers", "servers"):
        value = data.get(key)
        if isinstance(value, dict):
            return value
    return {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace", type=Path, nargs="?", default=Path.cwd())
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--config", type=Path, action="append", default=[])
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    home = args.home.expanduser().resolve()
    output_dir = (args.output_dir or workspace / "reports").resolve()

    candidates = [
        home / ".cursor/mcp.json",
        home / ".cursor/mcp-config.json",
        workspace / ".cursor/mcp.json",
        workspace / ".cursor/mcp-config.json",
        *[path.expanduser().resolve() for path in args.config],
    ]
    unique_candidates: list[Path] = []
    for path in candidates:
        if path not in unique_candidates:
            unique_candidates.append(path)

    servers: list[dict[str, Any]] = []
    errors: list[str] = []
    for path in unique_candidates:
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{path}: {exc}")
            continue
        for name, config in sorted(extract_servers(data).items()):
            if isinstance(config, dict):
                servers.append(redact_server(str(name), config, path))

    report = {
        "schema": "l9.mcp-inventory/v1",
        "generated_utc": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "read_only": True,
        "scanned_configs": [str(path) for path in unique_candidates],
        "servers": servers,
        "errors": errors,
        "policy": "Inventory only. Do not rewrite MCP configuration until a repeated management problem is proven.",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "mcp-inventory.json"
    md_path = output_dir / "mcp-inventory.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# MCP inventory and trust classification",
        "",
        f"Generated: `{report['generated_utc']}`",
        "",
        "**Mode:** read-only. Credential values are never emitted.",
        "",
        "| Server | Transport | Shell | Filesystem | Write hint | Credentials | Startup | Source |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for server in servers:
        lines.append(
            f"| `{server['name']}` | {server['transport']} | {server['shell_capability']} | "
            f"{server['filesystem_capability']} | {server['write_capability_hint']} | "
            f"{', '.join(server['credential_sources']) or 'none declared'} | "
            f"{server['startup_behavior']} | `{server['source']}` |"
        )
    if not servers:
        lines.append("| _No readable configured servers found_ |  |  |  |  |  |  |  |")
    lines.extend(["", "## Errors", ""])
    if errors:
        lines.extend(f"- {error}" for error in errors)
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## Decision gate",
            "",
            "Review trust boundaries before changing startup behavior, credentials, or write-capable servers.",
            "",
        ]
    )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"WROTE: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

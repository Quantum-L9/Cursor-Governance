#!/usr/bin/env python3
"""Render a no-secret Manus Custom MCP connector draft for the L9 MCP service."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse


def validate_endpoint(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("MCP endpoint must be an HTTPS URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError(
            "MCP endpoint must not contain credentials, query parameters, or fragments"
        )
    if parsed.path.rstrip("/") != "/mcp":
        raise ValueError("MCP endpoint path must be /mcp")
    return value.rstrip("/")


def draft(endpoint: str) -> dict[str, object]:
    return {
        "mode": "url",
        "mcpServers": {"l9-governance": {"url": endpoint}},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="Public HTTPS URL ending in /mcp")
    parser.add_argument("--output", type=Path, required=True, help="Destination JSON draft file")
    args = parser.parse_args(argv)
    try:
        endpoint = validate_endpoint(args.url)
    except ValueError as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(draft(endpoint), indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Render a Manus Custom MCP form draft for the L9 Governance service.

Without ``--token-file`` this emits the public read-only connector shape. With
one it adds a bearer header to a transient local draft for the protected
lifecycle deployment. The token is never printed or committed by this helper.
"""

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


def _read_token(path: Path) -> str:
    try:
        token = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ValueError(f"could not read token file: {exc}") from exc
    if not token or "\n" in token or "\r" in token:
        raise ValueError("token file must contain one non-empty token line")
    return token


def draft(endpoint: str, *, bearer_token: str | None = None) -> dict[str, object]:
    server: dict[str, object] = {"url": endpoint}
    if bearer_token:
        server["headers"] = {"Authorization": f"Bearer {bearer_token}"}
    return {
        "mode": "form",
        "mcpServers": {"l9-governance": server},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="Public HTTPS URL ending in /mcp")
    parser.add_argument(
        "--token-file",
        type=Path,
        help="Optional local bearer-token file for a protected lifecycle service",
    )
    parser.add_argument("--output", type=Path, required=True, help="Destination JSON draft file")
    args = parser.parse_args(argv)
    try:
        endpoint = validate_endpoint(args.url)
        token = _read_token(args.token_file) if args.token_file else None
    except ValueError as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(draft(endpoint, bearer_token=token), indent=2) + "\n", encoding="utf-8"
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

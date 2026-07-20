#!/usr/bin/env python3
"""Invoke code-graph-rag-mcp tools via one-shot JSON-RPC CLI (stderr suppressed)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_BIN = Path.home() / ".local/code-graph-rag-mcp/node_modules/.bin/code-graph-rag-mcp"


def resolve_bin() -> Path:
    env = os.environ.get("CODE_GRAPH_BIN")
    if env:
        return Path(env).expanduser()
    return DEFAULT_BIN


def resolve_repo() -> Path:
    for key in ("REPO_ROOT", "PWD"):
        val = os.environ.get(key)
        if val:
            return Path(val).expanduser().resolve()
    return Path.cwd().resolve()


def extract_jsonrpc_payload(stdout: str) -> dict[str, Any]:
    """Return JSON-RPC response from stdout (pretty-printed or single-line)."""
    text = stdout.strip()
    if text:
        try:
            obj = json.loads(text)
            if isinstance(obj, dict) and obj.get("jsonrpc") == "2.0":
                return obj
        except json.JSONDecodeError:
            pass

    candidate: dict[str, Any] | None = None
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and obj.get("jsonrpc") == "2.0":
            candidate = obj
    if candidate is None:
        raise RuntimeError(f"No JSON-RPC response found in stdout:\n{text[:500]}")
    return candidate


def call_tool(
    repo_root: Path, tool_name: str, arguments: dict[str, Any] | None = None
) -> dict[str, Any]:
    bin_path = resolve_bin()
    if not bin_path.is_file():
        raise FileNotFoundError(f"code-graph-rag-mcp not found: {bin_path}")

    payload = {
        "jsonrpc": "2.0",
        "id": "cli",
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments or {}},
    }
    proc = subprocess.run(
        [str(bin_path), str(repo_root), json.dumps(payload)],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0 and not proc.stdout.strip():
        raise RuntimeError(proc.stderr.strip() or f"exit {proc.returncode}")

    response = extract_jsonrpc_payload(proc.stdout)
    if "error" in response:
        raise RuntimeError(json.dumps(response["error"], indent=2))

    content = response.get("result", {}).get("content", [])
    if not content:
        return {"raw": response}
    text = content[0].get("text", "")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"text": text}


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: code_graph_cli.py <tool_name> [json_arguments]", file=sys.stderr)
        return 2

    tool = sys.argv[1]
    args: dict[str, Any] = {}
    if len(sys.argv) > 2:
        args = json.loads(sys.argv[2])

    repo = resolve_repo()
    if len(sys.argv) > 3:
        repo = Path(sys.argv[3]).expanduser().resolve()

    result = call_tool(repo, tool, args)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

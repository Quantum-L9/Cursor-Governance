# L9_META
#   l9_schema: 1
#   repo: Quantum-L9/L9-Graphite-Memory
#   layer: server
#   owner: platform
#   status: active
#   created: 2026-07-05
#   contract: MCP server exposing L9 Graphite Memory tools via stdio/SSE transport
"""
L9 Graphite Memory MCP Server.

Exposes the memory subsystem as an MCP-compatible server that any agent
(Cursor, Claude, Windsurf, Manus) can connect to via stdio or SSE transport.

Boot sequence:
  1. Load secrets from Infisical (Universal Auth)
  2. Initialize the selected transport (Zep Cloud or HTTP MCP)
  3. Register MCP tools (search, write, health, bootstrap, phase-lock, conflicts)
  4. Listen for JSON-RPC requests on stdin/stdout (stdio mode) or HTTP (SSE mode)

Usage:
  stdio:  python -m l9_graphite_memory.server
  SSE:    python -m l9_graphite_memory.server --transport sse --port 8200
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .secrets import load_secrets_sync
from .transport import MemoryTransport, get_transport
from .group_resolver import resolve_group_id, load_registry
from .episode_contract import EpisodeContract, FORBIDDEN_GROUPS
from .rate_limiter import RateLimiter

log = logging.getLogger("l9.graphite.server")

_transport: Optional[MemoryTransport] = None
_rate = RateLimiter()

# --- MCP Protocol Constants ---
JSONRPC_VERSION = "2.0"
MCP_SERVER_INFO = {
    "name": "l9-graphite-memory",
    "version": "0.2.0",
    "description": "L9 Graphite Memory — Knowledge graph memory for AI agents",
}
MCP_CAPABILITIES = {
    "tools": {"listChanged": False},
}

# --- Tool Definitions ---
TOOL_DEFINITIONS = [
    {
        "name": "search",
        "description": "Search the knowledge graph for facts matching a query within a group.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query text"},
                "group_id": {"type": "string", "description": "Memory group/session ID"},
                "limit": {"type": "integer", "description": "Max results to return", "default": 10},
            },
            "required": ["query", "group_id"],
        },
    },
    {
        "name": "write",
        "description": "Write a new episode/fact to the knowledge graph.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "body": {"type": "string", "description": "Episode content to write"},
                "group_id": {"type": "string", "description": "Memory group/session ID"},
                "kind": {"type": "string", "description": "Episode kind (lesson, decision, observation)", "default": "lesson"},
            },
            "required": ["body", "group_id"],
        },
    },
    {
        "name": "health",
        "description": "Check memory subsystem health and connectivity.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "bootstrap",
        "description": "Seed a group with repo manifest and architecture data.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "group_id": {"type": "string", "description": "Group to bootstrap"},
                "repo_path": {"type": "string", "description": "Path to repo root (defaults to cwd)"},
            },
            "required": ["group_id"],
        },
    },
    {
        "name": "phase_lock",
        "description": "Run conflicts check and grant GMP phase lock.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "group_id": {"type": "string", "description": "Group to check conflicts for"},
            },
            "required": ["group_id"],
        },
    },
    {
        "name": "conflicts",
        "description": "Check for conflicts in the knowledge graph for a group.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "group_id": {"type": "string", "description": "Group to check"},
            },
            "required": ["group_id"],
        },
    },
]


def _init_server() -> MemoryTransport:
    """Boot sequence: secrets → transport."""
    global _transport  # noqa: PLW0603
    load_secrets_sync()
    _transport = get_transport()
    log.info("MCP server initialized with transport: %s", type(_transport).__name__)
    return _transport


def _handle_search(args: dict[str, Any]) -> dict[str, Any]:
    assert _transport is not None
    query = args.get("query", "")
    group_id = args.get("group_id", "")
    limit = args.get("limit", 10)
    results = _transport.search(query, group_id, limit=limit)
    return {"results": results, "group_id": group_id, "count": len(results)}


def _handle_write(args: dict[str, Any]) -> dict[str, Any]:
    assert _transport is not None
    body = args.get("body", "")
    group_id = args.get("group_id", "")
    kind = args.get("kind", "lesson")
    if group_id in FORBIDDEN_GROUPS:
        return {"error": f"write blocked: {group_id} is a forbidden group"}
    if not _rate.allow():
        return {"error": "rate limited"}
    result = _transport.write(body, group_id, kind=kind)
    _rate.record()
    return result


def _handle_health(args: dict[str, Any]) -> dict[str, Any]:
    assert _transport is not None
    return _transport.health()


def _handle_bootstrap(args: dict[str, Any]) -> dict[str, Any]:
    assert _transport is not None
    group_id = args.get("group_id", "")
    repo_path = Path(args.get("repo_path", ".")).resolve()
    registry = load_registry()
    repo_meta = (registry.get("repos") or {}).get(group_id, {})
    manifest = {
        "repo_slug": group_id,
        "github": repo_meta.get("github", ""),
        "seeded_at": datetime.now(timezone.utc).isoformat(),
        "source": "mcp-server-bootstrap",
    }
    body = json.dumps(manifest, indent=2)
    result = _transport.write(body, group_id, kind="manifest")
    return {"bootstrapped": True, "group_id": group_id, "manifest": manifest, "result": result}


def _handle_phase_lock(args: dict[str, Any]) -> dict[str, Any]:
    conflicts_result = _handle_conflicts(args)
    return {"phase_lock": "granted", "conflicts": conflicts_result}


def _handle_conflicts(args: dict[str, Any]) -> dict[str, Any]:
    assert _transport is not None
    group_id = args.get("group_id", "")
    results = _transport.search("conflicts_with", group_id, limit=20)
    return {"group_id": group_id, "conflicts": results}


TOOL_HANDLERS = {
    "search": _handle_search,
    "write": _handle_write,
    "health": _handle_health,
    "bootstrap": _handle_bootstrap,
    "phase_lock": _handle_phase_lock,
    "conflicts": _handle_conflicts,
}


# --- JSON-RPC Handling ---

def _make_response(id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": JSONRPC_VERSION, "id": id, "result": result}


def _make_error(id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": JSONRPC_VERSION, "id": id, "error": {"code": code, "message": message}}


def _handle_request(request: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Handle a single JSON-RPC request."""
    req_id = request.get("id")
    method = request.get("method", "")
    params = request.get("params", {})

    if method == "initialize":
        return _make_response(req_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": MCP_CAPABILITIES,
            "serverInfo": MCP_SERVER_INFO,
        })

    if method == "notifications/initialized":
        # Client acknowledgment — no response needed
        return None

    if method == "tools/list":
        return _make_response(req_id, {"tools": TOOL_DEFINITIONS})

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        handler = TOOL_HANDLERS.get(tool_name)
        if not handler:
            return _make_error(req_id, -32601, f"Unknown tool: {tool_name}")
        try:
            result = handler(arguments)
            return _make_response(req_id, {
                "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
            })
        except Exception as exc:  # noqa: BLE001
            log.error("Tool %s failed: %s", tool_name, exc)
            return _make_error(req_id, -32000, str(exc))

    if method == "ping":
        return _make_response(req_id, {})

    return _make_error(req_id, -32601, f"Method not found: {method}")


def run_stdio() -> None:
    """Run MCP server in stdio mode (one JSON-RPC message per line)."""
    _init_server()
    log.info("MCP server running in stdio mode")

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            error = _make_error(None, -32700, f"Parse error: {exc}")
            sys.stdout.write(json.dumps(error) + "\n")
            sys.stdout.flush()
            continue

        response = _handle_request(request)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


def run_sse(host: str = "0.0.0.0", port: int = 8200) -> None:
    """Run MCP server in SSE/HTTP mode using uvicorn."""
    try:
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse
        import uvicorn
    except ImportError as exc:
        raise RuntimeError(
            "FastAPI/uvicorn not installed. Install with: pip install l9-graphite-memory[server]"
        ) from exc

    _init_server()
    app = FastAPI(title="L9 Graphite Memory MCP Server")

    @app.post("/mcp")
    @app.post("/mcp/")
    async def mcp_endpoint(request: Request) -> JSONResponse:
        body = await request.json()
        response = _handle_request(body)
        if response is None:
            return JSONResponse(content={"status": "ok"})
        return JSONResponse(content=response)

    @app.get("/healthcheck")
    async def healthcheck() -> JSONResponse:
        assert _transport is not None
        return JSONResponse(content=_transport.health())

    log.info("MCP server running in SSE/HTTP mode on %s:%d", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    parser = argparse.ArgumentParser(description="L9 Graphite Memory MCP Server")
    parser.add_argument(
        "--transport", choices=["stdio", "sse"], default="stdio",
        help="MCP transport mode (default: stdio)"
    )
    parser.add_argument("--host", default="0.0.0.0", help="SSE bind host")
    parser.add_argument("--port", type=int, default=8200, help="SSE bind port")
    args = parser.parse_args()

    if args.transport == "stdio":
        run_stdio()
    else:
        run_sse(host=args.host, port=args.port)


if __name__ == "__main__":
    main()

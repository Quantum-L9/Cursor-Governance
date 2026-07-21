# L9_META
#   l9_schema: 1
#   repo: Quantum-L9/L9-Graphite-Memory
#   layer: transport
#   owner: platform
#   status: active
#   created: 2026-07-05
#   contract: MemoryTransport protocol abstraction
"""
Transport abstraction for L9-Graphite-Memory.

Defines the ``MemoryTransport`` Protocol that all backend implementations
(HTTP MCP, Zep Cloud, mock) must satisfy. The memory client imports only
this protocol; concrete backends are selected at runtime via environment
variable ``GRAPHITI_TRANSPORT``.

Implementations:
  - HttpMcpTransport: Raw HTTP JSON-RPC to a self-hosted MCP server (legacy).
  - ZepCloudTransport: Zep Cloud SDK (see zep_transport.py).
"""
from __future__ import annotations

import json
import logging
import os
import ssl
import urllib.error
import urllib.request
from typing import Any, Optional, Protocol, runtime_checkable

from .circuit_breaker import CircuitBreaker
from .rate_limiter import RateLimiter

__all__ = [
    "MemoryTransport",
    "HttpMcpTransport",
    "get_transport",
]

log = logging.getLogger("l9.graphite.transport")


@runtime_checkable
class MemoryTransport(Protocol):
    """Protocol that all memory transport backends must implement."""

    def health(self) -> dict[str, Any]:
        """Return health/liveness status of the backend."""
        ...

    def search(self, query: str, group_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search the knowledge graph for facts/nodes matching query."""
        ...

    def write(self, body: str, group_id: str, kind: str = "lesson", **kwargs: Any) -> dict[str, Any]:
        """Write an episode/fact to the knowledge graph."""
        ...

    def call_tool(self, name: str, arguments: Optional[dict[str, Any]] = None) -> Any:
        """Call a named MCP tool with arguments."""
        ...

    def list_tools(self) -> list[str]:
        """List available tool names on the backend."""
        ...


class HttpMcpTransport:
    """Raw HTTP JSON-RPC transport to a self-hosted MCP server (legacy)."""

    def __init__(self) -> None:
        self._circuit = CircuitBreaker()
        self._rate = RateLimiter()

    def _url(self) -> str:
        base = os.environ.get("GRAPHITI_MCP_URL", "http://127.0.0.1:8100/mcp/").rstrip("/")
        return base if base.endswith("/mcp") or base.endswith("/mcp/") else f"{base}/mcp/"

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        token = os.environ.get("GRAPHITI_MCP_TOKEN", "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _rpc(self, method: str, params: Optional[dict[str, Any]] = None, timeout: int = 30) -> dict[str, Any]:
        if not self._circuit.can_execute():
            raise RuntimeError("circuit breaker OPEN")
        payload = {"jsonrpc": "2.0", "id": "cli", "method": method, "params": params or {}}
        req = urllib.request.Request(
            self._url(),
            data=json.dumps(payload).encode(),
            headers=self._headers(),
            method="POST",
        )
        ssl_ctx = ssl.create_default_context()
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx) as resp:
                body = json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            self._circuit.record_failure()
            detail = exc.read().decode()[:500]
            raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            self._circuit.record_failure()
            raise RuntimeError(f"MCP unreachable: {exc.reason}") from exc
        if "error" in body:
            self._circuit.record_failure()
            raise RuntimeError(json.dumps(body["error"]))
        self._circuit.record_success()
        return body.get("result", body)

    def health(self) -> dict[str, Any]:
        """Check liveness and tool plane reachability."""
        result: dict[str, Any] = {"transport": "http_mcp", "healthy": False}
        # Liveness
        try:
            health_url = self._url().replace("/mcp/", "/healthcheck").replace("/mcp", "/healthcheck")
            req = urllib.request.Request(health_url, headers=self._headers())
            ssl_ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, timeout=10, context=ssl_ctx) as resp:
                result["liveness"] = json.loads(resp.read().decode())
            result["liveness_ok"] = True
        except Exception as exc:  # noqa: BLE001
            result["liveness_ok"] = False
            result["liveness_error"] = str(exc)
        # Tool plane
        try:
            tools_result = self._rpc("tools/list", {}, timeout=10)
            tools = tools_result.get("tools", tools_result) if isinstance(tools_result, dict) else tools_result
            names = [t.get("name") for t in tools if isinstance(t, dict)] if isinstance(tools, list) else []
            result["tool_plane_reachable"] = True
            result["tool_count"] = len(names)
        except Exception as exc:  # noqa: BLE001
            result["tool_plane_reachable"] = False
            result["tool_plane_error"] = str(exc)
        result["healthy"] = bool(result.get("liveness_ok")) and bool(result.get("tool_plane_reachable"))
        result["circuit"] = self._circuit.status()
        return result

    def search(self, query: str, group_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search via MCP tools."""
        for tool, arg_key in (("search_facts", "max_facts"), ("search_nodes", "max_nodes")):
            try:
                data = self.call_tool(tool, {"query": query, "group_id": group_id, arg_key: limit})
                facts = self._extract_facts(data)
                if facts:
                    return facts
            except Exception as exc:  # noqa: BLE001
                log.warning("search tool %s failed for %s: %s", tool, group_id, exc)
                continue
        return []

    def write(self, body: str, group_id: str, kind: str = "lesson", **kwargs: Any) -> dict[str, Any]:
        """Write an episode via MCP add_episode tool."""
        if not self._rate.allow():
            raise RuntimeError("rate limit exceeded")
        self._rate.record()
        arguments: dict[str, Any] = {
            "name": f"{kind}:{body[:60]}",
            "body": body,
            "group_id": group_id,
            "source_description": f"l9-memory-cli/{kind}",
        }
        arguments.update(kwargs)
        return self.call_tool("add_episode", arguments)

    def call_tool(self, name: str, arguments: Optional[dict[str, Any]] = None) -> Any:
        """Call a named MCP tool."""
        result = self._rpc("tools/call", {"name": name, "arguments": arguments or {}})
        content = result.get("content", []) if isinstance(result, dict) else []
        if content and isinstance(content[0], dict):
            text = content[0].get("text", "")
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text
        return result

    def list_tools(self) -> list[str]:
        """List available MCP tools."""
        try:
            result = self._rpc("tools/list", {}, timeout=10)
            tools = result.get("tools", result) if isinstance(result, dict) else result
            return sorted(t.get("name", "") for t in tools if isinstance(t, dict))
        except Exception:  # noqa: BLE001
            return []

    @staticmethod
    def _extract_facts(data: Any) -> list[dict[str, Any]]:
        if isinstance(data, dict):
            return list(data.get("facts") or data.get("results") or data.get("nodes") or [])
        if isinstance(data, list):
            return data
        return []


def get_transport() -> MemoryTransport:
    """Factory: return the appropriate transport based on GRAPHITI_TRANSPORT env var.

    Values:
      - "zep" (default): ZepCloudTransport (requires zep-python + ZEP_API_KEY)
      - "http": HttpMcpTransport (legacy self-hosted MCP)
      - "mock": raises NotImplementedError (for future test mock)

    Falls back to HttpMcpTransport if zep-python is not installed.
    """
    transport_type = os.environ.get("GRAPHITI_TRANSPORT", "zep").lower().strip()

    if transport_type == "http":
        log.info("Using HttpMcpTransport (legacy)")
        return HttpMcpTransport()

    if transport_type == "zep":
        try:
            from .zep_transport import ZepCloudTransport
            log.info("Using ZepCloudTransport")
            return ZepCloudTransport()
        except ImportError:
            log.warning("zep-python not installed; falling back to HttpMcpTransport")
            return HttpMcpTransport()
        except RuntimeError as exc:
            log.warning("ZepCloudTransport init failed (%s); falling back to HttpMcpTransport", exc)
            return HttpMcpTransport()

    log.warning("Unknown GRAPHITI_TRANSPORT=%s; using HttpMcpTransport", transport_type)
    return HttpMcpTransport()

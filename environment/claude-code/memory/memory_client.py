#!/usr/bin/env python3
"""Zero-dependency JSON-RPC client for the l9-shared-memory HTTP MCP server.

Uses only the Python standard library so the enforcement hooks run in any
consumer repository without a virtualenv. The server is the l9-graphite-memory
control plane; identity is derived from the bearer token, never a call argument.

Never logs or prints the bearer token.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class MemoryError(RuntimeError):
    """Raised when the memory endpoint is unreachable or returns an error."""


def _endpoint() -> str:
    base = os.environ.get("L9_MEMORY_HTTP_URL", "").strip().rstrip("/")
    if not base:
        raise MemoryError("L9_MEMORY_HTTP_URL is not set")
    parsed = urllib.parse.urlparse(base)
    # Restrict the scheme before any network access: https everywhere, http only
    # for loopback dev. Blocks file:/ftp:/custom-scheme SSRF via a mis-set env.
    is_loopback = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    if parsed.scheme != "https" and not (parsed.scheme == "http" and is_loopback):
        raise MemoryError(f"refusing non-https memory endpoint scheme: {parsed.scheme!r}")
    return base + "/mcp"


def _token() -> str:
    token = os.environ.get("L9_MEMORY_CLIENT_TOKEN", "").strip()
    if not token:
        raise MemoryError("L9_MEMORY_CLIENT_TOKEN is not set")
    return token


def _parse_body(raw: bytes, content_type: str) -> dict[str, Any]:
    text = raw.decode("utf-8", errors="replace").strip()
    # The streamable-HTTP transport may answer as text/event-stream; take the
    # last JSON `data:` frame. Otherwise the body is a plain JSON-RPC object.
    if "text/event-stream" in content_type or text.startswith("event:"):
        payload = ""
        for line in text.splitlines():
            if line.startswith("data:"):
                payload = line[len("data:") :].strip()
        text = payload or text
    return json.loads(text)


def rpc(method: str, params: dict[str, Any] | None = None, *, timeout: float = 20.0) -> Any:
    """Issue one JSON-RPC call and return its `result`, raising on any error."""
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}).encode(
        "utf-8"
    )
    request = urllib.request.Request(
        _endpoint(),
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {_token()}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            parsed = _parse_body(response.read(), response.headers.get("Content-Type", ""))
    except urllib.error.HTTPError as exc:  # pragma: no cover - network dependent
        raise MemoryError(f"memory endpoint HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:  # pragma: no cover
        raise MemoryError(f"memory endpoint unreachable: {exc}") from exc
    if isinstance(parsed, dict) and parsed.get("error"):
        err = parsed["error"]
        raise MemoryError(f"memory rpc error {err.get('code')}: {err.get('message')}")
    return parsed.get("result") if isinstance(parsed, dict) else parsed


def tool_call(name: str, arguments: dict[str, Any] | None = None, *, timeout: float = 20.0) -> Any:
    """Call a `memory.*` tool and return its decoded structured payload."""
    result = rpc("tools/call", {"name": name, "arguments": arguments or {}}, timeout=timeout)
    if isinstance(result, dict) and result.get("isError"):
        raise MemoryError(f"memory tool {name} reported an error")
    content = (result or {}).get("content") if isinstance(result, dict) else None
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "")
                try:
                    return json.loads(text)
                except (json.JSONDecodeError, TypeError):
                    return {"text": text}
    return result


def health(*, timeout: float = 15.0) -> dict[str, Any]:
    return tool_call("memory.health", {}, timeout=timeout)


def search(query: str, namespaces: list[str], *, limit: int = 5) -> dict[str, Any]:
    return tool_call("memory.search", {"query": query, "namespaces": namespaces, "limit": limit})


def hydrate(task: str, namespaces: list[str], *, limit: int = 8) -> dict[str, Any]:
    return tool_call("memory.hydrate", {"task": task, "namespaces": namespaces, "limit": limit})


def conflicts(namespace: str) -> dict[str, Any]:
    return tool_call("memory.conflicts", {"namespace": namespace})


def phase_lock(namespace: str, task_signature: str, *, ttl_seconds: int = 3600) -> dict[str, Any]:
    return tool_call(
        "memory.phase_lock",
        {"namespace": namespace, "task_signature": task_signature, "ttl_seconds": ttl_seconds},
    )


def verify_phase_lock(namespace: str, task_signature: str) -> dict[str, Any]:
    return tool_call(
        "memory.verify_phase_lock",
        {"namespace": namespace, "task_signature": task_signature},
    )


def ingest(record: dict[str, Any]) -> dict[str, Any]:
    return tool_call("memory.ingest", record)

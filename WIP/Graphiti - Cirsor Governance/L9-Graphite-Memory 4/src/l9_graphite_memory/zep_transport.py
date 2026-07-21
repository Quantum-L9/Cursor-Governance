# L9_META
#   l9_schema: 1
#   repo: Quantum-L9/L9-Graphite-Memory
#   layer: transport
#   owner: platform
#   status: active
#   created: 2026-07-05
#   contract: ZepCloudTransport — MemoryTransport implementation via Zep Cloud SDK
"""
Zep Cloud transport implementation for L9-Graphite-Memory.

Uses the ``zep-python`` SDK to communicate with Zep Cloud's managed Graphiti
service. Reads ``ZEP_API_KEY`` from ``os.environ`` (injected by Infisical
Universal Auth via ``secrets.py``).

Mapping from legacy MCP tool names to Zep Cloud SDK methods:
  - search_facts / search_nodes → memory.search_sessions(search_scope="facts")
  - add_episode → memory.add(messages=[...])
  - get_episodes → memory.get_session_messages(session_id, limit=N)
  - healthcheck → client connectivity test

The ``group_id`` concept maps to Zep's ``session_id``. Each L9 group is a
distinct Zep session, enabling multi-tenant graph isolation.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

from .circuit_breaker import CircuitBreaker
from .rate_limiter import RateLimiter

__all__ = ["ZepCloudTransport"]

log = logging.getLogger("l9.graphite.transport.zep")


class ZepCloudTransport:
    """Zep Cloud SDK transport conforming to MemoryTransport protocol."""

    def __init__(self) -> None:
        api_key = os.environ.get("ZEP_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError(
                "ZEP_API_KEY not set. Ensure Infisical is configured or set the env var directly."
            )

        try:
            from zep_python.client import Zep
        except ImportError as exc:
            raise RuntimeError(
                "zep-python not installed. Install with: pip install l9-graphite-memory[zep]"
            ) from exc

        base_url = os.environ.get("ZEP_API_URL", "").strip() or None
        self._client = Zep(api_key=api_key, base_url=base_url)
        self._circuit = CircuitBreaker()
        self._rate = RateLimiter()
        log.info("ZepCloudTransport initialized (base_url=%s)", base_url or "default")

    def health(self) -> dict[str, Any]:
        """Check connectivity to Zep Cloud."""
        result: dict[str, Any] = {"transport": "zep_cloud", "healthy": False}
        try:
            # Attempt a lightweight operation to verify connectivity
            self._client.memory.list_sessions(page_size=1)
            result["healthy"] = True
            result["liveness_ok"] = True
            result["tool_plane_reachable"] = True
            self._circuit.record_success()
        except Exception as exc:  # noqa: BLE001
            self._circuit.record_failure()
            result["liveness_ok"] = False
            result["tool_plane_reachable"] = False
            result["error"] = str(exc)
        result["circuit"] = self._circuit.status()
        return result

    def search(self, query: str, group_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search facts in a Zep session (group_id maps to session_id)."""
        if not self._circuit.can_execute():
            raise RuntimeError("circuit breaker OPEN")
        try:
            response = self._client.memory.search_sessions(
                text=query,
                session_ids=[group_id],
                search_scope="facts",
                limit=limit,
            )
            self._circuit.record_success()
            results: list[dict[str, Any]] = []
            if response and response.results:
                for r in response.results:
                    fact_data: dict[str, Any] = {}
                    if hasattr(r, "fact") and r.fact:
                        fact_data = {
                            "uuid": getattr(r.fact, "uuid", None),
                            "body": getattr(r.fact, "body", ""),
                            "rating": getattr(r.fact, "rating", None),
                            "created_at": str(getattr(r.fact, "created_at", "")),
                        }
                    elif hasattr(r, "session_id"):
                        fact_data = {"session_id": r.session_id, "score": getattr(r, "score", None)}
                    results.append(fact_data)
            return results
        except Exception as exc:  # noqa: BLE001
            self._circuit.record_failure()
            log.warning("Zep search failed for session %s: %s", group_id, exc)
            raise RuntimeError(f"Zep search failed: {exc}") from exc

    def write(self, body: str, group_id: str, kind: str = "lesson", **kwargs: Any) -> dict[str, Any]:
        """Write an episode to Zep Cloud as a message in a session."""
        if not self._circuit.can_execute():
            raise RuntimeError("circuit breaker OPEN")
        if not self._rate.allow():
            raise RuntimeError("rate limit exceeded")

        from zep_python.types import Message

        try:
            # Ensure session exists
            self._ensure_session(group_id)

            # Map episode to Zep message format
            message = Message(
                role_type="system",
                role="l9-memory-cli",
                content=body,
                metadata={
                    "kind": kind,
                    "source": "l9-graphite-memory",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    **{k: v for k, v in kwargs.items() if isinstance(v, (str, int, float, bool))},
                },
            )

            result = self._client.memory.add(
                session_id=group_id,
                messages=[message],
            )
            self._circuit.record_success()
            self._rate.record()
            return {"written": True, "session_id": group_id, "status": str(result)}
        except Exception as exc:  # noqa: BLE001
            self._circuit.record_failure()
            log.error("Zep write failed for session %s: %s", group_id, exc)
            raise RuntimeError(f"Zep write failed: {exc}") from exc

    def call_tool(self, name: str, arguments: Optional[dict[str, Any]] = None) -> Any:
        """Map legacy MCP tool names to Zep SDK operations.

        This provides backward compatibility with the existing CLI commands
        that reference tool names from the self-hosted MCP server.
        """
        args = arguments or {}

        tool_map = {
            "search_facts": self._tool_search_facts,
            "search_nodes": self._tool_search_nodes,
            "add_episode": self._tool_add_episode,
            "get_episodes": self._tool_get_episodes,
        }

        handler = tool_map.get(name)
        if handler:
            return handler(args)

        log.warning("Unknown tool %s — attempting generic search fallback", name)
        return {"error": f"tool '{name}' not mapped to Zep SDK", "arguments": args}

    def list_tools(self) -> list[str]:
        """List available tool names (mapped from MCP conventions)."""
        return ["add_episode", "get_episodes", "search_facts", "search_nodes"]

    # --- Private tool handlers ---

    def _tool_search_facts(self, args: dict[str, Any]) -> dict[str, Any]:
        query = args.get("query", "")
        group_id = args.get("group_id", "")
        limit = args.get("max_facts", args.get("limit", 10))
        facts = self.search(query, group_id, limit=limit)
        return {"facts": facts}

    def _tool_search_nodes(self, args: dict[str, Any]) -> dict[str, Any]:
        query = args.get("query", "")
        group_id = args.get("group_id", "")
        limit = args.get("max_nodes", args.get("limit", 10))
        facts = self.search(query, group_id, limit=limit)
        return {"nodes": facts}

    def _tool_add_episode(self, args: dict[str, Any]) -> dict[str, Any]:
        body = args.get("body", args.get("episode_body", ""))
        group_id = args.get("group_id", "")
        kind = args.get("source_description", "episode")
        kwargs = {k: v for k, v in args.items() if k not in ("body", "episode_body", "group_id", "source_description")}
        return self.write(body, group_id, kind=kind, **kwargs)

    def _tool_get_episodes(self, args: dict[str, Any]) -> dict[str, Any]:
        group_id = args.get("group_id", "")
        last_n = args.get("last_n", 50)
        if not self._circuit.can_execute():
            raise RuntimeError("circuit breaker OPEN")
        try:
            response = self._client.memory.get_session_messages(
                session_id=group_id,
                limit=last_n,
            )
            self._circuit.record_success()
            messages = response.messages if response and response.messages else []
            episodes = [
                {
                    "uuid": getattr(m, "uuid", None),
                    "body": getattr(m, "content", ""),
                    "role": getattr(m, "role", ""),
                    "created_at": str(getattr(m, "created_at", "")),
                    "metadata": getattr(m, "metadata", {}),
                }
                for m in messages
            ]
            return {"episodes": episodes}
        except Exception as exc:  # noqa: BLE001
            self._circuit.record_failure()
            raise RuntimeError(f"Zep get_episodes failed: {exc}") from exc

    def _ensure_session(self, group_id: str) -> None:
        """Ensure a Zep session exists for the given group_id (idempotent)."""
        try:
            self._client.memory.get_session(session_id=group_id)
        except Exception:  # noqa: BLE001
            # Session doesn't exist — create it
            try:
                self._client.memory.add_session(
                    session_id=group_id,
                    metadata={"source": "l9-graphite-memory", "created_by": "cli"},
                )
                log.info("Created Zep session: %s", group_id)
            except Exception as exc:  # noqa: BLE001
                # Might be a race condition or already exists
                log.debug("Session creation for %s returned: %s", group_id, exc)

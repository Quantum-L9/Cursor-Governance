# L9_META
#   l9_schema: 1
#   repo: Quantum-L9/L9-Graphite-Memory
#   layer: tests
#   owner: platform
#   status: active
#   created: 2026-07-05
"""Tests for transport abstraction layer."""
from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from l9_graphite_memory.transport import (
    HttpMcpTransport,
    MemoryTransport,
    get_transport,
)


class TestMemoryTransportProtocol:
    """Verify that concrete transports satisfy the MemoryTransport protocol."""

    def test_http_transport_is_memory_transport(self) -> None:
        transport = HttpMcpTransport()
        assert isinstance(transport, MemoryTransport)

    def test_protocol_has_required_methods(self) -> None:
        required = {"health", "search", "write", "call_tool", "list_tools"}
        protocol_methods = {
            name for name in dir(MemoryTransport) if not name.startswith("_")
        }
        assert required.issubset(protocol_methods)


class TestHttpMcpTransport:
    """Unit tests for HttpMcpTransport."""

    def test_url_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GRAPHITI_MCP_URL", None)
            transport = HttpMcpTransport()
            assert "/mcp" in transport._url()

    def test_url_custom(self) -> None:
        with patch.dict(os.environ, {"GRAPHITI_MCP_URL": "https://my-server.com/api"}):
            transport = HttpMcpTransport()
            url = transport._url()
            assert url.endswith("/mcp/")

    def test_headers_no_token(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GRAPHITI_MCP_TOKEN", None)
            transport = HttpMcpTransport()
            headers = transport._headers()
            assert "Authorization" not in headers
            assert headers["Content-Type"] == "application/json"

    def test_headers_with_token(self) -> None:
        with patch.dict(os.environ, {"GRAPHITI_MCP_TOKEN": "test-token-123"}):
            transport = HttpMcpTransport()
            headers = transport._headers()
            assert headers["Authorization"] == "Bearer test-token-123"

    def test_circuit_breaker_blocks_after_failures(self) -> None:
        transport = HttpMcpTransport()
        # Simulate failures to open circuit
        for _ in range(transport._circuit.failure_threshold):
            transport._circuit.record_failure()
        assert transport._circuit.state == "OPEN"
        with pytest.raises(RuntimeError, match="circuit breaker OPEN"):
            transport._rpc("tools/list", {})

    def test_extract_facts_from_dict(self) -> None:
        data = {"facts": [{"uuid": "1", "body": "test"}]}
        result = HttpMcpTransport._extract_facts(data)
        assert len(result) == 1
        assert result[0]["uuid"] == "1"

    def test_extract_facts_from_list(self) -> None:
        data = [{"uuid": "1"}, {"uuid": "2"}]
        result = HttpMcpTransport._extract_facts(data)
        assert len(result) == 2

    def test_extract_facts_empty(self) -> None:
        assert HttpMcpTransport._extract_facts(None) == []
        assert HttpMcpTransport._extract_facts("string") == []

    def test_list_tools_returns_empty_on_failure(self) -> None:
        transport = HttpMcpTransport()
        # Without a running server, list_tools should gracefully return empty
        result = transport.list_tools()
        assert isinstance(result, list)


class TestGetTransport:
    """Tests for the transport factory function."""

    def test_default_is_zep_with_fallback(self) -> None:
        """Without ZEP_API_KEY, Zep init fails and falls back to HTTP."""
        with patch.dict(os.environ, {"GRAPHITI_TRANSPORT": "zep"}, clear=False):
            os.environ.pop("ZEP_API_KEY", None)
            transport = get_transport()
            assert isinstance(transport, HttpMcpTransport)

    def test_explicit_http(self) -> None:
        with patch.dict(os.environ, {"GRAPHITI_TRANSPORT": "http"}):
            transport = get_transport()
            assert isinstance(transport, HttpMcpTransport)

    def test_unknown_transport_falls_back(self) -> None:
        with patch.dict(os.environ, {"GRAPHITI_TRANSPORT": "unknown_backend"}):
            transport = get_transport()
            assert isinstance(transport, HttpMcpTransport)

    def test_zep_transport_with_api_key(self) -> None:
        """With ZEP_API_KEY set, should create ZepCloudTransport."""
        with patch.dict(os.environ, {"GRAPHITI_TRANSPORT": "zep", "ZEP_API_KEY": "z_test_key"}):
            transport = get_transport()
            # Should be ZepCloudTransport (imported dynamically)
            assert type(transport).__name__ == "ZepCloudTransport"


class TestZepCloudTransport:
    """Unit tests for ZepCloudTransport (mocked SDK)."""

    def test_init_requires_api_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ZEP_API_KEY", None)
            from l9_graphite_memory.zep_transport import ZepCloudTransport
            with pytest.raises(RuntimeError, match="ZEP_API_KEY not set"):
                ZepCloudTransport()

    def test_init_with_api_key(self) -> None:
        with patch.dict(os.environ, {"ZEP_API_KEY": "z_test_key_123"}):
            from l9_graphite_memory.zep_transport import ZepCloudTransport
            transport = ZepCloudTransport()
            assert isinstance(transport, MemoryTransport)

    def test_health_success(self) -> None:
        with patch.dict(os.environ, {"ZEP_API_KEY": "z_test"}):
            from l9_graphite_memory.zep_transport import ZepCloudTransport
            transport = ZepCloudTransport()
            transport._client = MagicMock()
            transport._client.memory.list_sessions.return_value = MagicMock()
            result = transport.health()
            assert result["healthy"] is True
            assert result["transport"] == "zep_cloud"

    def test_health_failure(self) -> None:
        with patch.dict(os.environ, {"ZEP_API_KEY": "z_test"}):
            from l9_graphite_memory.zep_transport import ZepCloudTransport
            transport = ZepCloudTransport()
            transport._client = MagicMock()
            transport._client.memory.list_sessions.side_effect = Exception("connection refused")
            result = transport.health()
            assert result["healthy"] is False
            assert "connection refused" in result["error"]

    def test_search_returns_facts(self) -> None:
        with patch.dict(os.environ, {"ZEP_API_KEY": "z_test"}):
            from l9_graphite_memory.zep_transport import ZepCloudTransport
            transport = ZepCloudTransport()
            transport._client = MagicMock()
            mock_fact = MagicMock()
            mock_fact.uuid = "fact-uuid-1"
            mock_fact.body = "test fact"
            mock_fact.rating = 0.9
            mock_fact.created_at = "2026-01-01"
            mock_result = MagicMock()
            mock_result.fact = mock_fact
            mock_response = MagicMock()
            mock_response.results = [mock_result]
            transport._client.memory.search_sessions.return_value = mock_response
            results = transport.search("test query", "group-1", limit=5)
            assert len(results) == 1
            assert results[0]["uuid"] == "fact-uuid-1"

    def test_write_calls_add(self) -> None:
        with patch.dict(os.environ, {"ZEP_API_KEY": "z_test"}):
            from l9_graphite_memory.zep_transport import ZepCloudTransport
            transport = ZepCloudTransport()
            transport._client = MagicMock()
            transport._client.memory.get_session.return_value = MagicMock()
            transport._client.memory.add.return_value = MagicMock()
            result = transport.write("test body", "group-1", kind="lesson")
            assert result["written"] is True
            transport._client.memory.add.assert_called_once()

    def test_call_tool_search_facts(self) -> None:
        with patch.dict(os.environ, {"ZEP_API_KEY": "z_test"}):
            from l9_graphite_memory.zep_transport import ZepCloudTransport
            transport = ZepCloudTransport()
            transport._client = MagicMock()
            mock_response = MagicMock()
            mock_response.results = []
            transport._client.memory.search_sessions.return_value = mock_response
            result = transport.call_tool("search_facts", {"query": "test", "group_id": "g1", "max_facts": 5})
            assert "facts" in result

    def test_call_tool_unknown(self) -> None:
        with patch.dict(os.environ, {"ZEP_API_KEY": "z_test"}):
            from l9_graphite_memory.zep_transport import ZepCloudTransport
            transport = ZepCloudTransport()
            result = transport.call_tool("nonexistent_tool", {})
            assert "error" in result

    def test_list_tools(self) -> None:
        with patch.dict(os.environ, {"ZEP_API_KEY": "z_test"}):
            from l9_graphite_memory.zep_transport import ZepCloudTransport
            transport = ZepCloudTransport()
            tools = transport.list_tools()
            assert "add_episode" in tools
            assert "search_facts" in tools

    def test_circuit_breaker_opens_on_repeated_failures(self) -> None:
        with patch.dict(os.environ, {"ZEP_API_KEY": "z_test"}):
            from l9_graphite_memory.zep_transport import ZepCloudTransport
            transport = ZepCloudTransport()
            transport._client = MagicMock()
            transport._client.memory.search_sessions.side_effect = Exception("fail")
            # Exhaust circuit breaker
            for _ in range(transport._circuit.failure_threshold):
                try:
                    transport.search("q", "g", limit=1)
                except RuntimeError:
                    pass
            # Next call should be blocked by circuit breaker
            with pytest.raises(RuntimeError, match="circuit breaker OPEN"):
                transport.search("q", "g", limit=1)

#!/usr/bin/env python3
"""Contract tests for the Manus streamable-HTTP governance MCP service."""

from __future__ import annotations

import http.client
import importlib.util
import json
import sys
import threading
import unittest
import unittest.mock as mock
from pathlib import Path

ADAPTER = Path(__file__).resolve().parents[1]
REPOSITORY = ADAPTER.parents[3]
SERVER_PATH = ADAPTER / "mcp_server.py"

spec = importlib.util.spec_from_file_location("manus_mcp_server", SERVER_PATH)
assert spec is not None and spec.loader is not None
mcp_server = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mcp_server
spec.loader.exec_module(mcp_server)


class ManusMcpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = mcp_server.GovernanceMcpService(REPOSITORY)

    def test_initialize_and_tool_inventory_follow_streamable_mcp(self) -> None:
        initialized = self.service.handle_rpc(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-03-26"},
            }
        )
        self.assertIsNotNone(initialized)
        assert initialized is not None
        self.assertEqual(initialized["result"]["protocolVersion"], "2025-03-26")
        self.assertEqual(initialized["result"]["serverInfo"]["name"], "l9-governance")

        listed = self.service.handle_rpc(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        )
        self.assertIsNotNone(listed)
        assert listed is not None
        tool_names = {tool["name"] for tool in listed["result"]["tools"]}
        self.assertEqual(
            tool_names,
            {
                "governance_bootstrap",
                "governance_list_skills",
                "governance_read",
                "governance_search",
                "governance_status",
                "governance_validate",
            },
        )

    def test_read_and_search_are_bounded_to_governance_policy_paths(self) -> None:
        read = self.service.call_tool(
            "governance_read", {"path": "CANONICAL_LAW.md", "end_line": 5}
        )
        payload = read["structuredContent"]
        self.assertEqual(payload["path"], "CANONICAL_LAW.md")
        self.assertIn("L9_META", payload["content"])

        search = self.service.call_tool(
            "governance_search", {"query": "thin adapter", "max_results": 3}
        )
        self.assertFalse(search.get("isError", False))
        self.assertLessEqual(len(search["structuredContent"]["matches"]), 3)

        blocked = self.service.call_tool(
            "governance_read", {"path": "ops/secrets/openclaw-igorbot.registry.yaml"}
        )
        self.assertTrue(blocked["isError"])
        self.assertIn("allowlist", blocked["structuredContent"]["error"])

    def test_status_and_validation_use_existing_adapter_contract(self) -> None:
        status = self.service.call_tool("governance_status", {})
        self.assertFalse(status.get("isError", False))
        self.assertEqual(status["structuredContent"]["manus_adapter"]["status"], "ready")
        self.assertEqual(
            status["structuredContent"]["manus_adapter"]["memory"]["lifecycle"], "disabled"
        )

        validation = self.service.call_tool("governance_validate", {"mode": "manus"})
        self.assertTrue(validation.get("isError", False))
        self.assertIn("bearer-protected", validation["structuredContent"]["error"])

        protected = mcp_server.GovernanceMcpService(REPOSITORY, bootstrap_enabled=True)
        allowed = protected.call_tool("governance_validate", {"mode": "manus"})
        self.assertFalse(allowed.get("isError", False))
        self.assertEqual(allowed["structuredContent"]["status"], "passed")

    def test_lifecycle_tools_require_explicit_protected_service_mode(self) -> None:
        protected = mcp_server.GovernanceMcpService(REPOSITORY, memory_lifecycle_enabled=True)
        names = {tool["name"] for tool in protected.tools()}
        self.assertTrue(
            {
                "memory_lifecycle_status",
                "memory_lifecycle_start",
                "memory_lifecycle_close",
            }.issubset(names)
        )
        status = protected.call_tool("memory_lifecycle_status", {})
        self.assertFalse(status.get("isError", False))
        payload = status["structuredContent"]
        self.assertEqual(payload["transport"], "memory-control-plane/v1")
        self.assertIn(payload["status"], {"ready", "blocked"})

        refused = self.service.call_tool("memory_lifecycle_start", {})
        self.assertTrue(refused.get("isError", False))
        self.assertIn("bearer-protected", refused["structuredContent"]["error"])

    def test_lifecycle_start_refuses_unsigned_agent_fallback_before_memory_io(self) -> None:
        protected = mcp_server.GovernanceMcpService(REPOSITORY, memory_lifecycle_enabled=True)
        with mock.patch.dict(
            "os.environ",
            {
                "L9_MEMORY_AGENT_ID": "manus",
                "USER_ID": "manus_agent",
                "L9_MEMORY_SOURCE": "manus",
            },
            clear=True,
        ):
            result = protected.call_tool(
                "memory_lifecycle_start",
                {
                    "workspace": str(REPOSITORY),
                    "task": "exercise lifecycle guard",
                    "session_id": "manus-test-session",
                },
            )
        self.assertTrue(result.get("isError", False))
        self.assertIn("signed agent door", result["structuredContent"]["error"])

    def test_bootstrap_requires_a_real_git_workspace(self) -> None:
        result = self.service.call_tool(
            "governance_bootstrap", {"workspace": "/tmp", "mode": "check"}
        )
        self.assertTrue(result["isError"])
        self.assertIn("Git work tree", result["structuredContent"]["error"])

    def test_bootstrap_requires_a_bearer_protected_deployment(self) -> None:
        result = self.service.call_tool(
            "governance_bootstrap",
            {"workspace": str(REPOSITORY), "mode": "check"},
        )
        self.assertTrue(result["isError"])
        self.assertIn("bearer-protected MCP deployment", result["structuredContent"]["error"])

    def test_workspace_status_requires_a_bearer_protected_deployment(self) -> None:
        result = self.service.call_tool("governance_status", {"workspace": str(REPOSITORY)})
        self.assertTrue(result["isError"])
        self.assertIn("bearer-protected MCP deployment", result["structuredContent"]["error"])

    def test_http_transport_rejects_non_json_content_type(self) -> None:
        server = mcp_server.GovernanceMcpHttpServer(("127.0.0.1", 0), self.service, "")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            connection = http.client.HTTPConnection(
                "127.0.0.1", server.server_address[1], timeout=2
            )
            connection.request("POST", "/mcp", body="{}", headers={"Content-Type": "text/plain"})
            response = connection.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
            self.assertEqual(response.status, 415)
            self.assertEqual(payload["error"], "Content-Type must be application/json")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_notifications_have_no_json_rpc_response(self) -> None:
        self.assertIsNone(
            self.service.handle_rpc(
                {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
            )
        )

    def test_connector_renderer_requires_clean_https_mcp_endpoint(self) -> None:
        renderer_path = ADAPTER / "render_mcp_connector.py"
        renderer_spec = importlib.util.spec_from_file_location("manus_mcp_renderer", renderer_path)
        assert renderer_spec is not None and renderer_spec.loader is not None
        renderer = importlib.util.module_from_spec(renderer_spec)
        sys.modules[renderer_spec.name] = renderer
        renderer_spec.loader.exec_module(renderer)
        self.assertEqual(
            renderer.validate_endpoint("https://governance.example.com/mcp"),
            "https://governance.example.com/mcp",
        )
        with self.assertRaises(ValueError):
            renderer.validate_endpoint("http://governance.example.com/mcp")
        with self.assertRaises(ValueError):
            renderer.validate_endpoint("https://token@example.com/mcp")
        draft = renderer.draft("https://governance.example.com/mcp")
        self.assertEqual(draft["mode"], "form")
        self.assertEqual(set(draft), {"mode", "mcpServers"})
        self.assertEqual(
            json.loads(json.dumps(draft))["mcpServers"]["l9-governance"]["url"],
            "https://governance.example.com/mcp",
        )
        protected = renderer.draft("https://governance.example.com/mcp", bearer_token="test-token")
        self.assertEqual(
            protected["mcpServers"]["l9-governance"]["headers"],
            {"Authorization": "Bearer test-token"},
        )


if __name__ == "__main__":
    unittest.main()

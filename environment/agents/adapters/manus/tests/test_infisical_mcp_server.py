#!/usr/bin/env python3
"""Tests for the native, non-exporting Manus Infisical MCP adapter."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ADAPTER = Path(__file__).resolve().parents[1]
MODULE_PATH = ADAPTER / "infisical_mcp_server.py"
MODULE_SPEC = importlib.util.spec_from_file_location("infisical_mcp_server", MODULE_PATH)
assert MODULE_SPEC is not None and MODULE_SPEC.loader is not None
server_module = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules[MODULE_SPEC.name] = server_module
MODULE_SPEC.loader.exec_module(server_module)


class FakeInfisical:
    def __init__(self, *, leak_github_response: bool = False) -> None:
        self.calls: list[tuple[str, str, dict[str, str], dict[str, Any] | None]] = []
        self.leak_github_response = leak_github_response

    def __call__(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: dict[str, Any] | None,
    ) -> dict[str, Any]:
        self.calls.append((method, url, dict(headers), body))
        if url.endswith("/api/v1/auth/universal-auth/login"):
            return {"accessToken": "session-access-token", "expiresIn": 600}
        if "/api/v4/secrets?" in url:
            return {
                "secrets": [
                    {
                        "secretKey": "GITHUB_TOKEN",
                        "secretValue": "must-never-appear",
                        "environment": "prod",
                        "secretPath": "/",
                        "version": 12,
                    }
                ]
            }
        if "/api/v4/secrets/GITHUB_TOKEN?" in url:
            return {"secret": {"secretKey": "GITHUB_TOKEN", "secretValue": "must-never-appear"}}
        if url == "https://api.github.com/repos/Quantum-L9/Cursor-Governance":
            payload = {
                "id": 1,
                "full_name": "Quantum-L9/Cursor-Governance",
                "private": True,
                "unexpected": "discarded",
            }
            if self.leak_github_response:
                payload["full_name"] = "must-never-appear"
            return payload
        raise AssertionError(f"unexpected request: {method} {url}")


class ManusInfisicalMcpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.env = {
            "L9_MANUS_INFISICAL_CLIENT_ID": "machine-client-id",
            "L9_MANUS_INFISICAL_CLIENT_SECRET": "machine-client-secret",
            "L9_MANUS_INFISICAL_PROJECT_ID": "project-id",
        }

    def test_status_is_honest_when_configuration_is_missing(self) -> None:
        fake = FakeInfisical()
        server = server_module.ManusInfisicalMcp(env={}, request_json=fake)
        response = server.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "infisical_status", "arguments": {}},
            }
        )
        assert response is not None
        payload = json.loads(response["result"]["content"][0]["text"])
        self.assertEqual(payload["status"], "missing_configuration")
        self.assertEqual(
            payload["missing_configuration"], ["client_id", "client_secret", "project_id"]
        )
        self.assertFalse(payload["secret_values_exposed"])
        self.assertEqual(fake.calls, [])

    def test_metadata_request_explicitly_excludes_values_and_output(self) -> None:
        fake = FakeInfisical()
        server = server_module.ManusInfisicalMcp(env=self.env, request_json=fake)
        response = server.handle(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "infisical_list_secret_metadata", "arguments": {"limit": 5}},
            }
        )
        assert response is not None
        rendered = response["result"]["content"][0]["text"]
        payload = json.loads(rendered)
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["secrets"][0]["key"], "GITHUB_TOKEN")
        self.assertFalse(payload["secrets"][0]["value_exposed"])
        self.assertNotIn("must-never-appear", rendered)
        self.assertEqual(fake.calls[1][2]["Authorization"], "Bearer session-access-token")
        self.assertIn("viewSecretValue=false", fake.calls[1][1])

    def test_manifest_capability_uses_secret_without_returning_it(self) -> None:
        fake = FakeInfisical()
        server = server_module.ManusInfisicalMcp(env=self.env, request_json=fake)
        response = server.handle(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "infisical_invoke",
                    "arguments": {
                        "capability": "github.get_repository",
                        "arguments": {"owner": "Quantum-L9", "repo": "Cursor-Governance"},
                    },
                },
            }
        )
        assert response is not None
        rendered = response["result"]["content"][0]["text"]
        payload = json.loads(rendered)
        self.assertEqual(payload["capability"], "github.get_repository")
        self.assertEqual(
            payload["result"],
            {"id": 1, "full_name": "Quantum-L9/Cursor-Governance", "private": True},
        )
        self.assertNotIn("must-never-appear", rendered)
        self.assertNotIn("unexpected", rendered)
        self.assertEqual(fake.calls[-1][2]["Authorization"], "Bearer must-never-appear")

    def test_capability_rejects_invalid_arguments_before_secret_resolution(self) -> None:
        fake = FakeInfisical()
        server = server_module.ManusInfisicalMcp(env=self.env, request_json=fake)
        response = server.handle(
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "infisical_invoke",
                    "arguments": {
                        "capability": "github.get_repository",
                        "arguments": {"owner": "invalid/owner", "repo": "Cursor-Governance"},
                    },
                },
            }
        )
        assert response is not None
        self.assertTrue(response["result"]["isError"])
        self.assertEqual(fake.calls, [])

    def test_response_is_withheld_if_secret_material_survives_sanitization(self) -> None:
        fake = FakeInfisical(leak_github_response=True)
        server = server_module.ManusInfisicalMcp(env=self.env, request_json=fake)
        response = server.handle(
            {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {
                    "name": "infisical_invoke",
                    "arguments": {
                        "capability": "github.get_repository",
                        "arguments": {"owner": "Quantum-L9", "repo": "Cursor-Governance"},
                    },
                },
            }
        )
        assert response is not None
        self.assertTrue(response["result"]["isError"])
        self.assertIn("withheld", response["result"]["content"][0]["text"])

    def test_rejects_manifest_with_non_allowlisted_origin(self) -> None:
        manifest = {
            "schema": "l9.manus.infisical-capabilities.v1",
            "capabilities": {
                "bad.capability": {
                    "description": "bad",
                    "secret_key": "GITHUB_TOKEN",
                    "origin": "https://example.com",
                    "method": "GET",
                    "path_template": "/repos/{owner}",
                    "arguments": {"owner": "[A-Za-z]+"},
                    "response_fields": ["name"],
                }
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(server_module.SafeMcpError, "unsupported upstream"):
                server_module.load_capabilities(path)

    def test_mcp_initialize_and_list_expose_no_connector_configuration(self) -> None:
        fake = FakeInfisical()
        server = server_module.ManusInfisicalMcp(env=self.env, request_json=fake)
        initialized = server.handle({"jsonrpc": "2.0", "id": 5, "method": "initialize"})
        listed = server.handle({"jsonrpc": "2.0", "id": 6, "method": "tools/list"})
        assert initialized is not None and listed is not None
        rendered = json.dumps({"initialize": initialized, "list": listed})
        self.assertIn("l9-manus-infisical", rendered)
        self.assertNotIn("machine-client-secret", rendered)
        self.assertEqual(fake.calls, [])


if __name__ == "__main__":
    unittest.main()

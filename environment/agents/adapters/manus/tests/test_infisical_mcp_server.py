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


class InfisicalObservedReadinessTests(unittest.TestCase):
    """Synthetic API outcomes prove consumer logic, never live Infisical access."""

    ENV = {
        "L9_MANUS_INFISICAL_CLIENT_ID": "fixture-client-id",
        "L9_MANUS_INFISICAL_CLIENT_SECRET": "fixture-bootstrap-secret",
        "L9_MANUS_INFISICAL_PROJECT_ID": "fixture-project-id",
    }

    def test_configured_is_not_authenticated_and_status_never_logs_in(self) -> None:
        fake = FakeInfisical()
        server = server_module.ManusInfisicalMcp(env=self.ENV, request_json=fake)
        status = server.client.status(server.capabilities)
        self.assertEqual(status["status"], "configured")
        self.assertEqual(status["authentication"], "unverified")
        self.assertEqual(status["scope_access"], "unverified")
        self.assertEqual(fake.calls, [])
        server.client.list_metadata(1)
        status = server.client.status(server.capabilities)
        self.assertEqual(status["authentication"], "authenticated")
        self.assertEqual(status["scope_access"], "verified")

    def test_explicit_empty_env_cannot_borrow_process_credentials(self) -> None:
        from unittest.mock import patch

        with patch.dict("os.environ", self.ENV, clear=True):
            server = server_module.ManusInfisicalMcp(env={}, request_json=FakeInfisical())
        self.assertEqual(
            server.client.status(server.capabilities)["status"], "missing_configuration"
        )

    def test_invalid_config_never_reads_as_configured_or_sends_credentials(self) -> None:
        for extra in (
            {"L9_MANUS_INFISICAL_CLIENT_SECRET": "__ENCRYPTED_FAKE__"},
            {"L9_MANUS_INFISICAL_CLIENT_SECRET": "proxy-injected"},
            {"L9_MANUS_INFISICAL_SITE_URL": "https://untrusted.invalid"},
        ):
            with self.subTest(extra=extra):
                fake = FakeInfisical()
                server = server_module.ManusInfisicalMcp(
                    env={**self.ENV, **extra}, request_json=fake
                )
                self.assertEqual(
                    server.client.status(server.capabilities)["status"], "invalid_configuration"
                )
                with self.assertRaises(server_module.SafeMcpError):
                    server.client.list_metadata(1)
                self.assertEqual(fake.calls, [])

    def test_each_401_names_only_the_failing_stage(self) -> None:
        stages = (
            "universal_auth_login",
            "secret_metadata",
            "capability_secret_resolution",
            "capability_upstream",
        )
        for stage in stages:
            with self.subTest(stage=stage):
                fake = FakeInfisical()

                def requester(method, url, headers, body):
                    actual = (
                        "universal_auth_login"
                        if url.endswith("/login")
                        else "capability_upstream"
                        if url.startswith("https://api.github.com")
                        else "capability_secret_resolution"
                        if "/secrets/GITHUB_TOKEN?" in url
                        else "secret_metadata"
                    )
                    if actual == stage:
                        raise server_module.SafeMcpError(
                            "fixture-bootstrap-secret session-access-token must-never-appear",
                            http_status=401,
                        )
                    return fake(method, url, headers, body)

                server = server_module.ManusInfisicalMcp(env=self.ENV, request_json=requester)
                name = (
                    "infisical_list_secret_metadata" if stage in stages[:2] else "infisical_invoke"
                )
                arguments = (
                    {"limit": 1}
                    if name.endswith("metadata")
                    else {
                        "capability": "github.get_repository",
                        "arguments": {"owner": "Quantum-L9", "repo": "Cursor-Governance"},
                    }
                )
                response = server.handle(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/call",
                        "params": {"name": name, "arguments": arguments},
                    }
                )
                rendered = response["result"]["content"][0]["text"]
                self.assertTrue(response["result"]["isError"])
                self.assertIn(f"{stage} failed with HTTP 401", rendered)
                for secret in (
                    "fixture-bootstrap-secret",
                    "session-access-token",
                    "must-never-appear",
                ):
                    self.assertNotIn(secret, rendered)
                status = server.client.status(server.capabilities)
                if stage == "capability_upstream":
                    self.assertEqual(status["authentication"], "authenticated")
                    self.assertEqual(status["scope_access"], "verified")
                else:
                    self.assertEqual(status["authentication"], "refused")
                    self.assertEqual(server.client._access_token, "")

    def test_cached_token_rejected_by_metadata_is_cleared_without_silent_retry(self) -> None:
        fake = FakeInfisical()
        server = server_module.ManusInfisicalMcp(env=self.ENV, request_json=fake)
        server.client.list_metadata(1)
        calls = []

        def refused(method, url, headers, body):
            calls.append(url)
            raise server_module.SafeMcpError("do-not-echo", http_status=401)

        server.client._request_json = refused
        with self.assertRaisesRegex(
            server_module.SafeMcpError, "secret_metadata failed with HTTP 401"
        ):
            server.client.list_metadata(1)
        self.assertEqual(len(calls), 1)
        self.assertEqual(server.client._access_token, "")
        self.assertEqual(server.client.status(server.capabilities)["authentication"], "refused")

    def test_invalid_expiry_is_never_assigned_an_invented_lifetime(self) -> None:
        for expiry in (None, False, True, "invalid", -1, 0, float("nan"), float("inf")):
            with self.subTest(expiry=expiry):
                server = server_module.ManusInfisicalMcp(
                    env=self.ENV,
                    request_json=lambda *args: {
                        "accessToken": "fixture-token",
                        "expiresIn": expiry,
                    },
                )
                with self.assertRaisesRegex(
                    server_module.SafeMcpError, "unverified token lifetime"
                ):
                    server.client._token()
                self.assertEqual(server.client._access_token, "")
                self.assertEqual(
                    server.client.status(server.capabilities)["authentication"], "unverified"
                )

    def test_short_token_never_outlives_issued_expiry_and_status_is_observational(self) -> None:
        from unittest.mock import patch

        fake = FakeInfisical()

        def requester(method, url, headers, body):
            if url.endswith("/login"):
                return {"accessToken": "session-access-token", "expiresIn": 2}
            return fake(method, url, headers, body)

        server = server_module.ManusInfisicalMcp(env=self.ENV, request_json=requester)
        with patch.object(server_module.time, "monotonic", return_value=100.0):
            server.client.list_metadata(1)
        self.assertLessEqual(server.client._access_token_expires_at, 102.0)
        count = len(fake.calls)
        with patch.object(server_module.time, "monotonic", return_value=102.0):
            status = server.client.status(server.capabilities)
        self.assertEqual(status["authentication"], "expired")
        self.assertEqual(status["scope_access"], "unverified")
        self.assertEqual(server.client._access_token, "")
        self.assertEqual(count, len(fake.calls))

    def test_metadata_echo_of_bootstrap_or_access_token_is_withheld(self) -> None:
        for secret in ("fixture-bootstrap-secret", "session-access-token"):
            with self.subTest(secret=secret):
                fake = FakeInfisical()

                def requester(method, url, headers, body):
                    if "/api/v4/secrets?" in url:
                        return {"secrets": [{"secretKey": "GITHUB_TOKEN", "environment": secret}]}
                    return fake(method, url, headers, body)

                server = server_module.ManusInfisicalMcp(env=self.ENV, request_json=requester)
                with self.assertRaisesRegex(server_module.SafeMcpError, "response was withheld"):
                    server.client.list_metadata(1)
                self.assertNotEqual(
                    server.client.status(server.capabilities)["scope_access"], "verified"
                )

    def test_login_round_trip_is_subtracted_from_issued_lifetime(self) -> None:
        from unittest.mock import patch

        server = server_module.ManusInfisicalMcp(
            env=self.ENV,
            request_json=lambda *args: {"accessToken": "fixture-token", "expiresIn": 10},
        )
        with patch.object(server_module.time, "monotonic", side_effect=[100.0, 104.0]):
            self.assertEqual(server.client._token(), "fixture-token")
        self.assertLessEqual(server.client._access_token_expires_at, 110.0)
        self.assertEqual(server.client._access_token_expires_at, 109.0)

    def test_already_expired_login_response_is_not_cached_or_used(self) -> None:
        from unittest.mock import patch

        fake = FakeInfisical()

        def requester(method, url, headers, body):
            if url.endswith("/login"):
                return {"accessToken": "fixture-token", "expiresIn": 2}
            return fake(method, url, headers, body)

        server = server_module.ManusInfisicalMcp(env=self.ENV, request_json=requester)
        with patch.object(server_module.time, "monotonic", side_effect=[100.0, 104.0]):
            with self.assertRaisesRegex(server_module.SafeMcpError, "already-expired token"):
                server.client.list_metadata(1)
        self.assertEqual(server.client._access_token, "")
        self.assertEqual(server.client.status(server.capabilities)["authentication"], "expired")
        self.assertEqual(fake.calls, [])

    def test_escaped_credential_echo_is_withheld_before_json_serialization(self) -> None:
        for secret in ('quoted"secret', "backslash\\secret", "control\nsecret", "unicode-秘密"):
            for channel in ("metadata", "capability"):
                with self.subTest(secret=secret, channel=channel):
                    fake = FakeInfisical()

                    def requester(method, url, headers, body):
                        if channel == "metadata" and "/api/v4/secrets?" in url:
                            return {
                                "secrets": [{"secretKey": "GITHUB_TOKEN", "environment": secret}]
                            }
                        if channel == "capability" and "/secrets/GITHUB_TOKEN?" in url:
                            return {"secret": {"secretKey": "GITHUB_TOKEN", "secretValue": secret}}
                        if channel == "capability" and url.startswith("https://api.github.com"):
                            return {"full_name": {"nested": ["prefix-" + secret + "-suffix"]}}
                        return fake(method, url, headers, body)

                    server = server_module.ManusInfisicalMcp(
                        env={**self.ENV, "L9_MANUS_INFISICAL_CLIENT_SECRET": secret},
                        request_json=requester,
                    )
                    name = (
                        "infisical_list_secret_metadata"
                        if channel == "metadata"
                        else "infisical_invoke"
                    )
                    arguments = (
                        {"limit": 1}
                        if channel == "metadata"
                        else {
                            "capability": "github.get_repository",
                            "arguments": {"owner": "Quantum-L9", "repo": "Cursor-Governance"},
                        }
                    )
                    response = server.handle(
                        {
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "tools/call",
                            "params": {"name": name, "arguments": arguments},
                        }
                    )
                    result = response["result"]
                    self.assertTrue(result["isError"])
                    self.assertEqual(
                        json.loads(result["content"][0]["text"]),
                        {"error": "response was withheld because it contained credential material"},
                    )


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Native Manus MCP lane for approved Infisical-backed capabilities.

The server reads its Universal Auth machine-identity fields from the Custom MCP
connector process environment. It never exposes those fields, the issued access
token, or any resolved secret value through MCP, stdout logging, files, or a
child process. Instead, callers can inspect secret *metadata* and invoke a
small manifest-defined capability whose upstream and response shape are fixed.

This is intentionally a Manus-only adapter component. It does not depend on or
invoke the Cursor SessionStart secret bootstrap.
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from string import Formatter
from typing import Any

ADAPTER_ROOT = Path(__file__).resolve().parent
DEFAULT_CAPABILITIES_PATH = ADAPTER_ROOT / "infisical_capabilities.json"
MAX_HTTP_RESPONSE_BYTES = 1_048_576
MAX_METADATA_RESULTS = 100
GITHUB_API_ORIGIN = "https://api.github.com"

JsonRequester = Callable[[str, str, Mapping[str, str], dict[str, Any] | None], dict[str, Any]]


class SafeMcpError(Exception):
    """An error safe to return to a model-controlled MCP caller."""

    def __init__(self, message: str, *, http_status: int | None = None) -> None:
        super().__init__(message)
        self.http_status = http_status


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse redirects so an Authorization header cannot cross origins."""

    def redirect_request(
        self,
        request: urllib.request.Request,
        file_pointer: Any,
        status_code: int,
        message: str,
        headers: Any,
        redirected_url: str,
    ) -> urllib.request.Request | None:
        raise urllib.error.HTTPError(
            request.full_url,
            status_code,
            "redirect refused for credential-bearing request",
            headers,
            file_pointer,
        )


@dataclass(frozen=True)
class InfisicalSettings:
    """Connector-only configuration. Secret-bearing fields are never repr'd."""

    client_id: str = ""
    client_secret: str = field(default="", repr=False)
    project_id: str = ""
    environment: str = "prod"
    secret_path: str = "/"
    site_url: str = "https://app.infisical.com"

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> InfisicalSettings:
        return cls(
            client_id=(env.get("L9_MANUS_INFISICAL_CLIENT_ID") or "").strip(),
            client_secret=(env.get("L9_MANUS_INFISICAL_CLIENT_SECRET") or "").strip(),
            project_id=(env.get("L9_MANUS_INFISICAL_PROJECT_ID") or "").strip(),
            environment=(env.get("L9_MANUS_INFISICAL_ENV") or "prod").strip() or "prod",
            secret_path=(env.get("L9_MANUS_INFISICAL_SECRET_PATH") or "/").strip() or "/",
            site_url=(env.get("L9_MANUS_INFISICAL_SITE_URL") or "https://app.infisical.com")
            .strip()
            .rstrip("/"),
        )

    @property
    def missing_fields(self) -> tuple[str, ...]:
        fields = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "project_id": self.project_id,
        }
        return tuple(name for name, value in fields.items() if not value)

    @property
    def configured(self) -> bool:
        return not self.missing_fields

    def validate(self) -> None:
        try:
            parsed = urllib.parse.urlsplit(self.site_url)
            port = parsed.port
        except ValueError as exc:
            raise SafeMcpError("Infisical site URL must be a valid HTTPS origin") from exc
        if parsed.scheme != "https" or not parsed.netloc or parsed.path not in {"", "/"}:
            raise SafeMcpError("Infisical site URL must be an HTTPS origin")
        if parsed.hostname != "app.infisical.com" or port not in {None, 443}:
            raise SafeMcpError("Infisical site URL must use the canonical HTTPS host")
        if parsed.query or parsed.fragment or parsed.username or parsed.password:
            raise SafeMcpError(
                "Infisical site URL must not include credentials, query, or fragment"
            )
        if not self.secret_path.startswith("/"):
            raise SafeMcpError("Infisical secret path must start with '/'")
        for value in (self.client_id, self.client_secret, self.project_id):
            if value == "proxy-injected" or value.startswith("__ENCRYPTED_"):
                raise SafeMcpError("Infisical credential placeholders are not usable configuration")


@dataclass(frozen=True)
class Capability:
    """A fixed outbound operation authorized by the adapter-owned manifest."""

    identifier: str
    description: str
    secret_key: str
    origin: str
    method: str
    path_template: str
    arguments: dict[str, str]
    response_fields: tuple[str, ...]

    def validate(self) -> None:
        parsed = urllib.parse.urlsplit(self.origin)
        if parsed.scheme != "https" or parsed.netloc != "api.github.com":
            raise SafeMcpError(f"capability '{self.identifier}' uses an unsupported upstream")
        if parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password:
            raise SafeMcpError(
                f"capability '{self.identifier}' origin must be a clean HTTPS origin"
            )
        if self.method != "GET":
            raise SafeMcpError(f"capability '{self.identifier}' must use GET")
        if self.secret_key != "GITHUB_TOKEN":
            raise SafeMcpError(
                f"capability '{self.identifier}' uses an unsupported secret reference"
            )
        if not self.path_template.startswith("/") or "?" in self.path_template:
            raise SafeMcpError(f"capability '{self.identifier}' has an invalid path template")
        fields = {
            field_name
            for _, field_name, _, _ in Formatter().parse(self.path_template)
            if field_name is not None
        }
        if fields != set(self.arguments):
            raise SafeMcpError(
                f"capability '{self.identifier}' path parameters must match declared arguments"
            )
        if not self.response_fields:
            raise SafeMcpError(f"capability '{self.identifier}' must declare response fields")

    def render_path(self, values: Mapping[str, Any]) -> str:
        if set(values) != set(self.arguments):
            expected = ", ".join(sorted(self.arguments))
            raise SafeMcpError(f"capability '{self.identifier}' requires exactly: {expected}")
        clean: dict[str, str] = {}
        for name, pattern in self.arguments.items():
            value = values.get(name)
            if not isinstance(value, str) or not re.fullmatch(pattern, value):
                raise SafeMcpError(f"invalid capability argument: {name}")
            clean[name] = urllib.parse.quote(value, safe="")
        return self.path_template.format(**clean)


def load_capabilities(path: Path = DEFAULT_CAPABILITIES_PATH) -> dict[str, Capability]:
    """Load and validate the bounded, committed capability manifest."""

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SafeMcpError("capability manifest is unavailable") from exc
    if not isinstance(raw, dict) or raw.get("schema") != "l9.manus.infisical-capabilities.v1":
        raise SafeMcpError("capability manifest has an unsupported schema")
    entries = raw.get("capabilities")
    if not isinstance(entries, dict) or not entries:
        raise SafeMcpError("capability manifest defines no capabilities")

    capabilities: dict[str, Capability] = {}
    for identifier, item in entries.items():
        if not isinstance(identifier, str) or not re.fullmatch(
            r"[a-z][a-z0-9_.-]{2,80}", identifier
        ):
            raise SafeMcpError("capability manifest contains an invalid identifier")
        if not isinstance(item, dict):
            raise SafeMcpError(f"capability '{identifier}' is not an object")
        arguments = item.get("arguments")
        response_fields = item.get("response_fields")
        if not isinstance(arguments, dict) or not all(
            isinstance(name, str) and isinstance(pattern, str)
            for name, pattern in arguments.items()
        ):
            raise SafeMcpError(f"capability '{identifier}' has invalid arguments")
        if not isinstance(response_fields, list) or not all(
            isinstance(name, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name)
            for name in response_fields
        ):
            raise SafeMcpError(f"capability '{identifier}' has invalid response fields")
        capability = Capability(
            identifier=identifier,
            description=str(item.get("description") or ""),
            secret_key=str(item.get("secret_key") or ""),
            origin=str(item.get("origin") or ""),
            method=str(item.get("method") or ""),
            path_template=str(item.get("path_template") or ""),
            arguments={str(name): str(pattern) for name, pattern in arguments.items()},
            response_fields=tuple(response_fields),
        )
        capability.validate()
        capabilities[identifier] = capability
    return capabilities


def _request_json(
    method: str,
    url: str,
    headers: Mapping[str, str],
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Perform one bounded HTTPS JSON request without emitting request data."""

    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise SafeMcpError("refusing a non-HTTPS outbound request")
    body_bytes = json.dumps(body).encode("utf-8") if body is not None else None
    request_headers = {"Accept": "application/json", **dict(headers)}
    if body_bytes is not None:
        request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body_bytes, method=method, headers=request_headers)
    try:
        opener = urllib.request.build_opener(_NoRedirect())
        with opener.open(request, timeout=20) as response:  # noqa: S310
            raw = response.read(MAX_HTTP_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raise SafeMcpError(
            f"upstream request failed with HTTP {exc.code}", http_status=exc.code
        ) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise SafeMcpError(f"upstream request failed: {type(exc).__name__}") from exc
    if len(raw) > MAX_HTTP_RESPONSE_BYTES:
        raise SafeMcpError("upstream response exceeded the safe size limit")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SafeMcpError("upstream returned malformed JSON") from exc
    if not isinstance(payload, dict):
        raise SafeMcpError("upstream returned an unsupported JSON shape")
    return payload


class InfisicalClient:
    """Token and secret use remain internal to this connector process."""

    def __init__(
        self, settings: InfisicalSettings, request_json: JsonRequester = _request_json
    ) -> None:
        self.settings = settings
        self._request_json = request_json
        self._access_token = ""
        self._access_token_expires_at = 0.0
        self._authentication = "unverified"
        self._scope_access = "unverified"

    def _expire_token(self) -> None:
        if self._access_token and time.monotonic() >= self._access_token_expires_at:
            self._access_token = ""
            self._access_token_expires_at = 0.0
            self._authentication = "expired"
            self._scope_access = "unverified"

    def _request_stage(
        self,
        stage: str,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Retain the failing stage/code, never an upstream body or exception text."""
        try:
            return self._request_json(method, url, headers, body)
        except SafeMcpError as exc:
            code = exc.http_status
            suffix = f" with HTTP {code}" if code is not None else ""
            raise SafeMcpError(f"{stage} failed{suffix}", http_status=code) from exc

    def _safe_payload(self, payload: dict[str, Any], *values: str) -> dict[str, Any]:
        protected = (self.settings.client_secret, self._access_token, *values)

        def contains_credential(value: Any) -> bool:
            # Inspect decoded strings, including keys: JSON escaping must not
            # turn a recoverable credential into an apparently safe response.
            if isinstance(value, str):
                return any(secret and secret in value for secret in protected)
            if isinstance(value, Mapping):
                return any(
                    contains_credential(key) or contains_credential(nested)
                    for key, nested in value.items()
                )
            if isinstance(value, (list, tuple)):
                return any(contains_credential(nested) for nested in value)
            return False

        if contains_credential(payload):
            raise SafeMcpError("response was withheld because it contained credential material")
        return payload

    def status(self, capabilities: Mapping[str, Capability]) -> dict[str, Any]:
        """Return only configuration posture and declared capability identifiers."""

        self._expire_token()
        configuration = "configured" if self.settings.configured else "missing_configuration"
        if self.settings.configured:
            try:
                self.settings.validate()
            except (SafeMcpError, ValueError):
                configuration = "invalid_configuration"
        return {
            "status": configuration,
            "authentication": self._authentication,
            "scope_access": self._scope_access,
            "missing_configuration": list(self.settings.missing_fields),
            "capabilities": sorted(capabilities),
            "secret_values_exposed": False,
        }

    def _token(self) -> str:
        if not self.settings.configured:
            missing = ", ".join(self.settings.missing_fields)
            raise SafeMcpError(f"Infisical connector is not configured: {missing}")
        self.settings.validate()
        self._expire_token()
        if self._access_token and time.monotonic() < self._access_token_expires_at:
            return self._access_token
        login_started_at = time.monotonic()
        try:
            payload = self._request_stage(
                "universal_auth_login",
                "POST",
                f"{self.settings.site_url}/api/v1/auth/universal-auth/login",
                {},
                {"clientId": self.settings.client_id, "clientSecret": self.settings.client_secret},
            )
        except SafeMcpError:
            self._authentication = "refused"
            self._scope_access = "unverified"
            raise
        token = payload.get("accessToken")
        expires_in = payload.get("expiresIn")
        if not isinstance(token, str) or not token:
            self._authentication = "refused"
            raise SafeMcpError("Infisical login did not return an access token")
        try:
            ttl = float(expires_in)
        except (TypeError, ValueError):
            ttl = 0.0
        if isinstance(expires_in, bool) or not math.isfinite(ttl) or ttl <= 0:
            self._authentication = "unverified"
            raise SafeMcpError("universal_auth_login returned an unverified token lifetime")
        ttl = min(ttl, 3600.0)
        # The response arrives after issuance. Starting the clock on receipt
        # would add network/processing delay to the server-issued lifetime.
        expires_at = login_started_at + ttl - min(30.0, ttl * 0.1)
        if time.monotonic() >= expires_at:
            self._authentication = "expired"
            self._scope_access = "unverified"
            raise SafeMcpError("universal_auth_login returned an already-expired token")
        self._access_token = token
        self._access_token_expires_at = expires_at
        self._authentication = "authenticated"
        return token

    def _infisical_get(self, stage: str, path: str, query: Mapping[str, str]) -> dict[str, Any]:
        token = self._token()
        url = f"{self.settings.site_url}{path}?{urllib.parse.urlencode(query)}"
        try:
            return self._request_stage(stage, "GET", url, {"Authorization": f"Bearer {token}"})
        except SafeMcpError as exc:
            self._scope_access = "refused"
            if exc.http_status == 401:
                self._access_token = ""
                self._access_token_expires_at = 0.0
                self._authentication = "refused"
            raise

    def list_metadata(self, limit: int) -> dict[str, Any]:
        """List bounded secret metadata while asking Infisical not to return values."""

        if not 1 <= limit <= MAX_METADATA_RESULTS:
            raise SafeMcpError(f"limit must be between 1 and {MAX_METADATA_RESULTS}")
        payload = self._infisical_get(
            "secret_metadata",
            "/api/v4/secrets",
            {
                "projectId": self.settings.project_id,
                "environment": self.settings.environment,
                "secretPath": self.settings.secret_path,
                "viewSecretValue": "false",
                "expandSecretReferences": "false",
                "includeImports": "false",
                "recursive": "false",
            },
        )
        secrets = payload.get("secrets")
        if not isinstance(secrets, list):
            raise SafeMcpError("Infisical metadata response had no secrets list")
        results: list[dict[str, Any]] = []
        for item in secrets[:limit]:
            if not isinstance(item, dict):
                continue
            key = item.get("secretKey")
            if not isinstance(key, str) or not key:
                continue
            results.append(
                {
                    "key": key,
                    "environment": str(item.get("environment") or self.settings.environment),
                    "path": str(item.get("secretPath") or self.settings.secret_path),
                    "version": item.get("version"),
                    "value_exposed": False,
                }
            )
        response = self._safe_payload({"count": len(results), "secrets": results})
        self._scope_access = "verified"
        return response

    def _resolve_secret(self, name: str) -> str:
        payload = self._infisical_get(
            "capability_secret_resolution",
            f"/api/v4/secrets/{urllib.parse.quote(name, safe='')}",
            {
                "projectId": self.settings.project_id,
                "environment": self.settings.environment,
                "secretPath": self.settings.secret_path,
                "viewSecretValue": "true",
                "expandSecretReferences": "false",
                "includeImports": "false",
            },
        )
        secret = payload.get("secret")
        value = secret.get("secretValue") if isinstance(secret, dict) else None
        if not isinstance(value, str) or not value:
            raise SafeMcpError("configured capability secret is unavailable")
        self._scope_access = "verified"
        return value

    def invoke(self, capability: Capability, arguments: Mapping[str, Any]) -> dict[str, Any]:
        """Use one manifest-approved secret internally for one fixed upstream call."""

        path = capability.render_path(arguments)
        secret_value = self._resolve_secret(capability.secret_key)
        payload = self._request_stage(
            "capability_upstream",
            capability.method,
            f"{capability.origin}{path}",
            {
                "Authorization": f"Bearer {secret_value}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            None,
        )
        sanitized = {
            field: payload.get(field) for field in capability.response_fields if field in payload
        }
        return self._safe_payload(
            {"capability": capability.identifier, "result": sanitized}, secret_value
        )


def _tool_result(payload: dict[str, Any], *, is_error: bool = False) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": json.dumps(payload, sort_keys=True)}],
        "isError": is_error,
    }


class ManusInfisicalMcp:
    """Small MCP JSON-RPC server that owns no tool capable of returning a secret."""

    def __init__(
        self,
        env: Mapping[str, str] | None = None,
        request_json: JsonRequester = _request_json,
        capabilities_path: Path = DEFAULT_CAPABILITIES_PATH,
    ) -> None:
        self.capabilities = load_capabilities(capabilities_path)
        source = os.environ if env is None else env
        self.client = InfisicalClient(InfisicalSettings.from_env(source), request_json)

    def _tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "infisical_status",
                "description": (
                    "Report whether this native Manus Infisical connector is configured "
                    "and list its "
                    "approved capabilities. It never authenticates or returns secret material."
                ),
                "inputSchema": {"type": "object", "additionalProperties": False, "properties": {}},
            },
            {
                "name": "infisical_list_secret_metadata",
                "description": (
                    "List bounded Infisical secret names and metadata for the configured scope. "
                    "Secret values are explicitly excluded from the request and response."
                ),
                "inputSchema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "limit": {"type": "integer", "minimum": 1, "maximum": MAX_METADATA_RESULTS}
                    },
                },
            },
            {
                "name": "infisical_invoke",
                "description": (
                    "Execute one manifest-defined capability using its configured Infisical secret "
                    "inside this connector. The credential is never returned."
                ),
                "inputSchema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "capability": {"type": "string", "enum": sorted(self.capabilities)},
                        "arguments": {"type": "object"},
                    },
                    "required": ["capability", "arguments"],
                },
            },
        ]

    def handle(self, request: Mapping[str, Any]) -> dict[str, Any] | None:
        request_id = request.get("id")
        method = request.get("method")
        if not isinstance(method, str):
            return self._error(request_id, -32600, "request method must be a string")
        if method == "notifications/initialized":
            return None
        if method == "initialize":
            return self._result(
                request_id,
                {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "l9-manus-infisical", "version": "1.0.0"},
                },
            )
        if method == "ping":
            return self._result(request_id, {})
        if method == "tools/list":
            return self._result(request_id, {"tools": self._tools()})
        if method == "tools/call":
            return self._call_tool(request_id, request.get("params"))
        return self._error(request_id, -32601, f"method not found: {method}")

    def _call_tool(self, request_id: Any, params: Any) -> dict[str, Any]:
        if not isinstance(params, dict):
            return self._error(request_id, -32602, "tools/call params must be an object")
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(name, str) or not isinstance(arguments, dict):
            return self._error(request_id, -32602, "tool name and arguments are required")
        try:
            if name == "infisical_status":
                if arguments:
                    raise SafeMcpError("infisical_status accepts no arguments")
                response = _tool_result(self.client.status(self.capabilities))
            elif name == "infisical_list_secret_metadata":
                if set(arguments) - {"limit"}:
                    raise SafeMcpError("infisical_list_secret_metadata accepts only limit")
                limit = arguments.get("limit", 20)
                if not isinstance(limit, int) or isinstance(limit, bool):
                    raise SafeMcpError("limit must be an integer")
                response = _tool_result(self.client.list_metadata(limit))
            elif name == "infisical_invoke":
                if set(arguments) != {"capability", "arguments"}:
                    raise SafeMcpError("infisical_invoke requires capability and arguments")
                identifier = arguments.get("capability")
                supplied = arguments.get("arguments")
                if not isinstance(identifier, str) or not isinstance(supplied, dict):
                    raise SafeMcpError("invalid capability invocation")
                capability = self.capabilities.get(identifier)
                if capability is None:
                    raise SafeMcpError("unknown capability")
                response = _tool_result(self.client.invoke(capability, supplied))
            else:
                raise SafeMcpError("unknown tool")
        except SafeMcpError as exc:
            response = _tool_result({"error": str(exc)}, is_error=True)
        return self._result(request_id, response)

    @staticmethod
    def _result(request_id: Any, result: Any) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    @staticmethod
    def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def serve_stdio() -> int:
    """Serve line-delimited JSON-RPC without diagnostic output on stdout."""

    try:
        server = ManusInfisicalMcp()
    except SafeMcpError as exc:
        print(f"l9-manus-infisical: configuration error: {exc}", file=sys.stderr)
        return 1
    for line in sys.stdin:
        try:
            request = json.loads(line)
            if not isinstance(request, dict):
                raise ValueError("request must be an object")
            response = server.handle(request)
        except (json.JSONDecodeError, ValueError):
            response = ManusInfisicalMcp._error(None, -32700, "parse error")
        if response is not None:
            sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(serve_stdio())

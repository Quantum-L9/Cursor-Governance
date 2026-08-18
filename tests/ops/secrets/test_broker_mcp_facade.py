"""MCP facade tests for the L9 capability broker.

The facade is what lets Claude Code ``.mcp.json`` servers point at the broker
while the Graphiti bearer stays beyond the trust boundary. These tests drive
``_Handler.do_POST`` directly (no sockets, no network, no real credentials)
and cover the JSON-RPC handshake, the bounded memory tool mapping, the honest
401 for sessions without a verifiable platform identity, and the route
properties that keep the broker a no-secret-read service.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SECRETS_DIR = REPO_ROOT / "ops" / "secrets"
if str(SECRETS_DIR) not in sys.path:
    sys.path.insert(0, str(SECRETS_DIR))

try:
    import capability_broker as cb  # noqa: E402
except ImportError as exc:
    # Isolate UV_PROJECT can bind a sibling checkout whose cryptography wheel
    # does not load (macOS ABI). CI and a healthy local .venv still import.
    pytest.skip(f"capability broker imports unavailable: {exc}", allow_module_level=True)


class StubBroker:
    """Records capability invocations; authentication is toggleable."""

    def __init__(self, authenticated: bool = True) -> None:
        self.authenticated = authenticated
        self.calls: list[dict[str, Any]] = []

    def authenticate(self, authorization: str | None):
        if not self.authenticated or not authorization:
            raise cb.BrokerError(401, "missing session assertion")
        return {"session_id": "s-test", "org_id": "o-test"}

    def handle(self, claims: Any, body: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(body)
        return {"capability": body["capability"], "result": {"ok": True}}


def make_handler(
    stub: StubBroker,
    path: str,
    body: dict[str, Any] | None,
    headers: dict[str, str] | None = None,
) -> cb._Handler:
    handler = cb._Handler.__new__(cb._Handler)
    handler.path = path
    handler.headers = dict(headers or {})
    raw = json.dumps(body).encode("utf-8") if body is not None else b""
    handler.headers["Content-Length"] = str(len(raw))
    handler.rfile = io.BytesIO(raw)  # type: ignore[assignment]
    handler.wfile = io.BytesIO()  # type: ignore[assignment]
    handler.broker = stub  # type: ignore[assignment]
    handler.request_version = "HTTP/1.1"
    handler.requestline = f"POST {path} HTTP/1.1"
    handler.client_address = ("127.0.0.1", 1)  # type: ignore[assignment]
    handler.server = None  # type: ignore[assignment]
    return handler


def post(
    stub: StubBroker,
    path: str,
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, Any] | None]:
    handler = make_handler(stub, path, body, headers)
    handler.do_POST()
    raw = handler.wfile.getvalue().decode("utf-8")  # type: ignore[union-attr]
    status = int(raw.split(" ", 2)[1])
    payload_part = raw.split("\r\n\r\n", 1)
    payload = None
    if len(payload_part) == 2 and payload_part[1].strip():
        payload = json.loads(payload_part[1])
    return status, payload


def rpc(method: str, params: dict[str, Any] | None = None, request_id: Any = 1) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}


# --- handshake ---------------------------------------------------------------


def test_initialize_answers_without_identity() -> None:
    status, payload = post(StubBroker(), "/mcp/graphiti", rpc("initialize", {}, 1))
    assert status == 200
    assert payload["jsonrpc"] == "2.0"
    assert payload["result"]["serverInfo"]["name"] == "l9-capability-broker"
    assert "tools" in payload["result"]["capabilities"]


def test_ping_and_notifications() -> None:
    status, payload = post(StubBroker(), "/mcp/graphiti", rpc("ping", {}, 2))
    assert status == 200
    assert payload["result"] == {}
    status, _ = post(StubBroker(), "/mcp/graphiti", {"jsonrpc": "2.0", "method": "notifications/initialized"})
    assert status == 202


def test_unknown_method_is_jsonrpc_error() -> None:
    status, payload = post(
        StubBroker(),
        "/mcp/graphiti",
        rpc("tools/explode", {}, 3),
        headers={"Authorization": "Bearer s.jwt"},
    )
    assert status == 200
    assert payload["error"]["code"] == -32601


def test_malformed_body_is_parse_error() -> None:
    handler = make_handler(StubBroker(), "/mcp/graphiti", None)
    handler.rfile = io.BytesIO(b"{not json")  # type: ignore[assignment]
    handler.headers["Content-Length"] = str(len(b"{not json"))
    handler.do_POST()
    raw = handler.wfile.getvalue().decode("utf-8")  # type: ignore[union-attr]
    assert " " in raw and int(raw.split(" ", 2)[1]) == 200
    payload = json.loads(raw.split("\r\n\r\n", 1)[1])
    assert payload["id"] is None
    assert payload["error"]["code"] == -32700


# --- tools/list + tools/call on /mcp/graphiti ---------------------------------


def test_graphiti_tools_list() -> None:
    stub = StubBroker()
    status, payload = post(
        stub, "/mcp/graphiti", rpc("tools/list"), headers={"Authorization": "Bearer s.jwt"}
    )
    assert status == 200
    names = {t["name"] for t in payload["result"]["tools"]}
    assert names == {"search_memory", "write_governed"}


def test_search_memory_maps_to_graphiti_query() -> None:
    stub = StubBroker()
    status, payload = post(
        stub,
        "/mcp/graphiti",
        rpc("tools/call", {"name": "search_memory", "arguments": {"query": "phase lock"}}),
        headers={"Authorization": "Bearer s.jwt"},
    )
    assert status == 200
    assert payload["result"]["content"][0]["type"] == "text"
    assert stub.calls[0] == {
        "capability": "graphiti.query",
        "params": {"query": "phase lock"},
    }


def test_write_governed_maps_to_graphiti_write() -> None:
    stub = StubBroker()
    post(
        stub,
        "/mcp/graphiti",
        rpc("tools/call", {"name": "write_governed", "arguments": {"episode": "fact"}}),
        headers={"Authorization": "Bearer s.jwt"},
    )
    assert stub.calls[0] == {
        "capability": "graphiti.write_governed",
        "params": {"episode": "fact"},
    }


def test_unknown_tool_on_graphiti_is_refused() -> None:
    stub = StubBroker()
    status, payload = post(
        stub,
        "/mcp/graphiti",
        rpc("tools/call", {"name": "drop_all", "arguments": {}}),
        headers={"Authorization": "Bearer s.jwt"},
    )
    assert status == 200
    assert payload["error"]["code"] == -32602
    assert stub.calls == []


# --- honest 401 without platform identity -------------------------------------


def test_tools_list_without_identity_is_401() -> None:
    status, payload = post(StubBroker(), "/mcp/graphiti", rpc("tools/list"))
    assert status == 401
    assert payload["error"] == "missing session assertion"


def test_tools_call_without_identity_is_401() -> None:
    stub = StubBroker()
    status, payload = post(
        stub, "/mcp/graphiti", rpc("tools/call", {"name": "search_memory", "arguments": {}})
    )
    assert status == 401
    assert stub.calls == []


# --- header form /mcp ----------------------------------------------------------


def test_header_form_invoke_uses_x_capability_id() -> None:
    stub = StubBroker()
    status, payload = post(
        stub,
        "/mcp",
        rpc("tools/call", {"name": "invoke", "arguments": {"repo": "r"}}),
        headers={"X-Capability-Id": "github.pr_read", "Authorization": "Bearer s.jwt"},
    )
    assert status == 200
    assert stub.calls[0] == {
        "capability": "github.pr_read",
        "params": {"repo": "r"},
    }


def test_header_form_requires_capability_header() -> None:
    stub = StubBroker()
    status, payload = post(
        stub,
        "/mcp",
        rpc("tools/call", {"name": "invoke", "arguments": {}}),
        headers={"Authorization": "Bearer s.jwt"},
    )
    assert status == 200
    assert payload["error"]["code"] == -32602
    assert stub.calls == []


# --- route properties -----------------------------------------------------------


def test_no_secret_read_route_exists() -> None:
    source = (SECRETS_DIR / "capability_broker.py").read_text(encoding="utf-8")
    for route in ("/secret/", "/resolve-secret", "/print-secret"):
        assert f'self.path == "{route}"' not in source
    assert 'self.path == "/healthz"' in source


def test_unknown_path_segment_is_404() -> None:
    status, payload = post(
        StubBroker(), "/mcp/other", rpc("tools/list"), headers={"Authorization": "Bearer s.jwt"}
    )
    assert status == 200  # JSON-RPC envelope carries the refusal
    assert payload["error"]["code"] == 404

"""Opt-in stdio-to-remote Memory bridge. Synthetic keys only."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import StringIO
from pathlib import Path
from typing import Any

import pytest

from ops.memory.agent_assertion import identity_assertion_hmac, seal_identity_assertion
from ops.memory.remote_stdio_bridge import (
    STDIO_PROTOCOL_VERSION,
    AssertionSigner,
    BridgeFailure,
    HttpResponse,
    MemoryHttpTransport,
    http_protocol_for,
    prepare,
    serve,
)

CURSOR_KEY = "cursor-durable-signing-key-0123456789"
CLAUDE_KEY = "claude-durable-signing-key-0123456789"
KEYS = {"cursor": CURSOR_KEY, "claude-code": CLAUDE_KEY}
GRANTS = {
    "cursor": {"read": {"shared", "cursor-only"}, "write": {"shared", "cursor-only"}},
    "claude-code": {"read": {"shared"}, "write": set()},
}


def _assertion(agent_id: str) -> dict[str, Any]:
    return seal_identity_assertion(
        {
            "schema": "l9.identity-assertion/v1",
            "subject_ref": agent_id,
            "result": "resolved",
        }
    )


def _signer(agent_id: str, *, ttl_seconds: int = 3600) -> AssertionSigner:
    return AssertionSigner(agent_id, KEYS[agent_id], _assertion(agent_id), ttl_seconds=ttl_seconds)


def _env(agent_id: str, **extra: str) -> dict[str, str]:
    base = {"L9_MEMORY_REMOTE_STDIO": "1", "L9_MEMORY_REMOTE_URL": "http://127.0.0.1:9/mcp"}
    if agent_id == "cursor":
        base["CURSOR_AGENT"] = "1"
    else:
        base["CLAUDECODE"] = "1"
    base.update(extra)
    return base


class _Scripted:
    def __init__(self, responses: list[HttpResponse]) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[dict[str, Any], str | None]] = []

    def exchange(self, message: dict[str, Any], *, protocol_version: str | None) -> HttpResponse:
        self.calls.append((message, protocol_version))
        return self.responses.pop(0)


def _serve(lines: list[str], transport: _Scripted) -> list[dict[str, Any]]:
    stdout = StringIO()
    serve(lines, stdout, transport)  # type: ignore[arg-type]
    text = stdout.getvalue().strip()
    if not text:
        return []
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _result(protocol: str = "2025-11-25", *, request_id: Any = 1, **extra: Any) -> HttpResponse:
    body = {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {"protocolVersion": protocol, **extra},
    }
    return HttpResponse(200, "application/json", json.dumps(body).encode())


def test_stdio_initialize_converts_the_protocol_and_preserves_ids() -> None:
    transport = _Scripted(
        [
            _result(capabilities={"tools": {}}, serverInfo={"name": "memory"}),
            HttpResponse(
                200,
                "application/json",
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": "tools-7",
                        "result": {"tools": [{"name": "memory.health"}]},
                    }
                ).encode(),
            ),
            HttpResponse(202, "application/json", b""),
        ]
    )
    lines = [
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": STDIO_PROTOCOL_VERSION,
                    "clientInfo": {"name": "test"},
                },
            }
        ),
        json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
        json.dumps({"jsonrpc": "2.0", "id": "tools-7", "method": "tools/list", "params": {}}),
    ]
    # notification is between initialize and tools/list; reorder to match scripted responses
    lines = [lines[0], lines[2], lines[1]]
    replies = _serve(lines, transport)
    outbound, header = transport.calls[0]
    assert header is None
    assert outbound["params"]["protocolVersion"] == "2025-11-25"
    assert outbound["id"] == 1
    assert replies[0]["result"]["protocolVersion"] == STDIO_PROTOCOL_VERSION
    assert replies[0]["result"]["serverInfo"]["name"] == "memory"
    assert replies[0]["id"] == 1
    assert "error" not in replies[0]
    listed, list_header = transport.calls[1]
    assert list_header == "2025-11-25"
    assert listed["id"] == "tools-7"
    assert replies[1]["id"] == "tools-7"
    assert replies[1]["result"]["tools"][0]["name"] == "memory.health"
    assert transport.calls[2][1] == "2025-11-25"
    assert len(replies) == 2


def test_unknown_client_protocol_is_not_forwarded() -> None:
    transport = _Scripted([])
    replies = _serve(
        [
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "initialize",
                    "params": {"protocolVersion": "2026-07-28"},
                }
            )
        ],
        transport,
    )
    assert transport.calls == []
    assert replies[0]["id"] == 4
    assert "result" not in replies[0]
    assert replies[0]["error"]["data"]["failure_kind"] == "protocol"


def test_server_protocol_outside_the_http_set_is_a_contract_mismatch() -> None:
    transport = _Scripted([_result("2024-11-05", request_id=5)])
    replies = _serve(
        [
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 5,
                    "method": "initialize",
                    "params": {"protocolVersion": STDIO_PROTOCOL_VERSION},
                }
            )
        ],
        transport,
    )
    assert "result" not in replies[0]
    assert replies[0]["error"]["data"]["failure_kind"] == "contract_mismatch"


def test_tools_before_initialize_makes_no_request() -> None:
    transport = _Scripted([])
    replies = _serve(
        [json.dumps({"jsonrpc": "2.0", "id": 9, "method": "tools/list", "params": {}})],
        transport,
    )
    assert transport.calls == []
    assert replies[0]["error"]["data"]["failure_kind"] == "protocol"


def test_authentication_denial_keeps_the_id_and_is_not_a_result() -> None:
    body = {"jsonrpc": "2.0", "error": {"code": -32001, "message": "invalid token"}}
    transport = _Scripted(
        [
            _result(),
            HttpResponse(401, "application/json", json.dumps(body).encode()),
        ]
    )
    replies = _serve(
        [
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {"protocolVersion": STDIO_PROTOCOL_VERSION},
                }
            ),
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": "write-1",
                    "method": "tools/call",
                    "params": {"name": "memory.write", "arguments": {"namespace": "shared"}},
                }
            ),
        ],
        transport,
    )
    denial = replies[1]
    assert denial["id"] == "write-1"
    assert denial["error"]["code"] == -32001
    assert "result" not in denial


def test_malformed_line_and_redirect_are_explicit_failures() -> None:
    transport = _Scripted([_result(), HttpResponse(302, "text/plain", b"")])
    replies = _serve(
        [
            "{",
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {"protocolVersion": STDIO_PROTOCOL_VERSION},
                }
            ),
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}),
        ],
        transport,
    )
    assert replies[0]["error"]["data"]["failure_kind"] == "malformed"
    assert replies[2]["id"] == 2
    assert replies[2]["error"]["data"]["failure_kind"] == "protocol"
    assert "redirect refused" in replies[2]["error"]["message"]


def test_bridge_source_does_not_open_a_local_store() -> None:
    import ast

    root = Path(__file__).resolve().parents[3]
    tree = ast.parse((root / "ops/memory/remote_stdio_bridge.py").read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert "sqlite3" not in imported
    assert "ops.memory.store_compat" not in imported
    assert "l9_graphite_memory.server" not in imported


def test_prepare_refuses_a_missing_url_and_an_ephemeral_hosted_key(tmp_path: Path) -> None:
    without_url = _env("cursor")
    without_url.pop("L9_MEMORY_REMOTE_URL")
    with pytest.raises(BridgeFailure, match="not a fallback") as missing:
        prepare(without_url)
    assert missing.value.kind == "configuration"
    secret = tmp_path / "keys.json"
    secret.write_text(json.dumps({"agent_signing_keys": KEYS}), encoding="utf-8")
    hosted = _env(
        "claude-code",
        CLAUDE_CODE_REMOTE="true",
        CLAUDE_CODE_ENTRYPOINT="remote_mobile",
    )
    with pytest.raises(BridgeFailure, match="ephemeral hosted"):
        prepare(hosted, identity_assertion=_assertion("claude-code"))
    transport = prepare(
        {**hosted, "L9_MEMORY_REMOTE_SECRET_MAP": str(secret)},
        identity_assertion=_assertion("claude-code"),
    )
    assert transport.signer.agent_id == "claude-code"


def test_opt_in_off_does_not_build_a_transport() -> None:
    with pytest.raises(BridgeFailure, match="opt-in only"):
        prepare({"CURSOR_AGENT": "1", "L9_MEMORY_REMOTE_URL": "http://127.0.0.1:9/mcp"})


def test_http_versions_pass_through_and_stdio_does_not() -> None:
    assert http_protocol_for(STDIO_PROTOCOL_VERSION) == ("2025-11-25", STDIO_PROTOCOL_VERSION)
    assert http_protocol_for("2025-06-18") == ("2025-06-18", "2025-06-18")
    with pytest.raises(BridgeFailure):
        http_protocol_for("2025-03-26")


class _Recorder(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        server = self.server
        assert isinstance(server, _MemoryServer)
        record = {
            "path": self.path,
            "headers": {key.lower(): value for key, value in self.headers.items()},
            "body": raw,
        }
        server.records.append(record)
        status, payload = server.answer(record)
        encoded = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(status)
        if encoded:
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Connection", "close")
        self.end_headers()
        if encoded:
            self.wfile.write(encoded)

    def log_message(self, fmt: str, *args: Any) -> None:
        return


class _MemoryServer(ThreadingHTTPServer):
    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), _Recorder)
        self.records: list[dict[str, Any]] = []
        self.store: dict[str, list[str]] = {}

    def answer(self, record: dict[str, Any]) -> tuple[int, Any]:
        if record["path"].rstrip("/") != "/mcp":
            return 404, {"jsonrpc": "2.0", "error": {"code": -32600, "message": "not mcp"}}
        message = json.loads(record["body"])
        agent = _authenticated_agent(record["headers"])
        if agent is None:
            return 401, {"jsonrpc": "2.0", "error": {"code": -32001, "message": "invalid token"}}
        method = message.get("method")
        if method == "initialize":
            if "mcp-protocol-version" in record["headers"]:
                return 400, {
                    "jsonrpc": "2.0",
                    "id": message.get("id"),
                    "error": {
                        "code": -32600,
                        "message": "protocol header is not sent on initialize",
                    },
                }
            version = message["params"]["protocolVersion"]
            if version not in {"2025-11-25", "2025-06-18"}:
                return 400, {
                    "jsonrpc": "2.0",
                    "id": message.get("id"),
                    "error": {"code": -32600, "message": "unsupported protocol"},
                }
            return 200, {
                "jsonrpc": "2.0",
                "id": message["id"],
                "result": {
                    "protocolVersion": version,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "memory-3.0-fixture"},
                },
            }
        header = record["headers"].get("mcp-protocol-version")
        if header not in {"2025-11-25", "2025-06-18"}:
            return 400, {
                "jsonrpc": "2.0",
                "error": {"code": -32600, "message": "unsupported MCP-Protocol-Version"},
            }
        if method == "notifications/initialized":
            return 202, b""
        if method == "tools/list":
            return 200, {
                "jsonrpc": "2.0",
                "id": message["id"],
                "result": {"tools": [{"name": "memory.health"}, {"name": "memory.write"}]},
            }
        if method == "tools/call":
            return self._call(agent, message)
        return 200, {
            "jsonrpc": "2.0",
            "id": message.get("id"),
            "error": {"code": -32601, "message": "unknown method"},
        }

    def _call(self, agent: str, message: dict[str, Any]) -> tuple[int, Any]:
        arguments = message.get("params", {}).get("arguments") or {}
        name = message.get("params", {}).get("name")
        namespace = str(arguments.get("namespace", ""))
        if name == "memory.health":
            return 200, {
                "jsonrpc": "2.0",
                "id": message["id"],
                "result": {"content": [{"type": "text", "text": "ok"}], "isError": False},
            }
        grant = GRANTS[agent]
        if name == "memory.write":
            if namespace not in grant["write"]:
                return 200, {
                    "jsonrpc": "2.0",
                    "id": message["id"],
                    "error": {
                        "code": -32010,
                        "message": "namespace is not granted",
                        "data": {"type": "AuthorizationError"},
                    },
                }
            self.store.setdefault(namespace, []).append(str(arguments.get("content", "")))
            return 200, {
                "jsonrpc": "2.0",
                "id": message["id"],
                "result": {"content": [{"type": "text", "text": "written"}], "isError": False},
            }
        if name == "memory.read":
            if namespace not in grant["read"]:
                return 403, {"jsonrpc": "2.0", "error": {"code": -32010, "message": "ungranted"}}
            found = self.store.get(namespace, [])
            return 200, {
                "jsonrpc": "2.0",
                "id": message["id"],
                "result": {
                    "content": [{"type": "text", "text": json.dumps(found)}],
                    "isError": False,
                },
            }
        return 200, {
            "jsonrpc": "2.0",
            "id": message["id"],
            "error": {"code": -32601, "message": "unknown tool"},
        }


def _authenticated_agent(headers: dict[str, str]) -> str | None:
    authorization = headers.get("authorization", "")
    if not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    parts = token.split(".")
    if len(parts) != 4 or parts[0] not in KEYS:
        return None
    agent, exp, nonce, signature = parts
    payload = f"{agent}|{exp}|{nonce}".encode()
    expected = hmac.new(KEYS[agent].encode(), payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return None
    encoded = headers.get("l9-identity-assertion", "")
    padded = encoded + "=" * (-len(encoded) % 4)
    try:
        identity = json.loads(base64.urlsafe_b64decode(padded))
    except (ValueError, json.JSONDecodeError):
        return None
    digest = str(identity.get("assertion_digest", ""))
    mac = headers.get("l9-identity-assertion-hmac", "")
    if not hmac.compare_digest(identity_assertion_hmac(digest, KEYS[agent]), mac):
        return None
    if identity.get("subject_ref") != agent:
        return None
    return agent


@pytest.fixture
def memory_server() -> Any:
    server = _MemoryServer()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()


def _url(server: _MemoryServer) -> str:
    host, port = server.server_address[:2]
    return f"http://{host}:{port}/mcp"


def _session(server: _MemoryServer, agent_id: str) -> tuple[MemoryHttpTransport, StringIO]:
    transport = MemoryHttpTransport(_url(server), _signer(agent_id))
    return transport, StringIO()


def _call(
    server: _MemoryServer, agent_id: str, messages: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    transport, stdout = _session(server, agent_id)
    serve([json.dumps(message) for message in messages], stdout, transport)
    return [json.loads(line) for line in stdout.getvalue().splitlines() if line.strip()]


def _initialize(request_id: int = 1) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "initialize",
        "params": {"protocolVersion": STDIO_PROTOCOL_VERSION, "clientInfo": {"name": "test"}},
    }


def test_signed_handshake_write_and_cross_agent_read(memory_server: _MemoryServer) -> None:
    cursor = _call(
        memory_server,
        "cursor",
        [
            _initialize(1),
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": "list", "method": "tools/list", "params": {}},
            {
                "jsonrpc": "2.0",
                "id": "health",
                "method": "tools/call",
                "params": {"name": "memory.health"},
            },
            {
                "jsonrpc": "2.0",
                "id": "write",
                "method": "tools/call",
                "params": {
                    "name": "memory.write",
                    "arguments": {
                        "namespace": "shared",
                        "content": "from-cursor",
                        "agent_id": "claude-code",
                    },
                },
            },
        ],
    )
    assert cursor[0]["result"]["protocolVersion"] == STDIO_PROTOCOL_VERSION
    assert cursor[1]["id"] == "list"
    assert cursor[2]["result"]["content"][0]["text"] == "ok"
    assert cursor[3]["result"]["content"][0]["text"] == "written"
    claude = _call(
        memory_server,
        "claude-code",
        [
            _initialize(2),
            {
                "jsonrpc": "2.0",
                "id": "read",
                "method": "tools/call",
                "params": {"name": "memory.read", "arguments": {"namespace": "shared"}},
            },
            {
                "jsonrpc": "2.0",
                "id": "deny",
                "method": "tools/call",
                "params": {"name": "memory.write", "arguments": {"namespace": "cursor-only"}},
            },
        ],
    )
    assert json.loads(claude[1]["result"]["content"][0]["text"]) == ["from-cursor"]
    assert claude[2]["error"]["code"] == -32010
    assert "result" not in claude[2]
    authorizations = [
        record["headers"]["authorization"]
        for record in memory_server.records
        if record["body"] and b"memory.write" in record["body"]
    ]
    assert authorizations[0].startswith("Bearer cursor.")
    assert authorizations[1].startswith("Bearer claude-code.")
    for record in memory_server.records:
        blob = record["body"] + json.dumps(record["headers"]).encode()
        assert CURSOR_KEY.encode() not in blob
        assert CLAUDE_KEY.encode() not in blob
    tokens = [record["headers"]["authorization"] for record in memory_server.records]
    assert len(tokens) == len(set(tokens))


def test_expired_assertion_does_not_open_a_connection() -> None:
    class _Explode:
        def open(self, *args: Any, **kwargs: Any) -> Any:
            raise AssertionError("expired credential must not be sent")

    transport = MemoryHttpTransport(
        "http://127.0.0.1:9/mcp",
        _signer("cursor", ttl_seconds=1),
        opener=_Explode(),  # type: ignore[arg-type]
    )
    with pytest.raises(BridgeFailure) as caught:
        transport.exchange(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, protocol_version="2025-11-25"
        )
    assert caught.value.kind == "credential_expired"


def test_unreachable_endpoint_is_not_a_success_receipt() -> None:
    transport = MemoryHttpTransport("http://127.0.0.1:1/mcp", _signer("cursor"), timeout_seconds=2)
    stdout = StringIO()
    serve(
        [
            json.dumps(_initialize()),
        ],
        stdout,
        transport,
    )
    reply = json.loads(stdout.getvalue())
    assert reply["id"] == 1
    assert reply["error"]["data"]["failure_kind"] == "unreachable"
    assert "result" not in reply


def test_a_redirect_is_not_followed() -> None:
    class _Redirect(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            self.rfile.read(length)
            self.send_response(302)
            self.send_header("Location", "http://127.0.0.1:1/mcp")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, fmt: str, *args: Any) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), _Redirect)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address[:2]
        transport = MemoryHttpTransport(f"http://{host}:{port}/mcp", _signer("cursor"))
        stdout = StringIO()
        serve([json.dumps(_initialize())], stdout, transport)
        reply = json.loads(stdout.getvalue())
        assert reply["error"]["data"]["failure_kind"] == "protocol"
        assert "result" not in reply
    finally:
        server.shutdown()
        server.server_close()


def test_durable_key_name_uses_the_injected_binder_only() -> None:
    seen: list[str] = []

    def _bind(name: str) -> str:
        seen.append(name)
        return CURSOR_KEY

    transport = prepare(
        _env("cursor", L9_MEMORY_REMOTE_KEY_NAME="memory/cursor-signing-key"),
        identity_assertion=_assertion("cursor"),
        bind=_bind,
    )
    assert seen == ["memory/cursor-signing-key"]
    assert transport.signer.signing_key == CURSOR_KEY

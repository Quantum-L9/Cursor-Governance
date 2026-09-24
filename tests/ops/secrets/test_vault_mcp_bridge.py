"""vault_mcp_bridge: a remote MCP server whose key is bound from Infisical, never exported."""

from __future__ import annotations

import io
import json
import os
import sys
import urllib.error
from email.message import Message
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SECRETS_DIR = REPO_ROOT / "ops" / "secrets"
for _path in (SECRETS_DIR, REPO_ROOT / "ops" / "lib"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import vault_mcp_bridge as bridge  # noqa: E402

KEY = "ctx7sk-CANARY-KEY-VALUE"
CONFIG = {
    "url": "https://mcp.context7.com/mcp",
    "secret": "CONTEXT7_API_KEY",
    "header": "CONTEXT7_API_KEY",
    "format": "{value}",
}


class _Response:
    def __init__(self, body: bytes, ctype: str = "text/event-stream", session: str = "") -> None:
        self.headers = Message()
        self.headers["Content-Type"] = ctype
        if session:
            self.headers["Mcp-Session-Id"] = session
        self._body = body

    def read(self) -> bytes:
        return self._body


def _sse(message: dict) -> bytes:
    return f"event: message\ndata: {json.dumps(message)}\n\n".encode()


def _run(lines: list[dict], send, capsys: pytest.CaptureFixture[str]) -> list[dict]:
    bridge.Bridge(CONFIG, KEY, send=send).serve(io.StringIO("\n".join(map(json.dumps, lines))))
    return [json.loads(line) for line in capsys.readouterr().out.splitlines()]


def test_the_key_travels_only_as_the_declared_header_to_the_declared_host(
    capsys: pytest.CaptureFixture[str],
) -> None:
    seen: list[dict] = []

    def send(request, *, timeout, allowed_hosts, label):
        seen.append(
            {
                "url": request.full_url,
                "hosts": set(allowed_hosts),
                "headers": dict(request.header_items()),
                "body": request.data,
            }
        )
        return _Response(_sse({"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}))

    out = _run([{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}], send, capsys)
    assert out == [{"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}]
    assert seen[0]["url"] == CONFIG["url"]
    assert seen[0]["hosts"] == {"mcp.context7.com"}
    assert seen[0]["headers"]["Context7_api_key"] == KEY
    assert KEY.encode() not in seen[0]["body"]
    assert KEY not in os.environ.values()


def test_the_session_and_protocol_from_initialize_are_carried_forward(
    capsys: pytest.CaptureFixture[str],
) -> None:
    headers: list[dict] = []

    def send(request, **_kw):
        headers.append(dict(request.header_items()))
        if len(headers) == 1:
            result = {"protocolVersion": "2025-03-26", "serverInfo": {"name": "Context7"}}
            return _Response(_sse({"jsonrpc": "2.0", "id": 1, "result": result}), session="s-1")
        return _Response(b"", ctype="")  # 202 for the notification / call

    _run(
        [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
        ],
        send,
        capsys,
    )
    assert "Mcp-session-id" not in headers[0]
    assert headers[1]["Mcp-session-id"] == "s-1"
    assert headers[1]["Mcp-protocol-version"] == "2025-03-26"


def test_a_response_echoing_the_key_is_withheld(capsys: pytest.CaptureFixture[str]) -> None:
    def send(_request, **_kw):
        leak = {"jsonrpc": "2.0", "id": 7, "result": {"text": f"your key is {KEY}"}}
        return _Response(_sse(leak))

    out = _run([{"jsonrpc": "2.0", "id": 7, "method": "tools/call"}], send, capsys)
    assert out[0]["id"] == 7 and "withheld" in out[0]["error"]["message"]
    assert KEY not in json.dumps(out)


def test_upstream_errors_become_jsonrpc_errors_without_detail(
    capsys: pytest.CaptureFixture[str],
) -> None:
    def send(request, **_kw):
        raise urllib.error.HTTPError(
            request.full_url, 401, "no", Message(), io.BytesIO(KEY.encode())
        )

    out = _run([{"jsonrpc": "2.0", "id": 3, "method": "tools/list"}], send, capsys)
    assert out == [
        {
            "jsonrpc": "2.0",
            "id": 3,
            "error": {"code": bridge.UPSTREAM_ERROR, "message": "upstream HTTP 401"},
        }
    ]


def test_json_responses_are_forwarded_too(capsys: pytest.CaptureFixture[str]) -> None:
    def send(_request, **_kw):
        return _Response(
            json.dumps({"jsonrpc": "2.0", "id": 2, "result": {}}).encode(), "application/json"
        )

    assert _run([{"jsonrpc": "2.0", "id": 2, "method": "ping"}], send, capsys)[0]["id"] == 2


def test_sse_parsing_handles_multiple_events_and_multiline_data() -> None:
    body = b'event: message\ndata: {"a":\ndata: 1}\n\nevent: message\ndata: {"b": 2}\n\n'
    assert bridge.sse_messages(body) == ['{"a":\n1}', '{"b": 2}']


def test_the_registry_declares_context7_with_names_only() -> None:
    config = bridge.load_bridge("context7")
    assert config == CONFIG
    raw = (SECRETS_DIR / "vault-mcp-bridges.json").read_text()
    assert "ctx7sk" not in raw


@pytest.mark.parametrize(
    "entry",
    [
        {"url": "http://mcp.context7.com/mcp", "secret": "S", "header": "H", "format": "{value}"},
        {"url": "https://x.test/mcp", "secret": "S", "header": "H", "format": "static"},
        {"url": "https://x.test/mcp", "secret": "", "header": "H", "format": "{value}"},
    ],
)
def test_the_registry_refuses_unsafe_entries(tmp_path: Path, entry: dict) -> None:
    registry = tmp_path / "bridges.json"
    registry.write_text(json.dumps({"bridges": {"x": entry}}))
    with pytest.raises(bridge.BridgeError):
        bridge.load_bridge("x", registry)


def test_an_unbound_key_refuses_to_start_and_names_the_fix(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(bridge.cb, "bind", lambda _name: None)
    monkeypatch.setattr(
        bridge.cb, "bind_status", lambda name: {"name": name, "bound": False, "source": "unbound"}
    )
    assert bridge.main(["context7"]) == 1
    captured = capsys.readouterr()
    assert captured.out == "", "stdout is the MCP channel"
    assert "L9_INFISICAL_CLIENT_SECRET" in captured.err
    assert "CONTEXT7_API_KEY is not bound" in captured.err


def test_an_unknown_bridge_is_refused(capsys: pytest.CaptureFixture[str]) -> None:
    assert bridge.main(["nope"]) == 2
    assert capsys.readouterr().out == ""

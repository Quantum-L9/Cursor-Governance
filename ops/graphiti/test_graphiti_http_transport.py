"""CWE-939: Graphiti client never hands env URLs to urllib.urlopen."""

from __future__ import annotations

import socket
import ssl
import sys
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import graphiti_memory_client as gmc  # noqa: E402

_CLIENT = Path(__file__).resolve().parent / "graphiti_memory_client.py"


def test_source_does_not_call_urllib_urlopen() -> None:
    src = _CLIENT.read_text(encoding="utf-8")
    assert "urllib.request.urlopen" not in src
    assert "from urllib.request import urlopen" not in src


def test_require_http_url_rejects_file_and_userinfo() -> None:
    with pytest.raises(ValueError, match="non-http"):
        gmc._require_http_url("file:///etc/passwd")
    with pytest.raises(ValueError, match="userinfo"):
        gmc._require_http_url("http://user:pass@127.0.0.1:8100/mcp")


def test_require_http_url_rejects_non_loopback_http() -> None:
    with pytest.raises(ValueError, match="non-loopback"):
        gmc._require_http_url("http://example.com/mcp")


def test_require_http_url_accepts_loopback_and_https() -> None:
    assert gmc._require_http_url("http://127.0.0.1:8100/mcp").startswith("http://")
    assert gmc._require_http_url("https://graphiti.example/mcp").startswith("https://")


def test_urlopen_http_posts_over_loopback_socket() -> None:
    received: dict[str, bytes | str] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            received["path"] = self.path
            received["body"] = self.rfile.read(length)
            received["accept"] = self.headers.get("Accept", "")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Mcp-Session-Id", "sess-1")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')

        def log_message(self, *_args: object) -> None:
            return None

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        url = f"http://127.0.0.1:{port}/mcp"
        req = urllib.request.Request(
            url,
            data=b'{"id":1}',
            headers={
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        ctx = ssl.create_default_context()
        with gmc._urlopen_http(req, timeout=2, context=ctx) as resp:
            body = resp.read()
            session = resp.headers.get("Mcp-Session-Id")
        assert body == b'{"ok":true}'
        assert session == "sess-1"
        assert received["path"] == "/mcp"
        assert received["body"] == b'{"id":1}'
    finally:
        server.shutdown()
        server.server_close()


def test_urlopen_http_refuses_file_scheme() -> None:
    req = urllib.request.Request("file:///etc/passwd")
    ctx = ssl.create_default_context()
    with pytest.raises(ValueError, match="non-http"):
        gmc._urlopen_http(req, timeout=1, context=ctx)


def test_urlopen_http_maps_connect_error() -> None:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    req = urllib.request.Request(f"http://127.0.0.1:{port}/mcp", method="GET")
    ctx = ssl.create_default_context()
    with pytest.raises(urllib.error.URLError):
        gmc._urlopen_http(req, timeout=1, context=ctx)

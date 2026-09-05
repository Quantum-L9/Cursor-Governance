"""Tests for fixed-host OpenAI transport (mocked socket TLS)."""

from __future__ import annotations

import json
import os
import ssl
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from ops.graphiti.hydration import openai_fixed_host as ofh  # noqa: E402
from ops.graphiti.hydration import openai_key as ok  # noqa: E402


class _FakeSock:
    last: dict | None = None

    def __init__(self, response: bytes):
        self._response = response
        self._sent = bytearray()

    def sendall(self, data: bytes) -> None:
        self._sent.extend(data)
        type(self).last = {
            "request": bytes(self._sent),
            "host": ofh._OPENAI_HOST,
            "path": ofh._CHAT_PATH,
        }

    def recv(self, _n: int) -> bytes:
        if not self._response:
            return b""
        out, self._response = self._response, b""
        return out

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeRaw:
    def __init__(self, sock: _FakeSock):
        self._sock = sock

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _http_response(body: bytes, status: int = 200) -> bytes:
    return (
        f"HTTP/1.1 {status} X\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n"
    ).encode("ascii") + body


def _patch_transport(monkeypatch, response: bytes, capture: dict | None = None):
    sock = _FakeSock(response)

    def fake_create_connection(address, timeout=None):
        if capture is not None:
            capture["address"] = address
            capture["timeout"] = timeout
        return _FakeRaw(sock)

    def fake_wrap_socket(self, raw, server_hostname=None):
        if capture is not None:
            capture["server_hostname"] = server_hostname
            capture["verify_mode"] = self.verify_mode
            capture["check_hostname"] = self.check_hostname
            capture["context"] = self
        assert isinstance(raw, _FakeRaw)
        return sock

    monkeypatch.setattr(ofh.socket, "create_connection", fake_create_connection)
    monkeypatch.setattr(ssl.SSLContext, "wrap_socket", fake_wrap_socket)
    return sock


def test_chat_completions_uses_fixed_host(monkeypatch):
    capture: dict = {}
    body = json.dumps({"choices": [{"message": {"content": '{"ok": true}'}}]}).encode()
    sock = _patch_transport(monkeypatch, _http_response(body), capture)
    out = ofh.chat_completions(
        # Synthetic key: the assertions below check it is forwarded verbatim as
        # the Authorization: Bearer header to the fixed host.
        # nosemgrep: l9.baseline.python.hardcoded-credential
        api_key="sk-test",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=50,
        timeout=5.0,
    )
    assert capture["address"] == ("api.openai.com", 443)
    assert capture["server_hostname"] == "api.openai.com"
    assert capture["verify_mode"] == ssl.CERT_REQUIRED
    assert capture["check_hostname"] is True
    assert capture["context"] is not None
    assert sock.last is not None
    req = sock.last["request"].decode("latin-1")
    assert req.startswith("POST /v1/chat/completions HTTP/1.1")
    assert "Host: api.openai.com" in req
    assert "Authorization: Bearer sk-test" in req
    assert out["choices"][0]["message"]["content"]


def test_chat_completions_http_error(monkeypatch):
    _patch_transport(monkeypatch, _http_response(b'{"error":"nope"}', status=401))
    with pytest.raises(ofh.OpenAIFixedHostError, match="openai_http_401"):
        ofh.chat_completions(
            # Synthetic key for the 401 path.
            # nosemgrep: l9.baseline.python.hardcoded-credential
            api_key="sk-bad",
            messages=[{"role": "user", "content": "x"}],
            max_tokens=10,
            timeout=2.0,
        )


def test_message_content():
    assert ofh.message_content({"choices": [{"message": {"content": "  hi  "}}]}) == "hi"


def test_absent_key():
    with pytest.raises(ofh.OpenAIFixedHostError, match="absent"):
        ofh.chat_completions(
            api_key="",
            messages=[{"role": "user", "content": "x"}],
            max_tokens=10,
            timeout=1.0,
        )


def test_https_post_fixed_uses_literal_host_path(monkeypatch):
    """CWE-939 / CWE-295: fixed host + verified TLS only."""
    capture: dict = {}
    _patch_transport(monkeypatch, _http_response(b"{}"), capture)
    ctx = ssl.create_default_context()
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.check_hostname = True
    status, raw = ofh._https_post_fixed(
        body=b"{}",
        headers={"Content-Type": "application/json"},
        timeout=1.0,
        context=ctx,
    )
    assert status == 200
    assert raw == b"{}"
    assert capture["address"] == (ofh._OPENAI_HOST, ofh._OPENAI_PORT)
    assert capture["server_hostname"] == ofh._OPENAI_HOST
    assert capture["verify_mode"] == ssl.CERT_REQUIRED


def test_rejects_unverified_ssl_context():
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with pytest.raises(ofh.OpenAIFixedHostError, match="ssl_verify_mode_not_required"):
        ofh._https_post_fixed(
            body=b"{}",
            headers={},
            timeout=1.0,
            context=ctx,
        )


def test_resolve_key_from_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-env")
    key, reason = ok.resolve_openai_api_key()
    assert key == "sk-from-env"
    assert reason == ""


def test_resolve_key_from_sm(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def fake_fetch(secret_id, region, runner=None):
        assert secret_id == "l9/OPENAI_API_KEY"
        return "sk-from-sm", None

    import ops.secrets.resolve_secret as rs

    monkeypatch.setattr(rs, "fetch_secret_string", fake_fetch)
    key, reason = ok.resolve_openai_api_key(region="us-east-1")
    assert key == "sk-from-sm"
    assert reason == ""
    assert os.environ.get("OPENAI_API_KEY") == "sk-from-sm"

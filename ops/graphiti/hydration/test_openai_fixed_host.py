"""Tests for fixed-host OpenAI transport (mocked HTTPSConnection)."""

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


class _FakeHTTPResponse:
    def __init__(self, payload: bytes, status: int = 200):
        self._payload = payload
        self.status = status

    def read(self) -> bytes:
        return self._payload


class _FakeHTTPSConnection:
    last: dict | None = None

    def __init__(self, host, timeout=None, context=None):
        self.host = host
        self.timeout = timeout
        self.context = context
        self._resp: _FakeHTTPResponse | None = None

    def request(self, method, path, body=None, headers=None):
        type(self).last = {
            "host": self.host,
            "method": method,
            "path": path,
            "body": body,
            "headers": dict(headers or {}),
            "timeout": self.timeout,
            "context": self.context,
        }

    def getresponse(self):
        assert self._resp is not None
        return self._resp

    def close(self):
        return None


def test_chat_completions_uses_fixed_host(monkeypatch):
    conn = _FakeHTTPSConnection("unused")
    conn._resp = _FakeHTTPResponse(
        json.dumps({"choices": [{"message": {"content": '{"ok": true}'}}]}).encode()
    )

    def fake_conn(host, timeout=None, context=None):
        c = _FakeHTTPSConnection(host, timeout=timeout, context=context)
        c._resp = conn._resp
        return c

    monkeypatch.setattr(ofh.http.client, "HTTPSConnection", fake_conn)
    out = ofh.chat_completions(
        api_key="sk-test",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=50,
        timeout=5.0,
    )
    assert _FakeHTTPSConnection.last is not None
    captured = _FakeHTTPSConnection.last
    assert captured["host"] == "api.openai.com"
    assert captured["path"] == "/v1/chat/completions"
    assert captured["method"] == "POST"
    assert any("sk-test" in v for k, v in captured["headers"].items() if "auth" in k.lower())
    assert captured["context"] is not None
    assert out["choices"][0]["message"]["content"]


def test_chat_completions_http_error(monkeypatch):
    def fake_conn(host, timeout=None, context=None):
        c = _FakeHTTPSConnection(host, timeout=timeout, context=context)
        c._resp = _FakeHTTPResponse(b'{"error":"nope"}', status=401)
        return c

    monkeypatch.setattr(ofh.http.client, "HTTPSConnection", fake_conn)
    with pytest.raises(ofh.OpenAIFixedHostError, match="openai_http_401"):
        ofh.chat_completions(
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
    """CWE-939: transport must never accept a caller-controlled URL/scheme."""

    def fake_conn(host, timeout=None, context=None):
        c = _FakeHTTPSConnection(host, timeout=timeout, context=context)
        c._resp = _FakeHTTPResponse(b"{}")
        return c

    monkeypatch.setattr(ofh.http.client, "HTTPSConnection", fake_conn)
    status, raw = ofh._https_post_fixed(
        body=b"{}",
        headers={"Content-Type": "application/json"},
        timeout=1.0,
        context=ssl.create_default_context(),
    )
    assert status == 200
    assert raw == b"{}"
    assert _FakeHTTPSConnection.last is not None
    assert _FakeHTTPSConnection.last["host"] == ofh._OPENAI_HOST
    assert _FakeHTTPSConnection.last["path"] == ofh._CHAT_PATH
    assert "file" not in ofh._OPENAI_HOST
    assert ofh._CHAT_PATH.startswith("/")


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

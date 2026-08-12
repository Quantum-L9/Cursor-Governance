"""Tests for fixed-host OpenAI transport (mocked urlopen)."""

from __future__ import annotations

import io
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from ops.graphiti.hydration import openai_fixed_host as ofh  # noqa: E402
from ops.graphiti.hydration import openai_key as ok  # noqa: E402


class _FakeHTTPResponse(io.BytesIO):
    def __init__(self, payload: bytes, status: int = 200):
        super().__init__(payload)
        self.status = status

    def getcode(self) -> int:
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_chat_completions_uses_fixed_host(monkeypatch):
    captured: dict = {}

    def fake_urlopen(req, timeout=None, context=None):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        captured["headers"] = dict(req.header_items())
        captured["body"] = req.data
        captured["timeout"] = timeout
        captured["context"] = context
        return _FakeHTTPResponse(
            json.dumps({"choices": [{"message": {"content": '{"ok": true}'}}]}).encode()
        )

    monkeypatch.setattr(ofh.urllib.request, "urlopen", fake_urlopen)
    out = ofh.chat_completions(
        api_key="sk-test",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=50,
        timeout=5.0,
    )
    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured["method"] == "POST"
    assert any("sk-test" in v for k, v in captured["headers"].items() if "auth" in k.lower())
    assert captured["context"] is not None
    assert out["choices"][0]["message"]["content"]


def test_chat_completions_http_error(monkeypatch):
    import urllib.error

    def fake_urlopen(req, timeout=None, context=None):
        raise urllib.error.HTTPError(
            url=req.full_url,
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=io.BytesIO(b'{"error":"nope"}'),
        )

    monkeypatch.setattr(ofh.urllib.request, "urlopen", fake_urlopen)
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


def test_urlopen_fixed_refuses_file_scheme():
    import ssl
    import urllib.request

    req = urllib.request.Request("file:///etc/passwd")
    with pytest.raises(ofh.OpenAIFixedHostError, match="refusing non-fixed"):
        ofh._urlopen_fixed(req, timeout=1.0, context=ssl.create_default_context())


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

"""Fixed-host OpenAI Chat Completions transport (Sonar-clean).

Host and path are module constants — never taken from caller input — so this
module is not an SSRF sink. Shared by SessionEnd Phase B and the GHA distill
worker.

Uses http.client.HTTPSConnection against the literal host api.openai.com with
ssl.create_default_context() (certificate verification on). Avoids urllib's
file:// scheme surface (CWE-939 / Bandit B310 / Semgrep dynamic-urllib-use).
"""

from __future__ import annotations

import http.client
import json
import ssl
from typing import Any

# Literal constants only — never overwrite from env or caller.
_OPENAI_HOST = "api.openai.com"
_CHAT_PATH = "/v1/chat/completions"
_DEFAULT_MODEL = "gpt-4o-mini"


class OpenAIFixedHostError(RuntimeError):
    """Transport or protocol failure talking to the fixed OpenAI host."""


def _https_post_fixed(
    *,
    body: bytes,
    headers: dict[str, str],
    timeout: float,
    context: ssl.SSLContext,
) -> tuple[int, bytes]:
    """POST to the module-literal OpenAI host/path only (no urllib / file://)."""
    conn = http.client.HTTPSConnection(
        _OPENAI_HOST,
        timeout=timeout,
        context=context,
    )
    try:
        conn.request("POST", _CHAT_PATH, body=body, headers=headers)
        resp = conn.getresponse()
        return int(resp.status), resp.read()
    finally:
        conn.close()


def chat_completions(
    *,
    api_key: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    timeout: float,
    model: str = _DEFAULT_MODEL,
) -> dict[str, Any]:
    """POST chat completions to api.openai.com via verified HTTPS.

    Returns the parsed JSON response body. Raises OpenAIFixedHostError on
    HTTP/transport/parse failures. Never logs the API key.
    """
    key = (api_key or "").strip()
    if not key:
        raise OpenAIFixedHostError("openai_key_absent")
    if max_tokens < 1:
        raise OpenAIFixedHostError("max_tokens must be >= 1")
    if not messages:
        raise OpenAIFixedHostError("messages required")

    payload = json.dumps(
        {
            "model": model or _DEFAULT_MODEL,
            "max_tokens": int(max_tokens),
            "messages": messages,
        }
    ).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
        "Host": _OPENAI_HOST,
        "Connection": "close",
    }
    # Explicit TLS 1.2+ floor (Sonar python:S4423); default context already
    # verifies certificates against the system trust store.
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    try:
        status, raw = _https_post_fixed(
            body=payload,
            headers=headers,
            timeout=max(1.0, float(timeout)),
            context=context,
        )
        if status >= 400:
            raise OpenAIFixedHostError(f"openai_http_{status}")
        try:
            body = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise OpenAIFixedHostError("openai_response_not_json") from exc
        if not isinstance(body, dict):
            raise OpenAIFixedHostError("openai_response_not_object")
        return body
    except OpenAIFixedHostError:
        raise
    except TimeoutError as exc:
        raise OpenAIFixedHostError("openai_timeout") from exc
    except OSError as exc:
        raise OpenAIFixedHostError(f"openai_transport_{type(exc).__name__}") from exc


def message_content(response: dict[str, Any]) -> str:
    """Extract assistant message content from a chat completions response."""
    try:
        text = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise OpenAIFixedHostError("openai_missing_content") from exc
    if not isinstance(text, str):
        raise OpenAIFixedHostError("openai_content_not_string")
    return text.strip()

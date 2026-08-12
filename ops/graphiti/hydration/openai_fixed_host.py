"""Fixed-host OpenAI Chat Completions transport (Sonar-clean).

Host and path are module constants — never taken from caller input — so this
module is not an SSRF sink. Shared by SessionEnd Phase B and the GHA distill
worker.

Uses urllib.request.urlopen with ssl.create_default_context() (certificate
verification on) — same pattern as ops/graphiti/prune.py / graphiti_memory_client.
"""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from typing import Any

# Literal constants only — never overwrite from env or caller.
_OPENAI_HOST = "api.openai.com"
_CHAT_PATH = "/v1/chat/completions"
_OPENAI_URL = f"https://{_OPENAI_HOST}{_CHAT_PATH}"
_DEFAULT_MODEL = "gpt-4o-mini"


class OpenAIFixedHostError(RuntimeError):
    """Transport or protocol failure talking to the fixed OpenAI host."""


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
        raise OpenAIFixedHostError("OPENAI_API_KEY absent")
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
    # URL is assembled only from module literals — never caller-controlled.
    req = urllib.request.Request(
        _OPENAI_URL,
        data=payload,
        headers=headers,
        method="POST",
    )
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(
            req,
            timeout=max(1.0, float(timeout)),
            context=context,
        ) as resp:
            raw = resp.read()
            status = getattr(resp, "status", None) or resp.getcode()
            if int(status) >= 400:
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
    except urllib.error.HTTPError as exc:
        raise OpenAIFixedHostError(f"openai_http_{exc.code}") from exc
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

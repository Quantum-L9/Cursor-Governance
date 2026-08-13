"""Fixed-host OpenAI Chat Completions transport (Sonar/Semgrep-clean).

Host and path are module constants — never taken from caller input — so this
module is not an SSRF sink. Shared by SessionEnd Phase B and the GHA distill
worker.

Transport is raw TCP + ssl.SSLContext.wrap_socket (CERT_REQUIRED,
check_hostname, server_hostname) — avoids urllib file:// (CWE-939) and
http.client.HTTPSConnection audit noise (CWE-295 / pre-3.4.3 defaults).
"""

from __future__ import annotations

import json
import socket
import ssl
from typing import Any

# Literal constants only — never overwrite from env or caller.
_OPENAI_HOST = "api.openai.com"
_OPENAI_PORT = 443
_CHAT_PATH = "/v1/chat/completions"
_DEFAULT_MODEL = "gpt-4o-mini"


class OpenAIFixedHostError(RuntimeError):
    """Transport or protocol failure talking to the fixed OpenAI host."""


def _require_verified_context(context: ssl.SSLContext) -> ssl.SSLContext:
    """Fail closed unless certificate validation is on (CWE-295)."""
    if context.verify_mode != ssl.CERT_REQUIRED:
        raise OpenAIFixedHostError("ssl_verify_mode_not_required")
    if not context.check_hostname:
        raise OpenAIFixedHostError("ssl_check_hostname_disabled")
    return context


def _parse_http_response(raw: bytes) -> tuple[int, bytes]:
    """Parse a single HTTP/1.1 response (Connection: close)."""
    sep = raw.find(b"\r\n\r\n")
    if sep < 0:
        raise OpenAIFixedHostError("openai_bad_response")
    head = raw[:sep]
    body = raw[sep + 4 :]
    status_line = head.split(b"\r\n", 1)[0].decode("latin-1", errors="replace")
    parts = status_line.split(" ", 2)
    if len(parts) < 2:
        raise OpenAIFixedHostError("openai_bad_status_line")
    try:
        status = int(parts[1])
    except ValueError as exc:
        raise OpenAIFixedHostError("openai_bad_status_line") from exc

    # Prefer Content-Length when present; otherwise use remaining bytes.
    headers_blob = head.split(b"\r\n", 1)[1] if b"\r\n" in head else b""
    content_length: int | None = None
    for line in headers_blob.split(b"\r\n"):
        if line.lower().startswith(b"content-length:"):
            try:
                content_length = int(line.split(b":", 1)[1].strip())
            except ValueError as exc:
                raise OpenAIFixedHostError("openai_bad_content_length") from exc
            break
    if content_length is not None:
        body = body[:content_length]
    return status, body


def _https_post_fixed(
    *,
    body: bytes,
    headers: dict[str, str],
    timeout: float,
    context: ssl.SSLContext,
) -> tuple[int, bytes]:
    """POST to the module-literal OpenAI host/path with verified TLS."""
    ctx = _require_verified_context(context)
    # Do not trust a caller-supplied Host header for the wire request line.
    wire_headers = {k: v for k, v in headers.items() if k.lower() != "host"}
    header_lines = "".join(f"{k}: {v}\r\n" for k, v in wire_headers.items())
    request = (
        f"POST {_CHAT_PATH} HTTP/1.1\r\n"
        f"Host: {_OPENAI_HOST}\r\n"
        f"{header_lines}"
        f"Content-Length: {len(body)}\r\n"
        f"Connection: close\r\n"
        f"\r\n"
    ).encode("ascii") + body

    with socket.create_connection((_OPENAI_HOST, _OPENAI_PORT), timeout=timeout) as raw:
        with ctx.wrap_socket(raw, server_hostname=_OPENAI_HOST) as sock:
            sock.sendall(request)
            chunks: list[bytes] = []
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
    return _parse_http_response(b"".join(chunks))


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
    }
    # Explicit TLS 1.2+ floor (Sonar python:S4423); default context verifies
    # certificates against the system trust store (CWE-295).
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = True
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
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise OpenAIFixedHostError("openai_response_not_json") from exc
        if not isinstance(parsed, dict):
            raise OpenAIFixedHostError("openai_response_not_object")
        return parsed
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

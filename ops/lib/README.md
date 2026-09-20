# Lib

**Path:** `ops/lib` | **Kind:** module

## Purpose

HTTPS-only socket client. Never calls urllib.urlopen (CWE-939).

## Public interface

- `HttpsResponse`
- `def tls12_context() -> ssl.SSLContext` — Default HTTPS context that refuses TLS 1.0/1.1 (CodeQL py/insecure-protocol).
- `def require_https_url(url) -> str` — Refuse file://, http, userinfo, and hosts outside an optional allow-list.
- `def require_exchange_url(url) -> str`
- `def parse_http_response(raw) -> tuple[int, str, Message, bytes]`
- `def exchange(req) -> HttpsResponse` — HTTP/1.0 exchange over a raw socket. No redirects, no urlopen.
- `def https_exchange(req) -> HttpsResponse` — TLS exchange restricted to an explicit host allow-list.

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=module -->

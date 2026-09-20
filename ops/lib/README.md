# Lib

**Path:** `ops/lib` | **Tier:** discovered

## Purpose

HTTPS-only socket client. Never calls urllib.urlopen (CWE-939).



## Components

### `HttpsResponse`

No description

- File: `ops/lib/safe_https.py` (L27–40)
- Methods: `read`

## Functions

- `def tls12_context() -> ssl.SSLContext` — Default HTTPS context that refuses TLS 1.0/1.1 (CodeQL py/insecure-protocol).
- `def require_https_url(url) -> str` — Refuse file://, http, userinfo, and hosts outside an optional allow-list.
- `def require_exchange_url(url) -> str`
- `def parse_http_response(raw) -> tuple[int, str, Message, bytes]`
- `def exchange(req) -> HttpsResponse` — HTTP/1.0 exchange over a raw socket. No redirects, no urlopen.
- `def https_exchange(req) -> HttpsResponse` — TLS exchange restricted to an explicit host allow-list.

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `email.message`, `io`, `socket`, `ssl`, `urllib.error`, `urllib.parse`, `urllib.request`

<!-- l9-module-readme: generated-from-ast -->

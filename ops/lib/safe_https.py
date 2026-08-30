"""HTTPS-only socket client. Never calls urllib.urlopen (CWE-939).

Used by skill fetchers that must stay stdlib-only and must not follow
redirects (Authorization header must not leave the allow-listed host).
"""

from __future__ import annotations

import os
import socket
import ssl
import urllib.error
import urllib.request
from email.message import Message
from io import BytesIO
from urllib.parse import urlparse

_MAX_RESPONSE_BYTES = 8 * 1024 * 1024


def tls12_context() -> ssl.SSLContext:
    """Default HTTPS context that refuses TLS 1.0/1.1 (CodeQL py/insecure-protocol)."""
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    return context


class HttpsResponse:
    def __init__(self, status: int, headers: Message, body: bytes) -> None:
        self.status = status
        self.headers = headers
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> HttpsResponse:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


LOOPBACK_HTTP_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def _proxy_bypasses(host: str) -> bool:
    """True when NO_PROXY exempts ``host``.

    Exact names, leading-dot suffixes, ``*.example.com`` globs and a bare ``*``
    are honored. CIDR entries are ignored: they scope IP literals, and every
    caller here dials a DNS name.
    """
    raw = os.environ.get("NO_PROXY") or os.environ.get("no_proxy") or ""
    host = host.lower().rstrip(".")
    for entry in raw.split(","):
        item = entry.strip().lower().rstrip(".")
        if not item or "/" in item:
            continue
        if item == "*":
            return True
        if item.startswith("*."):
            item = item[1:]
        if item.startswith("."):
            if host == item[1:] or host.endswith(item):
                return True
            continue
        if host == item:
            return True
    return False


def proxy_for_https(host: str) -> str | None:
    """The HTTPS proxy that applies to ``host``, or None for a direct dial.

    A raw socket silently ignores ``HTTPS_PROXY``. In a hosted container where
    all egress is brokered, that turns a health probe into a measurement of a
    path no real client takes: the probe reaches the origin directly while every
    genuine client is refused at the proxy, and a blocked host reports healthy.
    Reading the proxy here keeps the probe on the client's path.
    """
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or ""
    proxy = proxy.strip()
    if not proxy or _proxy_bypasses(host):
        return None
    parsed = urlparse(proxy if "://" in proxy else f"http://{proxy}")
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    return parsed.geturl()


def _open_tunnel(proxy_url: str, host: str, port: int, timeout: float, label: str) -> socket.socket:
    """CONNECT through ``proxy_url`` and return the tunnelled socket.

    The tunnel carries no TLS of its own: the caller wraps the returned socket
    with the verified context and ``server_hostname=host``, so proxy interception
    still fails certificate validation exactly as a direct dial would.
    """
    parsed = urlparse(proxy_url)
    proxy_host = parsed.hostname or ""
    proxy_port = parsed.port or (443 if parsed.scheme == "https" else 80)
    sock = socket.create_connection((proxy_host, proxy_port), timeout=timeout)
    try:
        if parsed.scheme == "https":
            sock = tls12_context().wrap_socket(sock, server_hostname=proxy_host)
        lines = [f"CONNECT {host}:{port} HTTP/1.1", f"Host: {host}:{port}"]
        if parsed.username:
            from base64 import b64encode

            raw = f"{parsed.username}:{parsed.password or ''}".encode()
            lines.append(f"Proxy-Authorization: Basic {b64encode(raw).decode('ascii')}")
        sock.sendall(("\r\n".join(lines) + "\r\n\r\n").encode("latin-1"))
        head = b""
        while b"\r\n\r\n" not in head:
            piece = sock.recv(4096)
            if not piece:
                break
            head += piece
            if len(head) > 65536:
                break
        first = head.split(b"\r\n", 1)[0].decode("latin-1", "replace")
        code = 0
        parts = first.split(None, 2)
        if len(parts) >= 2 and parts[1].isdigit():
            code = int(parts[1])
        if code != 200:
            msg = f"{label} proxy refused CONNECT with status {code or 'unparsable'}"
            raise urllib.error.URLError(msg)
    except BaseException:
        sock.close()
        raise
    return sock


def require_https_url(
    url: str,
    *,
    allowed_hosts: frozenset[str] | None = None,
    label: str = "URL",
) -> str:
    """Refuse file://, http, userinfo, and hosts outside an optional allow-list."""
    parsed = urlparse(url)
    if parsed.scheme != "https":
        msg = f"refusing non-https {label} scheme {parsed.scheme!r}: {url[:120]}"
        raise ValueError(msg)
    if parsed.username or parsed.password:
        msg = f"refusing {label} with userinfo: {url[:120]}"
        raise ValueError(msg)
    host = (parsed.hostname or "").lower()
    if not host:
        msg = f"refusing {label} without host: {url[:120]}"
        raise ValueError(msg)
    if allowed_hosts is not None and host not in allowed_hosts:
        msg = f"refusing {label} host {host!r}: {url[:120]}"
        raise ValueError(msg)
    return url


def require_exchange_url(
    url: str,
    *,
    allowed_https_hosts: frozenset[str] | None = None,
    allow_loopback_http: bool = False,
    label: str = "URL",
) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        msg = f"refusing {label} scheme {parsed.scheme!r}: {url[:120]}"
        raise ValueError(msg)
    if parsed.username or parsed.password:
        msg = f"refusing {label} with userinfo: {url[:120]}"
        raise ValueError(msg)
    host = (parsed.hostname or "").lower()
    if not host:
        msg = f"refusing {label} without host: {url[:120]}"
        raise ValueError(msg)
    if parsed.scheme == "https":
        if allowed_https_hosts is not None and host not in allowed_https_hosts:
            msg = f"refusing {label} host {host!r}: {url[:120]}"
            raise ValueError(msg)
        return url
    if allow_loopback_http and host in LOOPBACK_HTTP_HOSTS:
        return url
    msg = f"refusing non-loopback http {label}: {url[:120]}"
    raise ValueError(msg)


def _decode_chunked(body: bytes) -> bytes:
    out = bytearray()
    rest = body
    while rest:
        nl = rest.find(b"\r\n")
        if nl < 0:
            raise urllib.error.URLError("chunked HTTP body is truncated")
        size_line = rest[:nl].split(b";", 1)[0]
        try:
            size = int(size_line, 16)
        except ValueError as exc:
            raise urllib.error.URLError("chunked HTTP size is not hex") from exc
        rest = rest[nl + 2 :]
        if size == 0:
            break
        if len(rest) < size:
            raise urllib.error.URLError("chunked HTTP body is truncated")
        out.extend(rest[:size])
        rest = rest[size:]
        if rest.startswith(b"\r\n"):
            rest = rest[2:]
    return bytes(out)


def parse_http_response(raw: bytes) -> tuple[int, str, Message, bytes]:
    sep = raw.find(b"\r\n\r\n")
    if sep < 0:
        raise urllib.error.URLError("HTTPS response missing header terminator")
    head = raw[:sep]
    body = raw[sep + 4 :]
    lines = head.split(b"\r\n")
    if not lines:
        raise urllib.error.URLError("HTTPS response missing status line")
    status_line = lines[0].decode("latin-1", errors="replace")
    parts = status_line.split(" ", 2)
    if len(parts) < 2:
        raise urllib.error.URLError("HTTPS status line unparseable")
    try:
        status = int(parts[1])
    except ValueError as exc:
        raise urllib.error.URLError("HTTPS status is not an integer") from exc
    reason = parts[2] if len(parts) > 2 else ""
    headers = Message()
    for line in lines[1:]:
        if b":" not in line:
            continue
        key, value = line.split(b":", 1)
        headers[key.decode("latin-1", errors="replace")] = value.decode(
            "latin-1", errors="replace"
        ).strip()
    encoding = (headers.get("Transfer-Encoding") or "").lower()
    if "chunked" in encoding:
        body = _decode_chunked(body)
    else:
        length = headers.get("Content-Length")
        if length is not None:
            try:
                body = body[: int(length)]
            except ValueError as exc:
                raise urllib.error.URLError("HTTPS Content-Length is invalid") from exc
    return status, reason, headers, body


def exchange(
    req: urllib.request.Request,
    *,
    timeout: float,
    allowed_https_hosts: frozenset[str] | None = None,
    allow_loopback_http: bool = False,
    label: str = "URL",
) -> HttpsResponse:
    """HTTP/1.0 exchange over a raw socket. No redirects, no urlopen.

    HTTPS is always verified (CERT_REQUIRED + check_hostname). Plain HTTP is
    allowed only for loopback when ``allow_loopback_http`` is set.
    """
    url = require_exchange_url(
        req.full_url,
        allowed_https_hosts=allowed_https_hosts,
        allow_loopback_http=allow_loopback_http,
        label=label,
    )
    parsed = urlparse(url)
    host = parsed.hostname
    if host is None:
        msg = f"refusing {label} without host: {url[:120]}"
        raise ValueError(msg)
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    method = req.get_method()
    payload = req.data if isinstance(req.data, (bytes, bytearray)) else b""
    try:
        if parsed.scheme == "https":
            context = tls12_context()
            if context.verify_mode != ssl.CERT_REQUIRED or not context.check_hostname:
                raise urllib.error.URLError("HTTPS requires CERT_REQUIRED and check_hostname")
            port = parsed.port or 443
            proxy = proxy_for_https(host)
            if proxy:
                raw_sock = _open_tunnel(proxy, host, port, timeout, label)
            else:
                raw_sock = socket.create_connection((host, port), timeout=timeout)
            sock: socket.socket = context.wrap_socket(raw_sock, server_hostname=host)
        else:
            port = parsed.port or 80
            sock = socket.create_connection((host, port), timeout=timeout)
    except urllib.error.URLError:
        # Already carries the proxy's refusal reason — do not re-wrap it.
        raise
    except OSError as exc:
        raise urllib.error.URLError(exc) from exc
    header_host = host if parsed.port in (None, 80, 443) else f"{host}:{port}"
    header_lines = [
        f"{method} {path} HTTP/1.0",
        f"Host: {header_host}",
        "Connection: close",
    ]
    for key, value in req.header_items():
        if key.lower() == "host":
            continue
        header_lines.append(f"{key}: {value}")
    if payload:
        header_lines.append(f"Content-Length: {len(payload)}")
    blob = ("\r\n".join(header_lines) + "\r\n\r\n").encode("latin-1") + bytes(payload)
    try:
        sock.sendall(blob)
        chunks: list[bytes] = []
        received = 0
        while True:
            piece = sock.recv(65536)
            if not piece:
                break
            received += len(piece)
            if received > _MAX_RESPONSE_BYTES:
                raise urllib.error.URLError(
                    f"{label} response exceeded {_MAX_RESPONSE_BYTES} bytes"
                )
            chunks.append(piece)
    except OSError as exc:
        raise urllib.error.URLError(exc) from exc
    finally:
        sock.close()
    status, reason, headers, body = parse_http_response(b"".join(chunks))
    if status >= 400:
        raise urllib.error.HTTPError(url, status, reason, headers, BytesIO(body))
    return HttpsResponse(status, headers, body)


def https_exchange(
    req: urllib.request.Request,
    *,
    timeout: float,
    allowed_hosts: frozenset[str],
    label: str = "URL",
) -> HttpsResponse:
    """TLS exchange restricted to an explicit host allow-list."""
    return exchange(
        req,
        timeout=timeout,
        allowed_https_hosts=allowed_hosts,
        allow_loopback_http=False,
        label=label,
    )

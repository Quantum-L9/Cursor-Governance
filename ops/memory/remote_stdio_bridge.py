"""Opt-in stdio MCP bridge to a Memory 3.0 signed-agent HTTP endpoint.

Inactive unless ``L9_MEMORY_REMOTE_STDIO=1``. The default launcher never
imports this module. Models and generated MCP entries keep a stdio command
and never receive the remote URL, a bearer, or a signing key.

The stdio face speaks protocol ``2024-11-05`` (newline-delimited JSON-RPC,
the same framing as ``l9_graphite_memory.server``). The HTTP face speaks
``2025-11-25`` or ``2025-06-18`` and sends ``MCP-Protocol-Version`` only
after initialize. Each request is signed again from the resolved actor.
A remote failure is a JSON-RPC error. This module does not open a local
SQLite store.
"""

from __future__ import annotations

import base64
import json
import ssl
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any, TextIO

from ops.memory.agent_assertion import (
    identity_assertion_hmac,
    mint_assertion,
    seal_identity_assertion,
)
from ops.memory.agent_identity import resolve_agent_id, unresolved_reason
from ops.memory.remote_key_binding import resolve_signing_key

OPT_IN_ENV = "L9_MEMORY_REMOTE_STDIO"
URL_ENV = "L9_MEMORY_REMOTE_URL"
STDIO_PROTOCOL_VERSION = "2024-11-05"
HTTP_PROTOCOL_VERSIONS = ("2025-11-25", "2025-06-18")
IDENTITY_ASSERTION_HEADER = "L9-Identity-Assertion"
IDENTITY_ASSERTION_HMAC_HEADER = "L9-Identity-Assertion-HMAC"
ACCEPT = "application/json, text/event-stream"
EXPIRY_MARGIN_SECONDS = 5
DEFAULT_TIMEOUT_SECONDS = 30.0
MAX_RESPONSE_BYTES = 32 * 1024 * 1024

_KIND_CODE = {
    "malformed": -32700,
    "protocol": -32600,
    "contract_mismatch": -32600,
    "authentication": -32001,
    "credential_expired": -32001,
    "authorization": -32010,
    "configuration": -32603,
    "unreachable": -32603,
    "timeout": -32603,
}


class BridgeFailure(Exception):
    """A remote or handshake failure. The message never includes key material."""

    def __init__(self, kind: str, message: str, *, http_status: int | None = None) -> None:
        super().__init__(message)
        self.kind = kind
        self.http_status = http_status


def encode_identity_assertion(sealed: Mapping[str, Any]) -> str:
    """Base64url of the sealed identity assertion, without padding.

    Same encoding as ``l9_graphite_memory.authz.remote_agent.encode_identity_assertion``
    at Memory ``eb0bcbed``. The installed 2.6.0 package does not ship that
    helper; use it when a later package does.
    """

    try:
        from l9_graphite_memory.authz.remote_agent import (
            encode_identity_assertion as package_encode,
        )
    except ImportError:
        package_encode = None
    if package_encode is not None:
        return str(package_encode(sealed))
    payload = json.dumps(dict(sealed), separators=(",", ":"), ensure_ascii=False)
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii").rstrip("=")


@dataclass
class AssertionSigner:
    """Mints the three HTTP headers for one resolved actor. The key is not repr'd."""

    agent_id: str
    signing_key: str
    identity_assertion: Mapping[str, Any]
    ttl_seconds: int = 3600

    def __repr__(self) -> str:
        return f"AssertionSigner(agent_id={self.agent_id!r})"

    def headers(self) -> dict[str, str]:
        token = mint_assertion(self.agent_id, self.signing_key, ttl_seconds=self.ttl_seconds)
        sealed = seal_identity_assertion(self.identity_assertion)
        digest = str(sealed["assertion_digest"])
        return {
            "Authorization": f"Bearer {token}",
            IDENTITY_ASSERTION_HEADER: encode_identity_assertion(sealed),
            IDENTITY_ASSERTION_HMAC_HEADER: identity_assertion_hmac(digest, self.signing_key),
        }


def _header_safe(value: str, name: str) -> str:
    unsafe = (
        not value
        or not value.isascii()
        or any(character.isspace() or ord(character) < 32 for character in value)
    )
    if unsafe:
        raise BridgeFailure("configuration", f"{name} must be a non-empty single-line ASCII value")
    return value


def _is_loopback(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        import ipaddress

        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def normalize_endpoint(url: str) -> str:
    """``url`` as an ``/mcp`` endpoint, or a configuration failure."""

    from urllib.parse import urlsplit, urlunsplit

    try:
        parts = urlsplit(url.strip())
        parts.port  # raises ValueError on an invalid port
    except ValueError as exc:
        raise BridgeFailure("configuration", "remote memory URL is not a valid URL") from exc
    host = parts.hostname or ""
    if parts.scheme not in {"https", "http"} or not host:
        raise BridgeFailure("configuration", "remote memory URL must be an absolute https:// URL")
    if parts.username is not None or parts.password is not None:
        raise BridgeFailure("configuration", "remote memory URL must not carry credentials")
    if parts.query or parts.fragment:
        raise BridgeFailure("configuration", "remote memory URL must not carry a query or fragment")
    if parts.scheme == "http" and not _is_loopback(host):
        raise BridgeFailure(
            "configuration",
            "plain http:// is accepted only for a loopback host",
        )
    path = parts.path.rstrip("/")
    if not path.endswith("/mcp"):
        path = f"{path}/mcp"
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


class _RefuseRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


@dataclass
class HttpResponse:
    status: int
    content_type: str
    body: bytes


class MemoryHttpTransport:
    """One signed POST to the Memory ``/mcp`` endpoint. Redirects are not followed."""

    def __init__(
        self,
        url: str,
        signer: AssertionSigner,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        clock: Callable[[], float] = time.time,
        opener: urllib.request.OpenerDirector | None = None,
    ) -> None:
        self.endpoint = normalize_endpoint(url)
        self.signer = signer
        self.timeout_seconds = timeout_seconds
        self.clock = clock
        if opener is None:
            from urllib.parse import urlsplit

            handlers: list[Any] = [_RefuseRedirects()]
            host = urlsplit(self.endpoint).hostname or ""
            if _is_loopback(host):
                handlers.append(urllib.request.ProxyHandler({}))
            if self.endpoint.startswith("https://"):
                handlers.append(urllib.request.HTTPSHandler(context=ssl.create_default_context()))
            opener = urllib.request.build_opener(*handlers)
        self._opener = opener

    def exchange(self, message: dict[str, Any], *, protocol_version: str | None) -> HttpResponse:
        headers = self._credential_headers()
        if protocol_version is not None:
            if protocol_version not in HTTP_PROTOCOL_VERSIONS:
                raise BridgeFailure(
                    "protocol",
                    "refusing to send an MCP-Protocol-Version the HTTP server does not speak",
                )
            headers["MCP-Protocol-Version"] = protocol_version
        body = json.dumps(message, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": ACCEPT,
                **headers,
            },
            method="POST",
        )
        try:
            with self._opener.open(request, timeout=self.timeout_seconds) as response:
                payload = response.read(MAX_RESPONSE_BYTES + 1)
                return HttpResponse(
                    status=int(response.status),
                    content_type=response.headers.get("Content-Type", ""),
                    body=payload,
                )
        except urllib.error.HTTPError as exc:
            try:
                payload = exc.read(MAX_RESPONSE_BYTES + 1)
            finally:
                exc.close()
            return HttpResponse(status=int(exc.code), content_type="", body=payload)
        except TimeoutError as exc:
            raise BridgeFailure(
                "timeout",
                f"remote memory server did not answer within {self.timeout_seconds:g}s",
            ) from exc
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, TimeoutError):
                raise BridgeFailure(
                    "timeout",
                    f"remote memory server did not answer within {self.timeout_seconds:g}s",
                ) from exc
            if isinstance(reason, ssl.SSLError):
                raise BridgeFailure(
                    "unreachable",
                    f"TLS to the remote memory server failed: {type(reason).__name__}",
                ) from exc
            raise BridgeFailure(
                "unreachable",
                f"remote memory server is unreachable: {type(reason).__name__}",
            ) from exc
        except OSError as exc:
            raise BridgeFailure(
                "unreachable",
                f"remote memory server is unreachable: {type(exc).__name__}",
            ) from exc

    def _credential_headers(self) -> dict[str, str]:
        minted = self.signer.headers()
        allowed = {"Authorization", IDENTITY_ASSERTION_HEADER, IDENTITY_ASSERTION_HMAC_HEADER}
        if set(minted) != allowed:
            raise BridgeFailure(
                "configuration", "signer produced a header set other than the three required"
            )
        authorization = minted["Authorization"]
        scheme, separator, token = authorization.partition(" ")
        if scheme != "Bearer" or separator != " " or not token or any(ch.isspace() for ch in token):
            raise BridgeFailure("authentication", "Authorization is not a Bearer agent assertion")
        token = _header_safe(token, "agent assertion")
        authorization = f"Bearer {token}"
        parts = token.split(".")
        if len(parts) != 4 or not parts[0] or not parts[1].isdigit():
            raise BridgeFailure("authentication", "agent assertion is not agent_id.exp.nonce.hmac")
        if parts[0] != self.signer.agent_id:
            raise BridgeFailure(
                "authentication", "agent assertion actor does not match the resolved actor"
            )
        if int(parts[1]) <= self.clock() + EXPIRY_MARGIN_SECONDS:
            raise BridgeFailure(
                "credential_expired", "agent assertion is expired or inside the expiry margin"
            )
        _header_safe(minted[IDENTITY_ASSERTION_HEADER], IDENTITY_ASSERTION_HEADER)
        _header_safe(minted[IDENTITY_ASSERTION_HMAC_HEADER], IDENTITY_ASSERTION_HMAC_HEADER)
        if (
            self.signer.signing_key in authorization
            or self.signer.signing_key in minted[IDENTITY_ASSERTION_HEADER]
        ):
            raise BridgeFailure(
                "configuration", "refusing to send a header that contains the signing key"
            )
        return {
            "Authorization": authorization,
            IDENTITY_ASSERTION_HEADER: minted[IDENTITY_ASSERTION_HEADER],
            IDENTITY_ASSERTION_HMAC_HEADER: minted[IDENTITY_ASSERTION_HMAC_HEADER],
        }


def http_protocol_for(client_version: object) -> tuple[str, str]:
    """Return ``(http_version, stdio_version)`` or refuse an unknown client version."""

    if client_version == STDIO_PROTOCOL_VERSION:
        return HTTP_PROTOCOL_VERSIONS[0], STDIO_PROTOCOL_VERSION
    if isinstance(client_version, str) and client_version in HTTP_PROTOCOL_VERSIONS:
        return client_version, client_version
    raise BridgeFailure(
        "protocol",
        "stdio client protocolVersion is not 2024-11-05 or a supported HTTP revision",
    )


def _decode_body(payload: bytes) -> Any:
    if len(payload) > MAX_RESPONSE_BYTES:
        raise BridgeFailure("protocol", "remote response is too large")
    if not payload:
        return None
    try:
        return json.loads(payload)
    except ValueError as exc:
        raise BridgeFailure("protocol", "remote response is not JSON") from exc


def _error_object(decoded: Any) -> dict[str, Any] | None:
    if isinstance(decoded, dict) and isinstance(decoded.get("error"), dict):
        error = decoded["error"]
        if "code" in error and "message" in error:
            return {"code": error["code"], "message": str(error["message"])}
    return None


def _failure_message(failure: BridgeFailure) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": None,
        "error": {
            "code": _KIND_CODE.get(failure.kind, -32603),
            "message": str(failure),
            "data": {"failure_kind": failure.kind, "http_status": failure.http_status},
        },
    }


def _interpret(request_id: Any, response: HttpResponse) -> dict[str, Any] | None:
    if response.status == 202:
        return None
    if 300 <= response.status < 400:
        raise BridgeFailure(
            "protocol",
            f"redirect refused (HTTP {response.status}); credentials are sent to one endpoint only",
            http_status=response.status,
        )
    decoded = _decode_body(response.body)
    if response.status == 401:
        error = _error_object(decoded) or {
            "code": -32001,
            "message": "remote authentication refused",
        }
        return {"jsonrpc": "2.0", "id": request_id, "error": error}
    if response.status == 403:
        error = _error_object(decoded) or {
            "code": -32010,
            "message": "remote authorization refused",
        }
        return {"jsonrpc": "2.0", "id": request_id, "error": error}
    if response.status >= 500 or response.status in {404, 408, 429}:
        raise BridgeFailure(
            "unreachable",
            f"remote memory server is unreachable (HTTP {response.status})",
            http_status=response.status,
        )
    if response.status != 200:
        detail = _error_object(decoded)
        message = str(detail["message"]) if detail else f"HTTP {response.status}"
        raise BridgeFailure(
            "protocol",
            f"remote memory refused the request: {message}",
            http_status=response.status,
        )
    if not isinstance(decoded, dict) or decoded.get("jsonrpc") != "2.0":
        raise BridgeFailure("protocol", "remote response is not a JSON-RPC object")
    if decoded.get("id") != request_id:
        raise BridgeFailure("protocol", "remote response id does not match the request")
    if "error" in decoded and "result" in decoded:
        raise BridgeFailure("protocol", "remote response has both result and error")
    if "result" not in decoded and "error" not in decoded:
        raise BridgeFailure("protocol", "remote response has no result or error")
    return decoded


def _write(stdout: TextIO, message: Mapping[str, Any]) -> None:
    stdout.write(json.dumps(message, separators=(",", ":"), ensure_ascii=False) + "\n")
    stdout.flush()


def serve(stdin: Iterable[str], stdout: TextIO, transport: MemoryHttpTransport) -> None:
    """Read stdio JSON-RPC lines and write the bridged responses."""

    negotiated: str | None = None
    for raw_line in stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            decoded = json.loads(line)
        except json.JSONDecodeError:
            _write(stdout, _failure_message(BridgeFailure("malformed", "parse error")))
            continue
        if not isinstance(decoded, dict):
            _write(
                stdout,
                _failure_message(BridgeFailure("protocol", "batch requests are not supported")),
            )
            continue
        request_id = decoded.get("id")
        method = decoded.get("method")
        try:
            if not isinstance(method, str) or not method:
                raise BridgeFailure("protocol", "request method is missing")
            params = decoded.get("params") if isinstance(decoded.get("params"), dict) else {}
            if method == "initialize":
                client_version = params.get("protocolVersion")
                http_version, stdio_version = http_protocol_for(client_version)
                outbound = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": "initialize",
                    "params": {**params, "protocolVersion": http_version},
                }
                response = transport.exchange(outbound, protocol_version=None)
                interpreted = _interpret(request_id, response)
                if interpreted is None:
                    raise BridgeFailure(
                        "protocol", "initialize returned an empty notification response"
                    )
                if "error" in interpreted:
                    _write(stdout, interpreted)
                    continue
                if "result" not in interpreted:
                    raise BridgeFailure("protocol", "initialize did not return a result")
                result = interpreted["result"]
                if not isinstance(result, dict):
                    raise BridgeFailure("protocol", "initialize result is not an object")
                answered = result.get("protocolVersion")
                if answered not in HTTP_PROTOCOL_VERSIONS:
                    raise BridgeFailure(
                        "contract_mismatch",
                        "server protocolVersion is not an HTTP revision this bridge speaks",
                    )
                negotiated = str(answered)
                rewritten = dict(result)
                rewritten["protocolVersion"] = stdio_version
                _write(stdout, {"jsonrpc": "2.0", "id": request_id, "result": rewritten})
                continue
            if negotiated is None:
                raise BridgeFailure("protocol", "initialize is required before other messages")
            outbound = {"jsonrpc": "2.0", "method": method, "params": params}
            if "id" in decoded:
                outbound["id"] = request_id
            response = transport.exchange(outbound, protocol_version=negotiated)
            if "id" not in decoded:
                if response.status != 202 or response.body.strip():
                    raise BridgeFailure(
                        "protocol",
                        f"notification was answered with HTTP {response.status}, not an empty 202",
                        http_status=response.status,
                    )
                continue
            interpreted = _interpret(request_id, response)
            if interpreted is None:
                raise BridgeFailure(
                    "protocol", "request was answered with an empty notification response"
                )
            _write(stdout, interpreted)
        except BridgeFailure as failure:
            payload = _failure_message(failure)
            payload["id"] = request_id if "id" in decoded else None
            _write(stdout, payload)


def prepare(
    env: Mapping[str, str] | None = None,
    *,
    identity_assertion: Mapping[str, Any] | None = None,
    bind: Callable[[str], str | None] | None = None,
    clock: Callable[[], float] = time.time,
) -> MemoryHttpTransport:
    """Build the transport for an explicit opt-in. Does not open a local store."""

    source = env if env is not None else {}
    if source.get(OPT_IN_ENV, "").strip() != "1":
        raise BridgeFailure("configuration", "remote stdio bridge is opt-in only")
    url = source.get(URL_ENV, "").strip()
    if not url:
        raise BridgeFailure(
            "configuration",
            f"{URL_ENV} is unset — refuse; a local store is not a fallback",
        )
    agent_id = resolve_agent_id(source)
    if not agent_id:
        raise BridgeFailure("configuration", unresolved_reason(source) or "no agent identity")
    try:
        signing_key = resolve_signing_key(agent_id, source, bind=bind)
    except KeyError as exc:
        raise BridgeFailure("configuration", str(exc)) from exc
    if identity_assertion is None:
        from ops.memory.print_agent_assertion_env import build_runtime_identity_assertion

        identity_assertion = build_runtime_identity_assertion(source)
    signer = AssertionSigner(agent_id, signing_key, identity_assertion)
    return MemoryHttpTransport(url, signer, clock=clock)


def main() -> int:
    import sys

    try:
        transport = prepare(dict(os_environ()))
    except BridgeFailure as failure:
        print(f"remote stdio bridge: {failure.kind}: {failure}", file=sys.stderr)
        return 1
    serve(sys.stdin, sys.stdout, transport)
    return 0


def os_environ() -> Mapping[str, str]:
    import os

    return os.environ


if __name__ == "__main__":
    raise SystemExit(main())

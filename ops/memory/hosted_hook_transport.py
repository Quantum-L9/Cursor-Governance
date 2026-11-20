"""The hosted hook carrier's transport: one record, one MCP call, as the hook principal.

``ops/memory/hook_carrier.py`` decides *whether* the hook lane is ``hosted``;
this module carries one envelope-admitted record to the hosted
``MemoryService`` when it is (CANONICAL_LAW §8.11 as amended 2026-11-17,
ADR-0055). It is the one module on the memory path allowed to open a network
connection, and only to two places, both learned at runtime:

- the Memory MCP endpoint — ``resource.identifier`` of
  ``ops/config/memory-auth0-onboarding.yaml``, which is also the token
  audience (the module names no host);
- the Auth0 issuer's token endpoint — from the onboarding ``issuer`` when it
  is bound, otherwise from the resource's RFC 9728 protected-resource metadata
  (``authorization_servers``), then that issuer's OIDC discovery document.
  The token endpoint must sit on the issuer's own host; the client secret is
  sent nowhere else.

Every URL is HTTPS, every exchange goes through ``ops/lib/safe_https.py``
(verified TLS 1.2+, no redirects, one host per request). The access token is a
client-credentials grant for the hook application (``l9-memory-hooks``),
cached in this process only; neither it nor the credential pair is printed,
logged, returned, or written anywhere.

Per record: one MCP ``initialize``, the ``notifications/initialized`` the
lifecycle requires before any request, and one ``tools/call`` naming the tool
the hosted service binds for a *hook principal* (:data:`HOSTED_TOOLS`,
l9-graphiti-memory ``docs/REMOTE_MCP_CONTRACT.md`` §2b): ``write`` goes to
``memory.ingest``, never ``memory.write_agent``. The relay outbox
(``ops/memory/relay.py`` ``CONNECTOR_TOOLS``) keeps ``memory.write_agent``
because an agent carries those entries and writes as itself; this module
writes as ``l9-memory-hooks``, whose envelope admits the hook tools only. The
result is exactly one of three things:

``ok``
    The service answered with a receipt whose id is a UUID. Only this may be
    reported ``OK`` by the caller.
``refused``
    The service's verdict — an MCP tool error, a JSON-RPC error answering the
    ``tools/call``, HTTP 403, or a receipt whose status is ``rejected`` /
    ``quarantined`` / ``failed``. Never rerouted through another door.
``unavailable``
    Not a verdict — network error, 5xx, 401, any other 4xx but 403 (session or
    protocol, before a tool ran), a JSON-RPC error answering ``initialize``,
    token or discovery failure, an unreadable response, or a missing receipt.
    The caller parks the record in the relay outbox with this reason;
    idempotency keys and candidate ids make the later retry converge.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse

from ops.memory.hook_carrier import HOOK_CLIENT_ID, HOOK_CLIENT_SECRET, bind_credential

TRANSPORT = "hosted-mcp"
PROTOCOL_VERSION = "2025-06-18"
CLIENT_INFO = {"name": "l9-cursor-governance-hook-carrier", "version": "1"}
DEFAULT_TIMEOUT = 10.0
#: Seconds shaved off ``expires_in`` so a token is never presented at its edge.
TOKEN_SKEW = 60.0
#: Statuses a receipt can carry that are the service's verdict, not a fault.
REFUSED_STATUSES = frozenset({"rejected", "quarantined", "failed"})
#: At most this many owed entries per drain: a Stop hook has a time budget.
DRAIN_LIMIT = 25

#: Hook-lane operation -> the tool the hosted service binds for a hook
#: principal (REMOTE_MCP_CONTRACT §2b). Deliberately not the relay's
#: ``CONNECTOR_TOOLS``: ``memory.write_agent`` is the agent lane and is never
#: called as the hook principal.
HOSTED_TOOLS: Mapping[str, str] = {
    "write": "memory.ingest",
    "ingest_candidate": "memory.ingest_governed_candidate",
    "close": "memory.close",
}
#: ``memory.ingest`` input properties (the shared ``MemoryWriteRequest`` shape
#: of the bound ``l9_graphite_memory`` release, ``mcp_tools._write_properties``)
#: and the two it requires. An argument outside this set is refused here rather
#: than dropped: a record is sent whole or not at all.
INGEST_FIELDS = frozenset(
    {
        "namespace",
        "content",
        "memory_class",
        "subject",
        "predicate",
        "object",
        "source_id",
        "idempotency_key",
        "valid_from",
        "valid_to",
        "confidence",
        "source_trust",
        "consent",
        "evidence",
        "numeric_declarations",
        "tags",
        "supersedes",
        "references",
        "dry_run",
    }
)
INGEST_REQUIRED = ("namespace", "content")

VERDICT_OK = "ok"
VERDICT_REFUSED = "refused"
VERDICT_UNAVAILABLE = "unavailable"

_LIB_DIR = Path(__file__).resolve().parents[1] / "lib"
_REASON_LIMIT = 500

#: In-process caches only. Keyed by digests, never by a credential.
_TOKENS: dict[str, tuple[str, float]] = {}
_TOKEN_ENDPOINTS: dict[str, tuple[str, str]] = {}


class HostedUnavailable(Exception):
    """The record did not reach a verdict; the message is safe to store."""


class HostedRefused(Exception):
    """The hosted service refused the record; the message quotes its reason."""


@dataclass(frozen=True)
class HttpReply:
    status: int
    headers: Mapping[str, str]
    body: bytes


#: ``http(method, url, headers, body, timeout) -> HttpReply``. Raises
#: :class:`HostedUnavailable` when no HTTP answer was received at all.
Http = Callable[[str, str, Mapping[str, str], bytes | None, float], HttpReply]


@dataclass(frozen=True)
class HostedResult:
    verdict: str
    tool: str
    payload: dict[str, Any] | None = None
    receipt_id: str | None = None
    reason: str | None = None
    latency_ms: int = 0

    @property
    def ok(self) -> bool:
        return self.verdict == VERDICT_OK

    @property
    def refused(self) -> bool:
        return self.verdict == VERDICT_REFUSED

    @property
    def unavailable(self) -> bool:
        return self.verdict == VERDICT_UNAVAILABLE


def reset_caches() -> None:
    """Test hook: forget cached tokens and discovered endpoints."""

    _TOKENS.clear()
    _TOKEN_ENDPOINTS.clear()


def _clip(text: object) -> str:
    return str(text).strip()[:_REASON_LIMIT]


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def _require_https(url: object, label: str) -> str:
    text = str(url or "").strip()
    parsed = urlparse(text)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise HostedUnavailable(f"{label} is not an https URL without userinfo")
    return text


def _default_http(
    method: str, url: str, headers: Mapping[str, str], body: bytes | None, timeout: float
) -> HttpReply:
    if str(_LIB_DIR) not in sys.path:
        sys.path.insert(0, str(_LIB_DIR))
    import safe_https  # noqa: PLC0415 - ops/lib is not a package

    request = urllib.request.Request(url, data=body, method=method, headers=dict(headers))
    host = _host(url)
    try:
        response = safe_https.https_exchange(
            request, timeout=timeout, allowed_hosts=frozenset({host}), label="hosted memory"
        )
        return HttpReply(
            response.status,
            {k.lower(): v for k, v in response.headers.items()},
            response.read(),
        )
    except urllib.error.HTTPError as exc:
        headers_in = exc.headers.items() if exc.headers is not None else ()
        return HttpReply(exc.code, {k.lower(): v for k, v in headers_in}, exc.read() or b"")
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise HostedUnavailable(f"{type(exc).__name__} reaching {host}") from exc


def _json_body(reply: HttpReply, label: str) -> dict[str, Any]:
    try:
        decoded = json.loads(reply.body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise HostedUnavailable(f"{label}: unreadable JSON (HTTP {reply.status})") from exc
    if not isinstance(decoded, dict):
        raise HostedUnavailable(f"{label}: response is not a JSON object")
    return decoded


def _rpc_messages(reply: HttpReply) -> list[dict[str, Any]]:
    """JSON-RPC messages in a Streamable HTTP reply (``application/json`` or SSE)."""

    content_type = str(reply.headers.get("content-type", "")).lower()
    text = reply.body.decode("utf-8", errors="replace")
    if "text/event-stream" in content_type:
        messages: list[dict[str, Any]] = []
        data: list[str] = []
        for line in [*text.splitlines(), ""]:
            if line.startswith("data:"):
                data.append(line[5:].lstrip())
            elif not line.strip() and data:
                try:
                    decoded = json.loads("\n".join(data))
                except ValueError:
                    decoded = None
                data = []
                if isinstance(decoded, dict):
                    messages.append(decoded)
        return messages
    try:
        decoded = json.loads(text)
    except ValueError:
        return []
    if isinstance(decoded, dict):
        return [decoded]
    if isinstance(decoded, list):
        return [item for item in decoded if isinstance(item, dict)]
    return []


def _rpc_error_text(error: object) -> str:
    if isinstance(error, dict):
        return _clip(f"JSON-RPC error {error.get('code')}: {error.get('message')}")
    return _clip(f"JSON-RPC error: {error}")


def _tool_payload(result: Mapping[str, Any]) -> dict[str, Any]:
    """The receipt object inside an MCP ``tools/call`` result."""

    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        inner = structured.get("result")
        if len(structured) == 1 and isinstance(inner, dict):
            return inner
        return structured
    for item in result.get("content") or ():
        if isinstance(item, dict) and item.get("type") == "text":
            try:
                decoded = json.loads(str(item.get("text") or ""))
            except ValueError:
                continue
            if isinstance(decoded, dict):
                return decoded
    raise HostedUnavailable("tools/call result carries no readable receipt")


def _tool_error_text(result: Mapping[str, Any]) -> str:
    parts = [
        str(item.get("text") or "")
        for item in result.get("content") or ()
        if isinstance(item, dict) and item.get("type") == "text"
    ]
    return _clip(" ".join(part for part in parts if part) or "tool reported isError")


def hosted_arguments(operation: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
    """The ``tools/call`` arguments for ``operation`` in its hosted tool's shape.

    ``write`` must fit ``memory.ingest``: both required fields present and no
    field the tool does not declare. The other operations pass through, since
    their relay arguments are already their hosted tool's arguments.
    """

    shaped = dict(arguments)
    if operation != "write":
        return shaped
    unknown = sorted(set(shaped) - INGEST_FIELDS)
    if unknown:
        raise HostedUnavailable(f"write arguments not declared by memory.ingest: {unknown}")
    missing = [name for name in INGEST_REQUIRED if not shaped.get(name)]
    if missing:
        raise HostedUnavailable(f"write arguments missing memory.ingest fields: {missing}")
    return shaped


def receipt_id_of(payload: Mapping[str, Any]) -> str | None:
    """The receipt's UUID (``receipt_id``, else ``write_receipt_id``), or ``None``."""

    for key in ("receipt_id", "write_receipt_id"):
        value = payload.get(key)
        if value is None:
            continue
        try:
            return str(uuid.UUID(str(value).strip()))
        except ValueError:
            continue
    return None


class HostedHookTransport:
    """Sends one hook-lane record to the hosted Memory MCP endpoint."""

    def __init__(
        self,
        env: Mapping[str, str] | None = None,
        *,
        http: Http | None = None,
        onboarding: Mapping[str, Any] | None = None,
        credential: Callable[[str], str | None] | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._env = env
        self._http = http or _default_http
        self._onboarding = onboarding
        self._credential = credential or (lambda name: bind_credential(name, env))
        self._timeout = timeout
        self._clock = clock

    # -- configuration --------------------------------------------------------
    def _document(self) -> Mapping[str, Any]:
        if self._onboarding is None:
            from ops.memory.auth0_native_oauth import load_onboarding  # noqa: PLC0415

            try:
                self._onboarding = load_onboarding()
            except (OSError, ValueError) as exc:
                raise HostedUnavailable(f"onboarding unreadable: {type(exc).__name__}") from exc
        return self._onboarding

    def resource(self) -> str:
        """The Memory MCP endpoint, which is also the token audience."""

        resource = (self._document().get("resource") or {}).get("identifier")
        return _require_https(resource, "onboarding resource.identifier")

    def _onboarding_issuer(self) -> str | None:
        issuer = self._document().get("issuer") or {}
        url = str(issuer.get("issuer_url") or "").strip()
        domain = str(issuer.get("domain") or "").strip()
        if url:
            return _require_https(url, "onboarding issuer.issuer_url")
        if domain:
            return _require_https(f"https://{domain}/", "onboarding issuer.domain")
        return None

    # -- HTTP -----------------------------------------------------------------
    def _get_json(self, url: str, label: str) -> dict[str, Any] | None:
        """A discovery document, or ``None`` on 404 (so the next candidate is tried)."""

        reply = self._http("GET", url, {"Accept": "application/json"}, None, self._timeout)
        if reply.status == 404:
            return None
        if reply.status != 200:
            raise HostedUnavailable(f"{label}: HTTP {reply.status}")
        return _json_body(reply, label)

    def _protected_resource_issuer(self, resource: str) -> str:
        """RFC 9728: the first authorization server the resource names."""

        parsed = urlparse(resource)
        origin = f"https://{parsed.netloc}"
        path = parsed.path.rstrip("/")
        candidates = [f"{origin}/.well-known/oauth-protected-resource{path}"]
        if path:
            candidates.append(f"{origin}/.well-known/oauth-protected-resource")
        for url in candidates:
            metadata = self._get_json(url, "protected-resource metadata")
            if metadata is None:
                continue
            named = metadata.get("resource")
            if named is not None and str(named).rstrip("/") != resource.rstrip("/"):
                raise HostedUnavailable("protected-resource metadata names another resource")
            servers = metadata.get("authorization_servers") or []
            if servers:
                return _require_https(servers[0], "authorization_servers[0]")
        raise HostedUnavailable("protected-resource metadata names no authorization server")

    def _token_endpoint(self, resource: str) -> tuple[str, str]:
        """``(issuer, token_endpoint)``, discovered once per process."""

        cached = _TOKEN_ENDPOINTS.get(resource)
        if cached:
            return cached
        issuer = self._onboarding_issuer() or self._protected_resource_issuer(resource)
        base = issuer.rstrip("/")
        document = None
        for url in (
            f"{base}/.well-known/openid-configuration",
            f"{base}/.well-known/oauth-authorization-server",
        ):
            document = self._get_json(url, "issuer discovery")
            if document is not None:
                break
        if document is None:
            raise HostedUnavailable("issuer publishes no discovery document")
        if str(document.get("issuer") or "").rstrip("/") != base:
            raise HostedUnavailable("discovery document names another issuer")
        endpoint = _require_https(document.get("token_endpoint"), "token_endpoint")
        if _host(endpoint) != _host(issuer):
            raise HostedUnavailable("token_endpoint is not on the issuer's host")
        _TOKEN_ENDPOINTS[resource] = (issuer, endpoint)
        return issuer, endpoint

    def _token(self, resource: str) -> str:
        client_id = self._credential(HOOK_CLIENT_ID)
        client_secret = self._credential(HOOK_CLIENT_SECRET)
        if not client_id or not client_secret:
            raise HostedUnavailable("hook credential does not bind")
        key = hashlib.sha256(f"{client_id}\0{resource}".encode()).hexdigest()
        cached = _TOKENS.get(key)
        if cached and cached[1] > self._clock():
            return cached[0]
        _issuer, endpoint = self._token_endpoint(resource)
        body = urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "audience": resource,
            }
        ).encode("ascii")
        reply = self._http(
            "POST",
            endpoint,
            {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
            body,
            self._timeout,
        )
        if reply.status != 200:
            code = ""
            try:
                code = str(json.loads(reply.body.decode("utf-8")).get("error") or "")
            except (UnicodeDecodeError, ValueError, AttributeError):
                code = ""
            raise HostedUnavailable(
                f"token request refused: HTTP {reply.status}" + (f" ({code[:60]})" if code else "")
            )
        grant = _json_body(reply, "token response")
        token = grant.get("access_token")
        if not isinstance(token, str) or not token:
            raise HostedUnavailable("token response carries no access_token")
        try:
            lifetime = float(grant.get("expires_in") or 0)
        except (TypeError, ValueError):
            lifetime = 0.0
        _TOKENS[key] = (token, self._clock() + max(0.0, lifetime - TOKEN_SKEW))
        return token

    def _drop_token(self, resource: str) -> None:
        client_id = self._credential(HOOK_CLIENT_ID) or ""
        _TOKENS.pop(hashlib.sha256(f"{client_id}\0{resource}".encode()).hexdigest(), None)

    def _post(
        self,
        resource: str,
        token: str,
        message: Mapping[str, Any],
        *,
        session_id: str | None,
        protocol: str | None,
    ) -> HttpReply:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if session_id:
            headers["Mcp-Session-Id"] = session_id
        if protocol:
            headers["MCP-Protocol-Version"] = protocol
        body = json.dumps(dict(message), ensure_ascii=False).encode("utf-8")
        reply = self._http("POST", resource, headers, body, self._timeout)
        if reply.status == 401:
            self._drop_token(resource)
            raise HostedUnavailable("MCP endpoint: HTTP 401 (hook principal not authenticated)")
        if reply.status == 403:
            detail = ""
            for msg in _rpc_messages(reply):
                if "error" in msg:
                    detail = ": " + _rpc_error_text(msg["error"])
            raise HostedRefused(_clip(f"HTTP 403 from the Memory MCP endpoint{detail}"))
        if reply.status >= 400:
            # 400 / 404 / 405 / 406 / 5xx: the session or the protocol failed, so
            # the record never reached a tool. Not a verdict on the record.
            raise HostedUnavailable(f"MCP endpoint: HTTP {reply.status}")
        return reply

    def _rpc(
        self,
        resource: str,
        token: str,
        request_id: int,
        method: str,
        params: Mapping[str, Any],
        *,
        session_id: str | None,
        protocol: str | None,
        error_is_verdict: bool,
    ) -> tuple[dict[str, Any], HttpReply]:
        """One JSON-RPC request. ``error_is_verdict``: a JSON-RPC error answers the
        record (``tools/call``) rather than the session (``initialize``)."""

        message = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": dict(params)}
        reply = self._post(resource, token, message, session_id=session_id, protocol=protocol)
        for msg in _rpc_messages(reply):
            if msg.get("id") != request_id:
                continue
            if "error" in msg:
                if error_is_verdict:
                    raise HostedRefused(_rpc_error_text(msg["error"]))
                raise HostedUnavailable(f"{method}: {_rpc_error_text(msg['error'])}")
            result = msg.get("result")
            if isinstance(result, dict):
                return result, reply
        raise HostedUnavailable(f"{method}: no JSON-RPC response for request {request_id}")

    # -- the one public operation ------------------------------------------------
    def call(self, operation: str, arguments: Mapping[str, Any]) -> HostedResult:
        """Carry one hook-lane record; never raises for a transport problem."""

        started = self._clock()
        tool = HOSTED_TOOLS.get(operation, "")
        try:
            if not tool:
                raise HostedUnavailable(f"operation {operation!r} has no hosted tool")
            payload = self._call(tool, hosted_arguments(operation, arguments))
        except HostedRefused as exc:
            return HostedResult(
                VERDICT_REFUSED, tool, reason=_clip(exc), latency_ms=self._ms(started)
            )
        except HostedUnavailable as exc:
            return HostedResult(
                VERDICT_UNAVAILABLE, tool, reason=_clip(exc), latency_ms=self._ms(started)
            )
        status = str(payload.get("status") or "").lower()
        if status in REFUSED_STATUSES:
            reason = payload.get("reason") or payload.get("error") or f"receipt status {status}"
            return HostedResult(
                VERDICT_REFUSED,
                tool,
                payload=payload,
                reason=_clip(f"{status}: {reason}"),
                latency_ms=self._ms(started),
            )
        receipt = receipt_id_of(payload)
        if receipt is None:
            return HostedResult(
                VERDICT_UNAVAILABLE,
                tool,
                payload=payload,
                reason="hosted result carries no UUID receipt id",
                latency_ms=self._ms(started),
            )
        return HostedResult(
            VERDICT_OK, tool, payload=payload, receipt_id=receipt, latency_ms=self._ms(started)
        )

    def _ms(self, started: float) -> int:
        return max(0, int((self._clock() - started) * 1000))

    def _call(self, tool: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        resource = self.resource()
        token = self._token(resource)
        initialized, reply = self._rpc(
            resource,
            token,
            1,
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": dict(CLIENT_INFO),
            },
            session_id=None,
            protocol=None,
            error_is_verdict=False,
        )
        session_id = reply.headers.get("mcp-session-id") or None
        protocol = str(initialized.get("protocolVersion") or PROTOCOL_VERSION)
        self._post(
            resource,
            token,
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            session_id=session_id,
            protocol=protocol,
        )
        result, _reply = self._rpc(
            resource,
            token,
            2,
            "tools/call",
            {"name": tool, "arguments": dict(arguments)},
            session_id=session_id,
            protocol=protocol,
            error_is_verdict=True,
        )
        if result.get("isError"):
            raise HostedRefused(_tool_error_text(result))
        return _tool_payload(result)


def drain(
    workspace: str | Path,
    *,
    transport: HostedHookTransport | None = None,
    limit: int = DRAIN_LIMIT,
) -> dict[str, Any]:
    """Carry owed relay entries through the hosted transport (Stop hook, ADR-0055).

    Each entry ends acknowledged with its hosted receipt, rejected with the
    service's refusal, or still owed. The first transport failure stops the
    drain: the endpoint that just failed is not asked again for every entry
    inside one Stop. Returns counts and the stop reason; never raises for a
    transport problem.
    """

    from ops.memory import relay  # noqa: PLC0415

    carrier = transport or HostedHookTransport()
    report: dict[str, Any] = {"acked": [], "rejected": [], "remaining": 0, "stopped": None}
    owed: Sequence[Mapping[str, Any]] = relay.pending(workspace)
    for index, entry in enumerate(owed):
        if index >= limit:
            report["stopped"] = f"drain limit {limit} reached"
            break
        ident = str(entry.get("id"))
        result = carrier.call(str(entry.get("operation")), entry.get("arguments") or {})
        if result.ok and result.receipt_id:
            relay.ack(workspace, ident, result.receipt_id)
            report["acked"].append(ident)
        elif result.refused:
            relay.reject(workspace, ident, result.reason or "refused by the hosted service")
            report["rejected"].append(ident)
        else:
            report["stopped"] = result.reason or "hosted transport unavailable"
            break
    report["remaining"] = len(relay.pending(workspace))
    return report

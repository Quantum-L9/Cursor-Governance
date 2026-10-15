#!/usr/bin/env python3
"""stdio MCP bridge to the admitted remote Memory service (ADR-0053, §8.10).

Cursor and Claude Code keep one model-visible memory entry: a local stdio
server launched by ``ops/memory/run_memory_mcp.sh``, with no URL, no headers
and no env block. When an operator names an admitted ``memory-remote-mcp/v1``
endpoint, the launcher execs this bridge instead of the package's local stdio
server. The bridge forwards each JSON-RPC line to that one endpoint over
authenticated Streamable HTTP and writes the service's messages back on stdout.
The tool set, envelopes and ``memory-control-plane/v1`` contract are the
service's own; the bridge adds and removes nothing.

Identity is the agent's own. Every request carries a freshly minted ADR-0031
signed-agent token for the derived actor and the sealed canonical identity
assertion (``l9.identity-assertion/v1``) under that agent's signing key. Grants,
the agents door secret and the human door never leave this machine: the server
owns grants (``memory-remote-mcp/v1``) and the bridge refuses to carry them.

Fail closed, never fall back:

* no endpoint configured  -> local mode (the launcher never calls ``--serve``)
* endpoint invalid, retired, non-``/mcp``, plain HTTP off loopback -> refuse
* release binding not admitted (``ops/config/memory-remote-binding.json``) ->
  refuse; a release *candidate* is reachable only on loopback, only for named
  qualification (``L9_MEMORY_REMOTE_CANDIDATE_QUALIFICATION=<reason>``)
* service identity (package version, both contract versions) differs -> refuse
* authentication refused -> refuse at start; mid-session, one re-mint and then
  a JSON-RPC error. No request is ever re-sent to another backend.

stdout is the MCP channel: diagnostics go to stderr only.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import threading
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ops.lib.safe_https import LOOPBACK_HTTP_HOSTS, exchange  # noqa: E402
from ops.memory.agent_assertion import (  # noqa: E402
    HUMAN_PRINCIPAL,
    identity_assertion_hmac,
    local_assertion_digest,
    mint_assertion,
)

BINDING_PATH = ROOT / "ops" / "config" / "memory-remote-binding.json"
CONTRACT_PATH = (
    ROOT
    / "environment"
    / "agents"
    / "adapters"
    / "claude-code"
    / "memory"
    / "memory-enforcement.contract.json"
)

BINDING_SCHEMA = "l9.memory-remote-binding.v1"
REMOTE_CONTRACT = "memory-remote-mcp/v1"
CONTROL_PLANE_CONTRACT = "memory-control-plane/v1"
ACTOR_PREFIX = "l9.actor-registry/global@1#"

ENV_ENDPOINT = "L9_MEMORY_REMOTE_MCP_ENDPOINT"
ENV_CONFIG = "L9_MEMORY_REMOTE_CONFIG"
ENV_CANDIDATE = "L9_MEMORY_REMOTE_CANDIDATE_QUALIFICATION"
ENV_AGENT_ID = "L9_MEMORY_AGENT_ID"
ENV_SIGNING_KEYS = "L9_MEMORY_AGENT_SIGNING_KEYS_JSON"
ENV_IDENTITY = "L9_MEMORY_IDENTITY_ASSERTION_JSON"
#: Server-side material. The service owns grants and verifies against its own
#: key registry; none of these may ride a request or survive into this process.
SERVER_SIDE_ENV = (
    "L9_MEMORY_AGENTS_DOOR_SECRET",
    "L9_MEMORY_AGENT_GRANTS_JSON",
    "L9_MEMORY_AGENT_ASSERTION",
    "L9_MEMORY_IDENTITY_ASSERTION_HMAC",
    "L9_MEMORY_HUMAN_DOOR_SECRET",
    "L9_MEMORY_SECRET_MAP",
    "L9_MEMORY_GRANTS_MAP",
)

MCP_PATHS = frozenset({"/mcp", "/mcp/"})
#: Ports of the retired C1 memory API. The retired hosts and variable names are
#: read from the contract's ``memory.forbidden_side_doors`` (one SSOT), so this
#: module never spells a retired transport itself (egress scanner).
RETIRED_PORTS = frozenset({9002, 8100})
#: Bare affirmatives are not a reason (rule 54's human-authorization shape).
_NOT_A_REASON = frozenset({"", "1", "true", "yes", "y", "on"})
ACCEPT = "application/json, text/event-stream"
TIMEOUT = 120.0
AUTH_REFUSED = -32001
UNAVAILABLE = -32000

Send = Callable[..., Any]


class RemoteBindingError(RuntimeError):
    """The remote transport cannot serve. The message names the fix."""


# ---------------------------------------------------------------------------
# Selection and validation
# ---------------------------------------------------------------------------


def default_config_path(env: Mapping[str, str]) -> Path:
    configured = env.get(ENV_CONFIG, "").strip()
    if configured:
        return Path(configured).expanduser()
    home = env.get("HOME", "").strip() or str(Path.home())
    return Path(home) / ".config" / "l9-memory" / "remote-endpoint.json"


def requested_endpoint(env: Mapping[str, str]) -> str | None:
    """The operator-named endpoint, or None for local stdio mode.

    The environment wins over the per-machine config file. The file exists for
    Dock-launched desktop hosts, whose MCP children inherit no shell export. It
    holds an address only: ``{"endpoint": "https://<host>/mcp"}``.
    """

    value = env.get(ENV_ENDPOINT, "").strip()
    if value:
        return value
    path = default_config_path(env)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RemoteBindingError(f"remote endpoint config {path} is unreadable: {exc}") from exc
    if not isinstance(data, dict) or set(data) != {"endpoint"}:
        raise RemoteBindingError(
            f'remote endpoint config {path} must be exactly {{"endpoint": "https://<host>/mcp"}}'
            " (an address only: no credential, header or grant belongs in it)"
        )
    endpoint = data["endpoint"]
    if not isinstance(endpoint, str) or not endpoint.strip():
        raise RemoteBindingError(f"remote endpoint config {path} names no endpoint")
    return endpoint.strip()


def forbidden_side_doors(contract_path: Path = CONTRACT_PATH) -> tuple[str, ...]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    doors = contract.get("memory", {}).get("forbidden_side_doors", [])
    return tuple(str(door) for door in doors if isinstance(door, str) and door)


def is_loopback(endpoint: str) -> bool:
    return (urlparse(endpoint).hostname or "").lower() in LOOPBACK_HTTP_HOSTS


def validate_endpoint(endpoint: str, *, side_doors: Iterable[str]) -> str:
    """Return ``endpoint`` when it can only be an admitted service's MCP route."""

    parsed = urlparse(endpoint)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"https", "http"}:
        raise RemoteBindingError(f"remote endpoint scheme {parsed.scheme!r} is not https")
    if parsed.scheme == "http" and host not in LOOPBACK_HTTP_HOSTS:
        raise RemoteBindingError("remote endpoint must be https off loopback (TLS is not optional)")
    if not host:
        raise RemoteBindingError("remote endpoint names no host")
    if parsed.username or parsed.password:
        raise RemoteBindingError("remote endpoint must not carry userinfo (no credential in a URL)")
    if parsed.query or parsed.fragment or parsed.params:
        raise RemoteBindingError("remote endpoint must not carry a query, fragment or params")
    if parsed.path not in MCP_PATHS:
        raise RemoteBindingError(
            f"remote endpoint path {parsed.path or '/'!r} is not the {REMOTE_CONTRACT} route /mcp"
        )
    try:
        port = parsed.port
    except ValueError as exc:
        raise RemoteBindingError(f"remote endpoint port is invalid: {exc}") from exc
    if port in RETIRED_PORTS:
        raise RemoteBindingError(f"remote endpoint port {port} is a retired memory endpoint")
    lowered = endpoint.lower()
    for door in side_doors:
        if door.lower() in lowered:
            raise RemoteBindingError(
                "remote endpoint names a retired memory side door listed in "
                "memory-enforcement.contract.json memory.forbidden_side_doors"
            )
    return endpoint


# ---------------------------------------------------------------------------
# Release binding
# ---------------------------------------------------------------------------


def load_binding(path: Path = BINDING_PATH) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RemoteBindingError(f"remote release binding {path} is unreadable: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema") != BINDING_SCHEMA:
        raise RemoteBindingError(f"remote release binding {path} is not {BINDING_SCHEMA}")
    if data.get("remote_contract_version") != REMOTE_CONTRACT:
        raise RemoteBindingError(f"remote release binding does not name {REMOTE_CONTRACT}")
    if data.get("control_plane_contract_version") != CONTROL_PLANE_CONTRACT:
        raise RemoteBindingError(f"remote release binding does not name {CONTROL_PLANE_CONTRACT}")
    return data


_RELEASE_EVIDENCE = ("version", "source_sha", "tag", "wheel_sha256", "admission_receipt")


def bound_release(
    binding: Mapping[str, Any], endpoint: str, env: Mapping[str, str]
) -> dict[str, str]:
    """The exact release this consumer may talk to, or a refusal.

    An admitted release names every evidence field. A candidate is reachable only
    on loopback and only under a named qualification reason: it is how the
    consumer is proven against release-candidate bytes before admission, never a
    route to a hosted service.
    """

    release = binding.get("release") or {}
    if release.get("admission") == "admitted":
        missing = [key for key in _RELEASE_EVIDENCE if not str(release.get(key) or "").strip()]
        if missing:
            raise RemoteBindingError(
                f"remote release binding claims admission without evidence: {', '.join(missing)}"
            )
        return {"mode": "admitted", "version": str(release["version"])}
    reason = env.get(ENV_CANDIDATE, "").strip()
    candidate = binding.get("candidate") or {}
    if reason.lower() not in _NOT_A_REASON and str(candidate.get("version") or "").strip():
        if not is_loopback(endpoint):
            raise RemoteBindingError(
                "release-candidate qualification is loopback-only: an unadmitted release "
                "is never reachable at a hosted endpoint"
            )
        return {"mode": "candidate_qualification", "version": str(candidate["version"])}
    raise RemoteBindingError(
        "missing or unadmitted Memory release binding "
        f"(ops/config/memory-remote-binding.json release.admission="
        f"{release.get('admission')!r}): bind the exact admitted release before selecting "
        "the remote transport"
    )


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


class Credentials:
    """One agent's signing key and sealed identity; mints per request."""

    def __init__(
        self, agent_id: str, signing_key: str, identity: Mapping[str, Any], ttl: int
    ) -> None:
        if not agent_id or agent_id == HUMAN_PRINCIPAL or "HUMAN" in agent_id.upper():
            raise RemoteBindingError("refusing the human principal over HTTP: agents only")
        actor = (identity.get("resolved_dimensions") or {}).get("actor_identity")
        if actor != f"{ACTOR_PREFIX}{agent_id}" or identity.get("subject_ref") != actor:
            raise RemoteBindingError(
                f"identity assertion names {actor!r}, not the authenticated agent {agent_id!r}"
            )
        digest = local_assertion_digest(identity)
        if identity.get("assertion_digest") != digest:
            raise RemoteBindingError("identity assertion is not sealed (assertion_digest mismatch)")
        self.agent_id = agent_id
        self.ttl = ttl
        self._key = signing_key
        compact = json.dumps(identity, separators=(",", ":"), ensure_ascii=False)
        self._identity_header = _b64url(compact.encode("utf-8"))
        self._identity_hmac = identity_assertion_hmac(digest, signing_key)

    @property
    def secret_bytes(self) -> bytes:
        return self._key.encode("utf-8")

    def headers(self) -> dict[str, str]:
        token = mint_assertion(self.agent_id, self._key, ttl_seconds=self.ttl)
        return {
            "Authorization": f"Bearer {token}",
            "L9-Identity-Assertion": self._identity_header,
            "L9-Identity-Assertion-HMAC": self._identity_hmac,
        }


def credentials_from_env(env: dict[str, str], ttl: int) -> Credentials:
    """Take this agent's own material from the minted door, then drop the rest.

    ``run_memory_mcp.sh`` mints the door exactly as for the local server. The
    bridge needs only ``{agent_id: key}`` and the sealed identity; it removes
    every server-side value from its own environment before it serves.
    """

    agent_id = env.get(ENV_AGENT_ID, "").strip()
    try:
        keys = json.loads(env.get(ENV_SIGNING_KEYS, "") or "{}")
        identity = json.loads(env.get(ENV_IDENTITY, "") or "{}")
    except ValueError as exc:
        raise RemoteBindingError(f"minted door is malformed: {exc}") from exc
    for name in (ENV_SIGNING_KEYS, ENV_IDENTITY, *SERVER_SIDE_ENV):
        env.pop(name, None)
    if not isinstance(keys, dict) or set(keys) != {agent_id}:
        raise RemoteBindingError(
            f"minted door must carry exactly the signing key of {agent_id or '<unresolved>'}"
        )
    key = keys[agent_id]
    if not isinstance(key, str) or len(key) < 16:
        raise RemoteBindingError(f"signing key for {agent_id} is missing or too short")
    if not isinstance(identity, dict) or not identity:
        raise RemoteBindingError("minted door carries no sealed identity assertion")
    return Credentials(agent_id, key, identity, ttl)


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------


def sse_messages(body: bytes) -> list[str]:
    messages: list[str] = []
    data: list[str] = []
    for line in body.decode("utf-8").splitlines():
        if line.startswith("data:"):
            data.append(line[5:].lstrip())
        elif not line.strip() and data:
            messages.append("\n".join(data))
            data = []
    if data:
        messages.append("\n".join(data))
    return messages


class AuthenticationRefused(RemoteBindingError):
    """The service refused this agent's credential."""


class RemoteBridge:
    def __init__(
        self,
        endpoint: str,
        credentials: Credentials,
        *,
        protocol_versions: Iterable[str],
        send: Send = exchange,
        out: Any = None,
    ) -> None:
        self.endpoint = endpoint
        self.credentials = credentials
        self.protocol_versions = tuple(protocol_versions)
        self._allowed = frozenset({(urlparse(endpoint).hostname or "").lower()})
        self._loopback = is_loopback(endpoint)
        self._send = send
        self._out = out if out is not None else sys.stdout
        self._lock = threading.Lock()
        self._protocol = ""

    # -- one exchange -----------------------------------------------------
    def _post(self, payload: bytes) -> tuple[int, str, bytes]:
        headers = {"Content-Type": "application/json", "Accept": ACCEPT}
        if self._protocol:
            headers["MCP-Protocol-Version"] = self._protocol
        headers.update(self.credentials.headers())
        request = urllib.request.Request(
            self.endpoint, data=payload, method="POST", headers=headers
        )
        try:
            response = self._send(
                request,
                timeout=TIMEOUT,
                allowed_https_hosts=self._allowed,
                allow_loopback_http=self._loopback,
                label="remote memory",
            )
        except urllib.error.HTTPError as exc:
            body = exc.read() if exc.fp is not None else b""
            return exc.code, (exc.headers.get("Content-Type") or "").lower(), body
        return (
            int(getattr(response, "status", 200)),
            (response.headers.get("Content-Type") or "").lower(),
            response.read(),
        )

    def exchange_once(self, message: Mapping[str, Any]) -> list[dict[str, Any]]:
        """POST one message; return the service's JSON-RPC replies.

        A 401 is re-minted once (fresh token, same identity) and then raised.
        """

        payload = json.dumps(message, separators=(",", ":")).encode("utf-8")
        status, ctype, body = self._post(payload)
        if status == 401:
            status, ctype, body = self._post(payload)
            if status == 401:
                raise AuthenticationRefused(
                    f"remote memory refused authentication for agent {self.credentials.agent_id}"
                )
        if self.credentials.secret_bytes in body:
            raise RemoteBindingError("remote response withheld: it echoed the signing key")
        if not body:
            return []
        texts = sse_messages(body) if "text/event-stream" in ctype else [body.decode("utf-8")]
        replies: list[dict[str, Any]] = []
        for text in texts:
            try:
                parsed = json.loads(text)
            except ValueError:
                continue
            if isinstance(parsed, dict):
                replies.append(parsed)
        if not replies and status >= 400:
            raise RemoteBindingError(f"remote memory answered HTTP {status}")
        for reply in replies:
            result = reply.get("result")
            if isinstance(result, dict) and isinstance(result.get("protocolVersion"), str):
                self._protocol = result["protocolVersion"]
        return replies

    # -- service identity -------------------------------------------------
    def verify_service(self, release_version: str) -> dict[str, Any]:
        """Prove the service is the bound release before serving any client."""

        init = self.exchange_once(
            {
                "jsonrpc": "2.0",
                "id": "l9-bridge-init",
                "method": "initialize",
                "params": {
                    "protocolVersion": self.protocol_versions[0],
                    "capabilities": {},
                    "clientInfo": {"name": "l9-governance-memory-bridge", "version": "1"},
                },
            }
        )
        if not init or "result" not in init[0]:
            raise RemoteBindingError(f"remote memory refused initialize: {init[:1]}")
        if self._protocol not in self.protocol_versions:
            raise RemoteBindingError(
                f"remote memory negotiated MCP revision {self._protocol!r}, "
                f"not one of {list(self.protocol_versions)}"
            )
        replies = self.exchange_once(
            {
                "jsonrpc": "2.0",
                "id": "l9-bridge-capabilities",
                "method": "tools/call",
                "params": {"name": "memory.capabilities", "arguments": {}},
            }
        )
        try:
            capabilities = json.loads(replies[0]["result"]["content"][0]["text"])
        except (IndexError, KeyError, TypeError, ValueError) as exc:
            raise RemoteBindingError(
                f"remote memory capabilities unreadable: {replies[:1]}"
            ) from exc
        expected = {
            "package_version": release_version,
            "contract_version": CONTROL_PLANE_CONTRACT,
            "remote_mcp_contract_version": REMOTE_CONTRACT,
        }
        drift = {
            key: capabilities.get(key)
            for key, value in expected.items()
            if capabilities.get(key) != value
        }
        if drift:
            raise RemoteBindingError(
                f"remote memory is not the bound release (expected {expected}, got {drift})"
            )
        return capabilities

    # -- relay ------------------------------------------------------------
    def emit(self, message: Mapping[str, Any]) -> None:
        with self._lock:
            self._out.write(json.dumps(message, separators=(",", ":")) + "\n")
            self._out.flush()

    def _error(self, request_id: Any, code: int, text: str) -> None:
        if request_id is None:
            return
        self.emit({"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": text}})

    def forward(self, line: str) -> None:
        try:
            message = json.loads(line)
        except ValueError:
            self.emit(
                {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
            )
            return
        request_id = message.get("id") if isinstance(message, dict) else None
        try:
            replies = self.exchange_once(message)
        except AuthenticationRefused as exc:
            print(f"memory_remote: {exc} — no fallback backend", file=sys.stderr)
            self._error(request_id, AUTH_REFUSED, f"{exc}; no fallback backend")
            return
        except (RemoteBindingError, urllib.error.URLError, OSError, ValueError) as exc:
            print(f"memory_remote: {exc}", file=sys.stderr)
            self._error(
                request_id,
                UNAVAILABLE,
                f"remote memory unavailable ({type(exc).__name__}); no fallback backend",
            )
            return
        for reply in replies:
            # Refusal bodies carry no id (memory-remote-mcp/v1); answer the caller's.
            if "id" not in reply or reply.get("id") is None:
                if request_id is None:
                    continue
                reply = {**reply, "id": request_id}
            self.emit(reply)

    def serve(self, stream: Iterable[str]) -> None:
        threads: list[threading.Thread] = []
        for raw in stream:
            line = raw.strip()
            if not line:
                continue
            if '"initialize"' in line:
                self.forward(line)  # the negotiated revision must exist first
                continue
            thread = threading.Thread(target=self.forward, args=(line,), daemon=True)
            thread.start()
            threads.append(thread)
        for thread in threads:
            thread.join(timeout=TIMEOUT)


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


def resolve(env: Mapping[str, str]) -> tuple[str, dict[str, Any], dict[str, str]] | None:
    """Endpoint, binding and release for the remote transport, or None (local)."""

    endpoint = requested_endpoint(env)
    if endpoint is None:
        return None
    validate_endpoint(endpoint, side_doors=forbidden_side_doors())
    binding = load_binding()
    return endpoint, binding, bound_release(binding, endpoint, env)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--check",
        action="store_true",
        help="exit 0 with 'local' or 'remote' on stdout; exit 1 naming the fix",
    )
    mode.add_argument("--serve", action="store_true", help="serve stdio until EOF")
    args = parser.parse_args(argv)
    env = os.environ
    try:
        resolved = resolve(env)
        if args.check:
            print("local" if resolved is None else "remote")
            return 0
        if resolved is None:
            raise RemoteBindingError("no remote endpoint configured: the launcher serves locally")
        endpoint, binding, release = resolved
        ttl = int(binding.get("assertion_ttl_seconds") or 300)
        credentials = credentials_from_env(env, ttl)  # type: ignore[arg-type]
        bridge = RemoteBridge(
            endpoint,
            credentials,
            protocol_versions=binding.get("http_mcp_protocol_versions") or (),
        )
        bridge.verify_service(release["version"])
    except RemoteBindingError as exc:
        print(f"memory_remote: {exc} — refuse to launch (no fallback backend)", file=sys.stderr)
        return 1
    except (urllib.error.URLError, OSError, ValueError) as exc:
        print(
            f"memory_remote: remote memory unreachable ({type(exc).__name__}: {exc}) — "
            "refuse to launch (no fallback backend)",
            file=sys.stderr,
        )
        return 1
    print(
        f"memory_remote: {credentials.agent_id} -> {REMOTE_CONTRACT} "
        f"({release['mode']}, l9-graphite-memory {release['version']})",
        file=sys.stderr,
    )
    bridge.serve(sys.stdin)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

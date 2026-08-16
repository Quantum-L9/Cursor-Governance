#!/usr/bin/env python3
"""L9 capability broker — the trusted side of the boundary.

This process is the only thing in the system that holds a credential. It sits
on the far side of the trust boundary from every agent surface and offers
exactly one kind of operation: *perform a registered capability and return a
sanitized result*.

What it deliberately does NOT offer, and never will (contract S4 / T4):

    GET  /secret/<name>          -> 404
    POST /resolve-secret         -> 404
    any route returning a value  -> does not exist

There is no handler to disable, no debug flag that prints one, and no response
path that carries secret material. A secret is read from the provider, used to
sign one outbound request, and discarded — it is never placed in a response
body, a log line, or an audit record.

Two guards run before the service will accept a single request:

1. **Boundary self-check** (contract §21). A broker running as the same
   unrestricted user as the agent is not a boundary, it is a decoration. If the
   process detects that it is inside a model-controlled runtime it refuses to
   start and says why. "Claude is not supposed to look here" is not isolation.

2. **Workload identity** (contract §4 / §20). The broker authenticates to
   Infisical with a projected, short-lived workload identity — Kubernetes
   ServiceAccount, SPIFFE JWT-SVID, or another provider-native mechanism. A
   Universal Auth client secret is explicitly rejected: adopting one here would
   just relocate the static secret rather than remove it.

Inbound requests are authenticated with :mod:`broker_identity`, authorized
against ``ops/secrets/capabilities.yaml``, executed against a FIXED upstream
contract the caller cannot influence, and sanitized on the way out.

Run:
  capability_broker.py serve --audience ccpool_<environment> --port 8787
  capability_broker.py preflight     # report posture without serving
"""

# L9-TRUSTED-OPERATOR-ONLY — raw-secret paths in this file are reachable only
# beyond the model boundary and are guarded by surface_trust.require_trusted /
# the broker's boundary self-check. The marker declares that status for review;
# it is not a bypass, and it does not disable those runtime guards.


from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import broker_identity  # noqa: E402
from capability_registry import CapabilitySpec, load_registry  # noqa: E402
from surface_trust import detected_model_markers  # noqa: E402

UPSTREAM_TIMEOUT_SECONDS = 45

# Credential-bearing response headers are dropped wholesale rather than
# inspected. Nothing an upstream sends under these names has any business
# crossing back to a model (contract §17).
FORBIDDEN_RESPONSE_HEADERS = frozenset(
    {"authorization", "proxy-authorization", "set-cookie", "www-authenticate", "x-api-key"}
)


class BrokerError(Exception):
    """Refusal with an HTTP status. Messages never contain secret material."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


# ---------------------------------------------------------------------------
# 1. Boundary self-check
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BoundaryPosture:
    isolated: bool
    reason: str
    markers: tuple[str, ...]


def boundary_posture(env: dict[str, str] | None = None) -> BoundaryPosture:
    """Decide whether this process is genuinely outside the model boundary.

    A real boundary means a separate container, service identity, namespace or
    remote service. We cannot prove that positively from inside a process, but
    we can prove the *negative* decisively: if the model runtime's own markers
    are visible here, the broker shares the agent's environment and is not
    isolated from it.

    ``L9_BROKER_ISOLATION_ATTESTED`` exists for deployments whose isolation is
    real but whose markers are inherited (a sidecar in the same pod, say). It
    names the isolation mechanism; it is not a bypass, and it cannot suppress a
    same-process detection.
    """
    source = os.environ if env is None else env
    markers = detected_model_markers(source)
    attested = (source.get("L9_BROKER_ISOLATION_ATTESTED") or "").strip()

    if markers and not attested:
        return BoundaryPosture(
            False,
            "refusing to start: model-runtime markers are visible in this process "
            f"({', '.join(markers)}). A broker sharing the agent's unrestricted runtime is "
            "not a trust boundary (contract §21).",
            markers,
        )
    if markers and attested:
        return BoundaryPosture(
            True,
            f"model markers present but isolation attested as '{attested}'",
            markers,
        )
    return BoundaryPosture(True, "no model-runtime markers detected in this process", markers)


# ---------------------------------------------------------------------------
# 2. Workload identity -> Infisical
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WorkloadIdentity:
    """How the broker authenticates to Infisical. Method name only, never material."""

    method: str
    detail: str
    identity_id: str = ""
    token_path: str = ""

    @property
    def available(self) -> bool:
        return self.method != "none"


def workload_identity(env: dict[str, str] | None = None) -> WorkloadIdentity:
    """Resolve a non-static workload identity, in the contract's preference order.

    A ``INFISICAL_CLIENT_SECRET`` in the environment is NOT accepted as a
    fallback. Silently accepting one is how the static secret comes back.
    """
    source = os.environ if env is None else env
    identity_id = (source.get("INFISICAL_IDENTITY_ID") or "").strip()

    # 1. Kubernetes Auth — projected ServiceAccount token, short-lived,
    #    mounted only into this container (contract §20).
    k8s = (source.get("INFISICAL_K8S_SA_TOKEN_PATH") or "").strip() or (
        "/var/run/secrets/kubernetes.io/serviceaccount/token"
    )
    if identity_id and Path(k8s).is_file():
        return WorkloadIdentity("kubernetes-auth", "projected ServiceAccount JWT", identity_id, k8s)

    # 2. SPIFFE JWT-SVID.
    svid = (source.get("SPIFFE_JWT_SVID_FILE") or "").strip()
    if identity_id and svid and Path(svid).is_file():
        return WorkloadIdentity("spiffe-jwt-svid", "SPIRE-issued JWT-SVID", identity_id, svid)

    # 3. Generic workload OIDC/JWT identity.
    oidc = (source.get("INFISICAL_JWT_IDENTITY_TOKEN_FILE") or "").strip()
    if identity_id and oidc and Path(oidc).is_file():
        return WorkloadIdentity("oidc-workload-identity", "provider OIDC token", identity_id, oidc)

    if (source.get("INFISICAL_CLIENT_SECRET") or "").strip():
        return WorkloadIdentity(
            "none",
            "INFISICAL_CLIENT_SECRET is present but REFUSED: a static Universal Auth "
            "secret is not a workload identity and must not be the broker's runtime "
            "credential (contract §4).",
        )
    return WorkloadIdentity(
        "none",
        "no workload identity available (want Kubernetes Auth, SPIFFE, or workload OIDC)",
    )


class SecretProvider:
    """Resolves registered secret names inside the trusted boundary. Never exported.

    Deliberately minimal: values live in local variables for the duration of one
    upstream call. There is no cache written to disk, no accessor that returns a
    dict of values to a caller, and no ``__repr__`` that could surface one.
    """

    def __init__(self, identity: WorkloadIdentity, env: dict[str, str] | None = None) -> None:
        if not identity.available:
            raise BrokerError(503, f"broker has no workload identity: {identity.detail}")
        self.identity = identity
        self.env = os.environ if env is None else env
        self._token: str | None = None
        self._token_expires = 0.0

    def _access_token(self) -> str:
        """Exchange the projected workload JWT for a short-lived Infisical token.

        Cached in memory only, bounded by the provider's own TTL, and never
        crossing the trust boundary (contract S8).
        """
        now = time.time()
        if self._token and now < self._token_expires - 30:
            return self._token
        host = (self.env.get("INFISICAL_SITE_URL") or "https://app.infisical.com").rstrip("/")
        jwt = Path(self.identity.token_path).read_text(encoding="utf-8").strip()
        route = {
            "kubernetes-auth": "/api/v1/auth/kubernetes-auth/login",
            "spiffe-jwt-svid": "/api/v1/auth/jwt-auth/login",
            "oidc-workload-identity": "/api/v1/auth/oidc-auth/login",
        }[self.identity.method]
        body = urllib.parse.urlencode(
            {"identityId": self.identity.identity_id, "jwt": jwt}
        ).encode("ascii")
        request = urllib.request.Request(
            f"{host}{route}",
            data=body,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise BrokerError(503, f"workload identity login failed: {type(exc).__name__}") from exc
        token = payload.get("accessToken")
        if not token:
            raise BrokerError(503, "workload identity login returned no access token")
        self._token = str(token)
        self._token_expires = now + float(payload.get("expiresIn") or 300)
        return self._token

    def resolve(self, name: str) -> str:
        """Return one registered secret VALUE. Trusted side only — never a response."""
        host = (self.env.get("INFISICAL_SITE_URL") or "https://app.infisical.com").rstrip("/")
        query = urllib.parse.urlencode(
            {
                "workspaceId": self.env.get("INFISICAL_PROJECT_ID", ""),
                "environment": self.env.get("INFISICAL_ENV", "prod"),
                "secretPath": self.env.get("INFISICAL_SECRET_PATH", "/"),
                "viewSecretValue": "true",
            }
        )
        request = urllib.request.Request(
            f"{host}/api/v3/secrets/raw/{urllib.parse.quote(name)}?{query}",
            method="GET",
            headers={"Authorization": f"Bearer {self._access_token()}"},
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise BrokerError(503, f"secret resolution failed for a registered ref: {type(exc).__name__}") from exc
        value = (payload.get("secret") or {}).get("secretValue")
        if not value:
            raise BrokerError(503, "registered ref resolved empty")
        return str(value)


# ---------------------------------------------------------------------------
# 3. Parameter validation — the caller's only influence, tightly bounded
# ---------------------------------------------------------------------------

_VALIDATORS: dict[str, re.Pattern[str]] = {
    "digits": re.compile(r"\A[0-9]{1,12}\Z"),
    "sha": re.compile(r"\A[0-9a-f]{7,40}\Z"),
    "slug": re.compile(r"\A[A-Za-z0-9._-]{1,100}\Z"),
    "git_ref": re.compile(r"\A[A-Za-z0-9._/-]{1,200}\Z"),
    "text": re.compile(r"\A[^\x00]{0,65536}\Z", re.DOTALL),
}


def validate_params(spec: CapabilitySpec, supplied: dict[str, Any]) -> dict[str, str]:
    """Accept only registry-declared caller params, each matching its validator.

    Anything not declared as ``source: caller`` is refused outright — that is
    how ``group_id`` and ``project`` stay broker-derived and a session cannot
    reach another repository's data.
    """
    allowed = set(spec.caller_params())
    clean: dict[str, str] = {}
    for key, value in (supplied or {}).items():
        if key not in allowed:
            raise BrokerError(
                400, f"parameter '{key}' is not caller-supplied for capability '{spec.id}'"
            )
        rule = spec.params[key]
        text = str(value)
        max_bytes = int(rule.get("max_bytes", 4096))
        if len(text.encode("utf-8")) > max_bytes:
            raise BrokerError(400, f"parameter '{key}' exceeds its declared size limit")
        pattern = _VALIDATORS.get(str(rule.get("validate", "slug")))
        if pattern is None:
            raise BrokerError(500, f"capability '{spec.id}' declares an unknown validator")
        if not pattern.match(text):
            raise BrokerError(400, f"parameter '{key}' failed validation")
        maximum = rule.get("max")
        if maximum is not None and text.isdigit() and int(text) > int(maximum):
            raise BrokerError(400, f"parameter '{key}' exceeds its declared maximum")
        clean[key] = text
    return clean


# ---------------------------------------------------------------------------
# 4. Response sanitizers — structured subsets, not regex hope (contract §17)
# ---------------------------------------------------------------------------


def _sonar_issue_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    """Rebuild the Sonar response from named fields, discarding everything else."""
    return {
        "total": payload.get("total"),
        "p": payload.get("p"),
        "ps": payload.get("ps"),
        "issues": [
            {
                key: issue.get(key)
                for key in (
                    "key", "rule", "severity", "component", "line", "message",
                    "type", "status", "effort", "textRange", "flows",
                )
            }
            for issue in payload.get("issues") or []
        ],
        "rules": [
            {key: rule.get(key) for key in ("key", "name", "severity", "type", "htmlDesc")}
            for rule in payload.get("rules") or []
        ],
        "projectStatus": payload.get("projectStatus"),
        "component": payload.get("component"),
    }


def _semgrep_findings(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "findings": [
            {
                key: finding.get(key)
                for key in (
                    "id", "rule_name", "severity", "confidence", "path", "line",
                    "message", "state",
                )
            }
            for finding in payload.get("findings") or []
        ]
    }


def _mcp_envelope(payload: dict[str, Any]) -> dict[str, Any]:
    """MCP responses pass through by shape, with auth-bearing envelope keys dropped."""
    return {key: value for key, value in payload.items() if key in ("jsonrpc", "id", "result", "error")}


def _github_pr_view(payload: Any) -> Any:
    keys = (
        "number", "state", "title", "draft", "mergeable", "mergeable_state",
        "head", "base", "html_url", "check_runs", "total_count", "conclusion", "body",
    )
    if isinstance(payload, list):
        return [{k: item.get(k) for k in keys if k in item} for item in payload]
    return {k: payload.get(k) for k in keys if k in payload}


SANITIZERS: dict[str, Callable[[Any], Any]] = {
    "sonar_issue_snapshot": _sonar_issue_snapshot,
    "semgrep_findings": _semgrep_findings,
    "mcp_envelope": _mcp_envelope,
    "github_pr_view": _github_pr_view,
}


def scrub(spec: CapabilitySpec, payload: Any, known_values: list[str]) -> Any:
    """Sanitize, then belt-and-braces: assert no live credential survived.

    The structured subset above is the actual control. The equality sweep below
    is a backstop for the case a sanitizer is later widened carelessly — if a
    resolved value appears anywhere in the serialized response, the response is
    dropped rather than redacted, because a leak means the sanitizer is wrong.
    """
    sanitizer = SANITIZERS.get(spec.sanitizer)
    if sanitizer is None:
        raise BrokerError(500, f"capability '{spec.id}' declares an unknown sanitizer")
    result = sanitizer(payload)
    serialized = json.dumps(result, default=str)
    for value in known_values:
        if value and value in serialized:
            raise BrokerError(500, "response withheld: sanitizer let credential material through")
    return result


# ---------------------------------------------------------------------------
# 5. Execution
# ---------------------------------------------------------------------------


class Broker:
    def __init__(self, audience: str, env: dict[str, str] | None = None) -> None:
        self.env = os.environ if env is None else env
        self.audience = audience
        self.registry = load_registry()
        self.identity = workload_identity(self.env)
        self.expected_org = (self.env.get("L9_BROKER_EXPECTED_ORG") or "").strip() or None
        self.jwks = broker_identity.JWKSCache(
            (self.env.get("L9_BROKER_JWKS_URL") or broker_identity.DEFAULT_JWKS_URL)
        )
        self._provider: SecretProvider | None = None
        self.audit: list[dict[str, Any]] = []

    @property
    def provider(self) -> SecretProvider:
        if self._provider is None:
            self._provider = SecretProvider(self.identity, self.env)
        return self._provider

    def authenticate(self, authorization: str | None) -> broker_identity.SessionClaims:
        if not authorization or not authorization.lower().startswith("bearer "):
            raise BrokerError(401, "missing session assertion")
        try:
            return broker_identity.verify(
                authorization.split(" ", 1)[1].strip(),
                expected_audience=self.audience,
                expected_org=self.expected_org,
                jwks=self.jwks,
            )
        except broker_identity.IdentityError as exc:
            raise BrokerError(401, f"session identity rejected: {exc}") from exc

    def handle(self, claims: broker_identity.SessionClaims, body: dict[str, Any]) -> dict[str, Any]:
        capability_id = str(body.get("capability") or "")
        spec = self.registry.get(capability_id)
        if spec is None:
            self._record(claims, capability_id, "DENY", "unregistered capability")
            raise BrokerError(404, f"capability '{capability_id}' is not registered")

        params = validate_params(spec, body.get("params") or {})
        try:
            result = self._execute(spec, params)
        except BrokerError:
            self._record(claims, capability_id, "ERROR", "upstream or provider failure")
            raise
        self._record(claims, capability_id, "ALLOW", "executed")
        return {"capability": capability_id, "result": result}

    def _execute(self, spec: CapabilitySpec, params: dict[str, str]) -> Any:
        """Perform the fixed upstream operation. Host and credential are not negotiable."""
        path = spec.paths[0]
        method = sorted(spec.methods)[0]
        if not spec.allows(method, path):
            raise BrokerError(500, "registry inconsistency: default operation not allowed")

        values = [self.provider.resolve(ref) for ref in spec.secret_refs]
        # The URL is assembled from the registry's own host and an allow-listed
        # path. No caller string reaches the host or scheme, so there is no
        # redirect or SSRF surface (contract §8).
        url = f"https://{spec.upstream_host}{spec.base_path}{path}"
        if params and method == "GET":
            url = f"{url}?{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(url, method=method)
        request.add_header("Authorization", f"Bearer {values[0]}")
        try:
            with urllib.request.urlopen(request, timeout=UPSTREAM_TIMEOUT_SECONDS) as response:  # noqa: S310
                raw = response.read(spec.max_response_bytes + 1)
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            raise BrokerError(502, f"upstream failed: {type(exc).__name__}") from exc
        if len(raw) > spec.max_response_bytes:
            raise BrokerError(502, "upstream response exceeded the declared limit")
        return scrub(spec, json.loads(raw.decode("utf-8")), values)

    def _record(self, claims: broker_identity.SessionClaims, capability: str, decision: str, detail: str) -> None:
        """Audit exactly what contract §5 lists. The assertion itself is never stored."""
        entry = dict(claims.audit_record())
        entry.update(
            {
                "capability": capability,
                "decision": decision,
                "detail": detail,
                "timestamp": int(time.time()),
            }
        )
        self.audit.append(entry)


class _Handler(BaseHTTPRequestHandler):
    broker: Broker

    server_version = "L9CapabilityBroker/1.0"

    def _send(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path == "/healthz":
            self._send(200, {"status": "ok", "capabilities": len(self.broker.registry)})
            return
        # Every other GET, including anything shaped like /secret/<name>, is a
        # 404 because no such route is defined anywhere in this service.
        self._send(404, {"error": "no such route; this broker exposes no secret-read API"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/capability":
            self._send(404, {"error": "no such route; this broker exposes no secret-read API"})
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
            claims = self.broker.authenticate(self.headers.get("Authorization"))
            self._send(200, self.broker.handle(claims, body))
        except BrokerError as exc:
            self._send(exc.status, {"error": exc.message})
        except (ValueError, KeyError):
            self._send(400, {"error": "malformed request"})

    def log_message(self, fmt: str, *args: Any) -> None:
        """Access logs carry method and path only — never headers, never bodies."""
        sys.stderr.write(f"broker {self.address_string()} {fmt % args}\n")


def preflight(audience: str | None, env: dict[str, str] | None = None) -> tuple[int, dict[str, Any]]:
    """Report posture without serving. Used by tests and by operators."""
    source = os.environ if env is None else env
    posture = boundary_posture(source)
    identity = workload_identity(source)
    report = {
        "boundary_isolated": posture.isolated,
        "boundary_detail": posture.reason,
        "workload_identity_method": identity.method,
        "workload_identity_detail": identity.detail,
        "audience": audience or "<unset>",
        "capabilities": load_registry().ids(),
    }
    ready = posture.isolated and identity.available and bool(audience)
    report["status"] = "READY" if ready else "BLOCKED"
    return (0 if ready else 1), report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="L9 capability broker (trusted side).")
    parser.add_argument("command", choices=["serve", "preflight"])
    parser.add_argument("--audience", help="exact ccpool_<environment> this broker serves")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--bind", default="127.0.0.1")
    args = parser.parse_args(argv)

    audience = args.audience or (os.environ.get("L9_BROKER_AUDIENCE") or "").strip() or None

    if args.command == "preflight":
        code, report = preflight(audience)
        print(json.dumps(report, indent=2))
        return code

    posture = boundary_posture()
    if not posture.isolated:
        print(f"capability_broker: {posture.reason}", file=sys.stderr)
        return 1
    if not audience:
        print("capability_broker: --audience ccpool_<environment> is required", file=sys.stderr)
        return 2

    _Handler.broker = Broker(audience)
    print(
        f"capability broker listening on {args.bind}:{args.port} "
        f"audience={audience} identity={_Handler.broker.identity.method}"
    )
    ThreadingHTTPServer((args.bind, args.port), _Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Model-side capability client — the ONLY secret-adjacent API an agent gets.

This module is designed to be safe to hand an LLM. Read the public surface and
note what is missing: there is no ``get_secret``, no ``resolve``, no ``export``,
no name-to-value call of any shape. There is no private helper that could be
coaxed into one either, because this process never speaks to Infisical, never
reads a credential, and holds nothing worth stealing. It asks a broker to
*perform an operation* and hands back the sanitized result (contract S4).

    agent  ->  capability_client  ->  L9 broker  ->  [trust boundary]  ->  secret

Everything left of the boundary is assumed hostile. The client therefore carries
only:

  * the broker URL (not a secret),
  * a caller identity assertion it did not mint and cannot forge into more
    authority than the platform already gave the session,
  * the capability id it wants.

Broker authentication uses whatever signed identity the *platform* issues to the
session — never a credential pasted into the environment. :func:`session_identity`
reports which mechanism is available; when none is, every capability degrades
and the client says so plainly rather than falling back to a static secret
(contract §19, §28).

Usage:
  capability_client.py --check
  capability_client.py --check --require sonar.read_issues,graphiti.query
  capability_client.py --invoke sonar.read_issues --param branch=main
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from capability_registry import CapabilityRegistry, load_registry  # noqa: E402
from surface_trust import classify  # noqa: E402

#: Capability status vocabulary. Shared with the shell bootstrap so a surface
#: reports the same three words everywhere (contract R5).
ENABLED = "ENABLED"
DEGRADED = "DEGRADED"
UNAVAILABLE = "UNAVAILABLE"
BLOCKED = "BLOCKED"

BROKER_URL_ENV = "L9_CAPABILITY_BROKER_URL"
BROKER_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class SessionIdentity:
    """How this session proves itself to the broker.

    ``token`` is a platform-issued session assertion, not a credential the
    operator pasted. It is deliberately *not* a secret in the S3 sense: the
    session can already read it, it authenticates only to the broker, and it
    grants no direct access to Infisical (contract §6). It is never logged,
    never written to a receipt, and never echoed.
    """

    method: str
    token: str | None
    detail: str

    @property
    def available(self) -> bool:
        return bool(self.token)


def session_identity(env: dict[str, str] | None = None) -> SessionIdentity:
    """Discover a platform-issued session identity, in order of trustworthiness.

    Order matters: a signed, broker-verifiable assertion beats a bare
    environment id. Nothing here mints, derives or persists an identity — if the
    platform issues none, that is reported as such and the caller degrades.
    """
    source = os.environ if env is None else env

    # 1. L9 self-hosted Claude (CCR pool). The session worker JWT is ES256,
    #    issued by `ccr`, audienced to the exact ccpool_<environment>, and
    #    verifiable by the broker against the Anthropic JWKS (contract §5).
    pool = (source.get("CLAUDE_CODE_REMOTE_ENVIRONMENT_ID") or "").strip()
    token_file = (source.get("CLAUDE_SESSION_IDENTITY_TOKEN_FILE") or "").strip()
    if token_file and pool.startswith("ccpool_"):
        try:
            token = Path(token_file).read_text(encoding="utf-8").strip()
        except OSError:
            token = ""
        if token:
            return SessionIdentity("ccr-session-jwt", token, f"self-hosted pool {pool}")

    # 2. A workload identity token projected into a trusted runtime (k8s SA,
    #    SPIFFE JWT-SVID). Present only outside the model sandbox.
    for var in ("L9_WORKLOAD_IDENTITY_TOKEN_FILE", "SPIFFE_JWT_SVID_FILE"):
        path = (source.get(var) or "").strip()
        if not path:
            continue
        try:
            token = Path(path).read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if token:
            return SessionIdentity("workload-identity-jwt", token, var)

    return SessionIdentity(
        "none",
        None,
        "no platform-issued session identity; this runtime cannot authenticate to a broker "
        "without placing a reusable secret in the sandbox (BLOCKED_BY_PLATFORM)",
    )


def broker_url(env: dict[str, str] | None = None) -> str:
    source = os.environ if env is None else env
    return (source.get(BROKER_URL_ENV) or "").strip().rstrip("/")


@dataclass(frozen=True)
class CapabilityStatus:
    capability: str
    status: str
    detail: str

    def line(self) -> str:
        return f"{self.capability}: {self.status} ({self.detail})"


class CapabilityClient:
    """Talks to the broker. Cannot talk to a secret provider — by construction."""

    def __init__(
        self,
        registry: CapabilityRegistry | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self.env = os.environ if env is None else env
        self.registry = registry if registry is not None else load_registry()
        self.trust = classify(env=self.env)
        self.url = broker_url(self.env)
        self.identity = session_identity(self.env)

    # -- availability --------------------------------------------------------

    def status(self, capability: str) -> CapabilityStatus:
        """Report a capability without invoking it. Never contacts an upstream."""
        spec = self.registry.get(capability)
        if spec is None:
            return CapabilityStatus(
                capability, UNAVAILABLE, "not registered in ops/secrets/capabilities.yaml"
            )
        if self.trust.trust_class not in spec.surfaces:
            return CapabilityStatus(
                capability, UNAVAILABLE, f"not offered to trust class {self.trust.trust_class}"
            )
        if not self.url:
            return CapabilityStatus(
                capability, DEGRADED, f"no broker configured ({BROKER_URL_ENV} unset)"
            )
        if not self.identity.available:
            # The platform-blocked case. It is DEGRADED rather than ENABLED
            # precisely so an outage can never be mistaken for a passing check
            # (contract §18).
            return CapabilityStatus(capability, BLOCKED, self.identity.detail)
        ok, detail = self._probe()
        if not ok:
            return CapabilityStatus(capability, DEGRADED, detail)
        return CapabilityStatus(
            capability, ENABLED, f"broker {self.url} via {self.identity.method}"
        )

    def _probe(self) -> tuple[bool, str]:
        """Ask the broker whether it is alive. Returns no secret-derived data."""
        try:
            request = urllib.request.Request(f"{self.url}/healthz", method="GET")
            self._authorize(request)
            with urllib.request.urlopen(request, timeout=BROKER_TIMEOUT_SECONDS) as response:  # noqa: S310
                if response.status == 200:
                    return True, "broker healthy"
                return False, f"broker health HTTP {response.status}"
        except (urllib.error.URLError, OSError, TimeoutError, ValueError) as exc:
            return False, f"broker unreachable: {type(exc).__name__}"

    # -- invocation ----------------------------------------------------------

    def invoke(self, capability: str, params: dict[str, str] | None = None) -> dict:
        """Ask the broker to perform a registered operation and return its result.

        The response has already been sanitized broker-side. Nothing in this
        method can widen the request: the upstream host, path set, method,
        credential and repository scope are all fixed by the registry entry on
        the broker's copy — the caller supplies only registry-declared params
        (contract §8).
        """
        spec = self.registry.get(capability)
        if spec is None:
            raise LookupError(f"capability '{capability}' is not registered")

        status = self.status(capability)
        if status.status in (UNAVAILABLE, BLOCKED):
            raise RuntimeError(f"capability '{capability}' {status.status}: {status.detail}")

        payload = json.dumps(
            {"capability": capability, "params": params or {}},
            separators=(",", ":"),
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.url}/capability",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        self._authorize(request)
        try:
            with urllib.request.urlopen(request, timeout=BROKER_TIMEOUT_SECONDS) as response:  # noqa: S310
                body = response.read(spec.max_response_bytes + 1)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:400]
            raise RuntimeError(f"broker denied '{capability}' (HTTP {exc.code}): {detail}") from exc
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            raise RuntimeError(
                f"broker unreachable for '{capability}': {type(exc).__name__}"
            ) from exc

        if len(body) > spec.max_response_bytes:
            raise RuntimeError(f"broker response for '{capability}' exceeded declared limit")
        return json.loads(body.decode("utf-8"))

    def _authorize(self, request: urllib.request.Request) -> None:
        """Attach the session assertion. The only header this client ever sets."""
        if self.identity.token:
            request.add_header("Authorization", f"Bearer {self.identity.token}")
        request.add_header("X-L9-Surface", self.trust.surface)


def _split(raw: str | None) -> list[str]:
    return [item.strip() for item in (raw or "").split(",") if item.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="L9 capability client (never returns secrets).")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="report capability availability")
    mode.add_argument("--invoke", help="capability id to invoke")
    parser.add_argument("--require", help="comma-separated capability ids that must be ENABLED")
    parser.add_argument("--param", action="append", default=[], help="key=value (repeatable)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    client = CapabilityClient()

    if args.check:
        wanted = _split(args.require) or client.registry.ids()
        results = [client.status(name) for name in wanted]
        if args.json:
            print(json.dumps([r.__dict__ for r in results], indent=2))
        else:
            print(
                f"capability plane: surface={client.trust.surface} "
                f"trust={client.trust.trust_class} broker={client.url or '<unset>'} "
                f"identity={client.identity.method}"
            )
            for result in results:
                print(f"  {result.line()}")
        if not args.require:
            return 0
        # Required capabilities must be ENABLED. DEGRADED and BLOCKED both fail
        # the requirement — an outage is never reported as success.
        return 0 if all(r.status == ENABLED for r in results) else 1

    params: dict[str, str] = {}
    for item in args.param:
        key, _, value = item.partition("=")
        if not key or not _:
            print(f"capability_client: bad --param '{item}' (want key=value)", file=sys.stderr)
            return 2
        params[key] = value
    try:
        print(json.dumps(client.invoke(args.invoke, params), indent=2))
    except (LookupError, RuntimeError) as exc:
        print(f"capability_client: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

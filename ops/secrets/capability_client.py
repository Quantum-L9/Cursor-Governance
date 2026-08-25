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

_OPS_LIB = HERE.parent / "lib"
if str(_OPS_LIB) not in sys.path:
    sys.path.insert(0, str(_OPS_LIB))

from safe_https import exchange  # noqa: E402

#: Capability status vocabulary. Shared with the shell bootstrap so a surface
#: reports the same words everywhere (contract R5).
#:
#: BLOCKED_BY_PLATFORM is deliberately distinct from DEGRADED (INV-4). DEGRADED
#: says "this deployment is missing something you can supply"; BLOCKED_BY_PLATFORM
#: says "this runtime cannot supply it at all, and no environment field will
#: change that". Collapsing the two sent operators to the account environment
#: field to fix something the field cannot fix (audit B-10).
ENABLED = "ENABLED"
DEGRADED = "DEGRADED"
UNAVAILABLE = "UNAVAILABLE"
BLOCKED_BY_PLATFORM = "BLOCKED_BY_PLATFORM"
#: Retained so existing string comparisons keep working; new code uses the
#: explicit name above.
BLOCKED = BLOCKED_BY_PLATFORM

#: Process exit codes for --check. A caller must be able to tell "fix your
#: config" from "this surface can never do this" without parsing prose.
EXIT_OK = 0
EXIT_DEGRADED = 3
EXIT_BLOCKED_BY_PLATFORM = 4

#: Where an operator goes when a capability reports BLOCKED_BY_PLATFORM. This is
#: a repository path rather than a bare issue number so the reference cannot rot
#: into a dangling link; the document names the live tracking issue.
PLATFORM_BLOCK_TRACKING = "docs/DEGRADED_MODE_CONTRACT.md#hosted-surface-identity"

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
    #: Machine-readable classification for the unavailable case. Empty when an
    #: identity was obtained. These three fields exist so an operator is told
    #: what kind of problem this is without reading prose (WS-5.1).
    reason: str = ""
    remediation: str = ""
    tracking: str = ""

    @property
    def available(self) -> bool:
        return bool(self.token)

    @property
    def terminal(self) -> bool:
        """True when nothing available to this repository or operator can produce
        an identity.

        A hosted surface issues none by design, so its capabilities are
        BLOCKED_BY_PLATFORM. An unconfigured self-hosted runtime has merely not
        been given one yet — that is DEGRADED, and reporting it as
        platform-blocked would convert a fixable gap into an un-actionable one,
        which is the same overstatement in the opposite direction from the
        defect this class of status exists to correct.
        """
        return self.remediation == "none_available_in_repo"


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

    # 3. Nothing issued one. Classify WHY, because the two cases need different
    #    responses. A hosted surface (Anthropic cloud_default) issues no session
    #    identity at all, so this is terminal and non-retryable: no broker URL,
    #    no network change and no environment field will produce one. A
    #    self-hosted or unknown runtime may simply be misconfigured.
    hosted = (source.get("CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE") or "").strip()
    if hosted == "cloud_default":
        return SessionIdentity(
            "none",
            None,
            "hosted surface issues no broker-verifiable session identity; capabilities are "
            "BLOCKED_BY_PLATFORM and cannot be enabled from this repository",
            reason="hosted_surface_issues_no_session_identity",
            remediation="none_available_in_repo",
            tracking=PLATFORM_BLOCK_TRACKING,
        )
    return SessionIdentity(
        "none",
        None,
        "no platform-issued session identity; this runtime cannot authenticate to a broker "
        "without placing a reusable secret in the sandbox (BLOCKED_BY_PLATFORM)",
        reason="no_session_identity_available",
        remediation="run on a self-hosted ccpool_* environment, or project a workload identity",
        tracking=PLATFORM_BLOCK_TRACKING,
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
        # Identity is evaluated BEFORE the broker URL, and the order is load-
        # bearing. A runtime that can never mint a broker-verifiable identity is
        # BLOCKED_BY_PLATFORM whether or not a URL happens to be configured.
        # Checking the URL first reported that runtime as "no broker configured"
        # — which reads as a missing environment field and sent operators to fix
        # something the field cannot fix (audit B-10, WS-5.1).
        if not self.identity.available and self.identity.terminal:
            return CapabilityStatus(capability, BLOCKED_BY_PLATFORM, self.identity.detail)
        if not self.url:
            return CapabilityStatus(
                capability, DEGRADED, f"no broker configured ({BROKER_URL_ENV} unset)"
            )
        if not self.identity.available:
            # A broker is configured but this runtime has no identity yet. That
            # is the operator's to close, so it degrades rather than blocks.
            return CapabilityStatus(capability, DEGRADED, self.identity.detail)
        ok, detail = self._probe()
        if not ok:
            return CapabilityStatus(capability, DEGRADED, detail)
        return CapabilityStatus(
            capability, ENABLED, f"broker {self.url} via {self.identity.method}"
        )

    def _probe(self) -> tuple[bool, str]:
        """Make an AUTHENTICATED broker call and return no secret-derived data.

        This hits ``/whoami``, not ``/healthz``: a capability is ENABLED only
        when the broker VERIFIES this session's identity, never on mere
        reachability. An unauthenticated ``/healthz`` 200 proves the process is
        up, which is exactly the reachability-is-not-health failure this probe
        must not repeat. A 401 here is the honest, observable authentication
        failure — the caller degrades, it does not fall back to a static secret.
        """
        try:
            request = urllib.request.Request(f"{self.url}/whoami", method="GET")
            self._authorize(request)
            with exchange(
                request,
                timeout=BROKER_TIMEOUT_SECONDS,
                allow_loopback_http=True,
                label="broker whoami URL",
            ) as response:
                if response.status == 200:
                    return True, "broker verified this session identity"
                return False, f"broker readiness HTTP {response.status}"
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                return False, "broker rejected this session identity (401)"
            return False, f"broker readiness HTTP {exc.code}"
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
            with exchange(
                request,
                timeout=BROKER_TIMEOUT_SECONDS,
                allow_loopback_http=True,
                label="broker capability URL",
            ) as response:
                body = response.read()[: spec.max_response_bytes + 1]
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
    parser.add_argument(
        "--allow-degraded",
        action="store_true",
        help=(
            "exit 0 despite DEGRADED capabilities, printing the tolerated set. "
            "Does NOT tolerate BLOCKED_BY_PLATFORM, which stays exit 4 (INV-4)."
        ),
    )
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

        blocked = [r for r in results if r.status == BLOCKED_BY_PLATFORM]
        degraded = [r for r in results if r.status in (DEGRADED, UNAVAILABLE)]

        # The platform-blocked block is printed whenever it applies, in a fixed
        # machine-greppable shape, so the operator is not left inferring the
        # class of failure from prose (WS-5.1).
        if blocked and not args.json:
            print(f"state={BLOCKED_BY_PLATFORM}")
            print(f"reason={client.identity.reason or 'unknown'}")
            print(f"remediation={client.identity.remediation or 'unknown'}")
            print(f"tracking={client.identity.tracking or 'unknown'}")

        if args.require:
            # Backward-compatible contract for callers that name what they need:
            # every required capability must be ENABLED, anything else exits 1.
            return EXIT_OK if all(r.status == ENABLED for r in results) else 1

        # Survey mode. This used to `return 0` unconditionally, so a caller that
        # omitted --require read a total capability outage as success (B-19).
        if blocked:
            # --allow-degraded deliberately does not rescue this: a state nothing
            # in this repository can repair must never exit 0 (INV-4).
            return EXIT_BLOCKED_BY_PLATFORM
        if degraded:
            if args.allow_degraded:
                print("tolerated (--allow-degraded): " + ", ".join(r.capability for r in degraded))
                return EXIT_OK
            return EXIT_DEGRADED
        return EXIT_OK

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

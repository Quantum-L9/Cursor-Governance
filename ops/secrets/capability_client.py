#!/usr/bin/env python3
"""Model-side capability client — the ONLY secret-adjacent API an agent gets.

This module is designed to be safe to hand an LLM. Read the public surface and
note what is missing: there is no ``get_secret``, no ``resolve``, no ``export``,
no name-to-value call of any shape. There is no private helper that could be
coaxed into one either, because this process never speaks to Infisical, never
reads a credential, and holds nothing worth stealing.

The L9 capability-broker experiment never shipped. Every registered capability
this client reports is UNAVAILABLE with that fact in ``detail``. Do not paste a
secret to work around it. Graphiti memory uses ``GRAPHITI_MCP_URL`` with no
bearer; authenticated Sonar / Semgrep AppSec / Context7 are not delivered.

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
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from capability_registry import CapabilityRegistry, load_registry  # noqa: E402
from surface_trust import classify  # noqa: E402

#: Capability status vocabulary. Shared with the shell bootstrap so a surface
#: reports the same words everywhere (contract R5).
#:
#: BLOCKED_BY_PLATFORM is retained so existing string comparisons keep working.
#: After broker retirement, registered capabilities report UNAVAILABLE, not
#: BLOCKED_BY_PLATFORM: the experiment is over, not waiting for identity.
ENABLED = "ENABLED"
DEGRADED = "DEGRADED"
UNAVAILABLE = "UNAVAILABLE"
BLOCKED_BY_PLATFORM = "BLOCKED_BY_PLATFORM"
BLOCKED = BLOCKED_BY_PLATFORM

EXIT_OK = 0
EXIT_DEGRADED = 3
EXIT_BLOCKED_BY_PLATFORM = 4

PLATFORM_BLOCK_TRACKING = "docs/DEGRADED_MODE_CONTRACT.md#hosted-surface-identity"

BROKER_URL_ENV = "L9_CAPABILITY_BROKER_URL"

RETIRED_DETAIL = (
    "capability broker experiment retired (never shipped); "
    "do not paste a secret to work around this"
)


@dataclass(frozen=True)
class SessionIdentity:
    """How this session would have proved itself to the retired broker.

    Retained so diagnostics still classify hosted vs self-hosted identity.
    ``token`` is never a secret in the S3 sense and is never logged.
    """

    method: str
    token: str | None
    detail: str
    reason: str = ""
    remediation: str = ""
    tracking: str = ""

    @property
    def available(self) -> bool:
        return bool(self.token)

    @property
    def terminal(self) -> bool:
        return self.remediation == "none_available_in_repo"


def session_identity(env: dict[str, str] | None = None) -> SessionIdentity:
    """Discover a platform-issued session identity (diagnostic only)."""
    source = os.environ if env is None else env

    pool = (source.get("CLAUDE_CODE_REMOTE_ENVIRONMENT_ID") or "").strip()
    token_file = (source.get("CLAUDE_SESSION_IDENTITY_TOKEN_FILE") or "").strip()
    if token_file and pool.startswith("ccpool_"):
        try:
            token = Path(token_file).read_text(encoding="utf-8").strip()
        except OSError:
            token = ""
        if token:
            return SessionIdentity("ccr-session-jwt", token, f"self-hosted pool {pool}")

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

    hosted = (source.get("CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE") or "").strip()
    if hosted == "cloud_default":
        return SessionIdentity(
            "none",
            None,
            "hosted surface issues no broker-verifiable session identity; "
            "the capability broker is retired and cannot be enabled from this repository",
            reason="hosted_surface_issues_no_session_identity",
            remediation="none_available_in_repo",
            tracking=PLATFORM_BLOCK_TRACKING,
        )
    return SessionIdentity(
        "none",
        None,
        "no platform-issued session identity; the capability broker is retired",
        reason="no_session_identity_available",
        remediation="none — capability broker experiment retired (never shipped)",
        tracking=PLATFORM_BLOCK_TRACKING,
    )


def broker_url(env: dict[str, str] | None = None) -> str:
    """Read leftover ``L9_CAPABILITY_BROKER_URL``. Setting it does not enable anything."""
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
    """Reports named capabilities. Cannot talk to a secret provider — by construction.

    After broker retirement this client never probes a host and never returns ENABLED.
    """

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
        return CapabilityStatus(capability, UNAVAILABLE, RETIRED_DETAIL)

    def invoke(self, capability: str, params: dict[str, str] | None = None) -> dict:
        """Refuse. The broker that would have executed this never shipped."""
        del params
        spec = self.registry.get(capability)
        if spec is None:
            raise LookupError(f"capability '{capability}' is not registered")
        status = self.status(capability)
        raise RuntimeError(f"capability '{capability}' {status.status}: {status.detail}")


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
            "exit 0 despite DEGRADED or UNAVAILABLE capabilities, printing the tolerated set. "
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
                f"trust={client.trust.trust_class} broker=retired "
                f"identity={client.identity.method}"
            )
            for result in results:
                print(f"  {result.line()}")

        blocked = [r for r in results if r.status == BLOCKED_BY_PLATFORM]
        degraded = [r for r in results if r.status in (DEGRADED, UNAVAILABLE)]

        if blocked and not args.json:
            print(f"state={BLOCKED_BY_PLATFORM}")
            print(f"reason={client.identity.reason or 'unknown'}")
            print(f"remediation={client.identity.remediation or 'unknown'}")
            print(f"tracking={client.identity.tracking or 'unknown'}")

        if args.require:
            return EXIT_OK if all(r.status == ENABLED for r in results) else 1

        if blocked:
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

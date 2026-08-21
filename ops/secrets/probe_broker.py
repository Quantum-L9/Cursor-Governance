#!/usr/bin/env python3
"""Tell an identity blocker apart from a reachability blocker.

Three independent things must hold before any brokered capability works:

    1. identity      the platform issues a session assertion the broker can verify
    2. configuration L9_CAPABILITY_BROKER_URL names a broker
    3. reachability  that broker host resolves and answers

The audit could not distinguish (3)'s two failure modes from the client side —
"not deployed" and "blocked upstream" both surface as a `502 CONNECT` from the
egress gateway (unknown U-4). This probe reports the distinction it CAN make:
DNS. `broker.quantumaipartners.com` raises `gaierror` while every other upstream
in the registry resolves from the same runtime, which is the signature of a host
that does not exist rather than one a policy is refusing.

The distinction matters because the three blockers call for different work, and
collapsing them sent operators to fix an environment field that could not have
helped (finding B-10).

Usage:
  python3 ops/secrets/probe_broker.py
  python3 ops/secrets/probe_broker.py --json
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from capability_client import broker_url, session_identity  # noqa: E402

_OPS_LIB = HERE.parent / "lib"
if str(_OPS_LIB) not in sys.path:
    sys.path.insert(0, str(_OPS_LIB))

from safe_https import exchange  # noqa: E402

TIMEOUT = 10

IDENTITY = "identity"
CONFIGURATION = "configuration"
REACHABILITY = "reachability"
NONE = "none"


def dns_state(host: str) -> str:
    try:
        socket.getaddrinfo(host, 443)
    except socket.gaierror:
        return "no_dns_record"
    except OSError:
        return "resolver_error"
    return "resolves"


def health_state(url: str, timeout: int = TIMEOUT) -> str:
    try:
        request = urllib.request.Request(f"{url}/healthz", method="GET")
        with exchange(
            request, timeout=timeout, allow_loopback_http=True, label="broker health URL"
        ) as response:
            return f"http_{response.status}"
    except urllib.error.HTTPError as exc:
        return f"http_{exc.code}"
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return f"unreachable_{type(exc).__name__}"


def run(env: dict[str, str] | None = None, *, timeout: int = TIMEOUT) -> dict:
    source = os.environ if env is None else env
    identity = session_identity(source)
    url = broker_url(source)

    result: dict = {
        "identity_method": identity.method,
        "identity_available": identity.available,
        "identity_reason": identity.reason,
        "broker_url": url or None,
    }

    # Ordered by dominance: an unverifiable identity cannot be rescued by a
    # reachable broker, so it is named first even when other things are wrong.
    if not identity.available:
        result["primary_blocker"] = IDENTITY
        result["remediation"] = identity.remediation
    elif not url:
        result["primary_blocker"] = CONFIGURATION
        result["remediation"] = "set L9_CAPABILITY_BROKER_URL in the account environment field"
    else:
        result["primary_blocker"] = NONE

    if url:
        host = urlparse(url).hostname or ""
        result["broker_host"] = host
        result["dns"] = dns_state(host)
        result["health"] = health_state(url, timeout)
        if result["dns"] == "no_dns_record":
            result["reachability_note"] = (
                "host has no DNS record — the broker is NOT DEPLOYED, "
                "as distinct from being blocked by egress policy"
            )
            if result["primary_blocker"] == NONE:
                result["primary_blocker"] = REACHABILITY
        elif not result["health"].startswith("http_2"):
            result["reachability_note"] = "host resolves but the broker did not answer healthily"
            if result["primary_blocker"] == NONE:
                result["primary_blocker"] = REACHABILITY

    result["ok"] = result["primary_blocker"] == NONE
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = run()
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["ok"] else 1

    print("=== Capability broker reachability ===")
    print(
        f"  identity:      {result['identity_method']} "
        f"({'available' if result['identity_available'] else result['identity_reason']})"
    )
    print(f"  broker url:    {result['broker_url'] or '<unset>'}")
    if "dns" in result:
        print(f"  broker dns:    {result['dns']}")
        print(f"  broker health: {result['health']}")
    if result.get("reachability_note"):
        print(f"  note:          {result['reachability_note']}")
    print(f"  PRIMARY BLOCKER: {result['primary_blocker']}")
    if result.get("remediation"):
        print(f"  remediation:     {result['remediation']}")
    if not result["ok"]:
        print("\n  See docs/DEGRADED_MODE_CONTRACT.md for what remains valid.")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

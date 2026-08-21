#!/usr/bin/env python3
"""Every registered capability must name a host that actually exists.

The capability registry binds each id to exactly one `upstream_host`, and the
broker will contact no other. That makes the field load-bearing — and it was
never checked. `context7.mcp` pointed at `api.context7.io`, a domain that does
not resolve, so the capability could not have succeeded even with a healthy
broker and a valid credential. Nothing probed it, so nothing said so (B-13).

Resolution is injectable, because a validator that needs DNS is a validator that
fails in an air-gapped CI runner for reasons unrelated to the registry. The
default resolver uses DNS; tests pass their own.

Usage:
  python3 ops/secrets/validate_capability_hosts.py              # syntax only
  python3 ops/secrets/validate_capability_hosts.py --resolve    # + DNS probe
"""

from __future__ import annotations

import argparse
import re
import socket
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

HERE = Path(__file__).resolve().parent
REGISTRY = HERE / "capabilities.yaml"

#: A hostname, not a URL and not a host:port. The broker composes the scheme and
#: path itself; anything else here is a registry authoring error.
_HOSTNAME = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))+$"
)

Resolver = Callable[[str], bool]


def dns_resolver(host: str) -> bool:
    try:
        socket.getaddrinfo(host, 443)
    except OSError:
        return False
    return True


def load_registry(path: Path | None = None) -> dict[str, Any]:
    return yaml.safe_load((path or REGISTRY).read_text(encoding="utf-8"))


def validate(
    registry: dict[str, Any],
    *,
    resolve: bool = False,
    resolver: Resolver | None = None,
) -> list[str]:
    """Return a list of violations. Empty means the registry is sound."""
    probe = resolver or dns_resolver
    violations: list[str] = []
    seen_ids: set[str] = set()

    for entry in registry.get("capabilities") or []:
        cap_id = entry.get("id", "<unnamed>")
        if cap_id in seen_ids:
            violations.append(f"{cap_id}: duplicate capability id")
        seen_ids.add(cap_id)

        host = entry.get("upstream_host")
        if not host:
            violations.append(f"{cap_id}: no upstream_host — the broker would have no bound target")
            continue
        if "://" in host or "/" in host:
            violations.append(f"{cap_id}: upstream_host {host!r} is a URL; want a bare hostname")
            continue
        if ":" in host:
            violations.append(
                f"{cap_id}: upstream_host {host!r} carries a port; want a bare hostname"
            )
            continue
        if not _HOSTNAME.match(host):
            violations.append(f"{cap_id}: upstream_host {host!r} is not a valid hostname")
            continue
        if resolve and not probe(host):
            violations.append(
                f"{cap_id}: upstream_host {host!r} does not resolve — "
                "this capability can never succeed"
            )
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--resolve", action="store_true", help="also probe DNS for each host")
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    args = parser.parse_args(argv)

    violations = validate(load_registry(args.registry), resolve=args.resolve)
    if violations:
        print(f"RESULT: FAIL — {len(violations)} capability host violation(s)")
        for violation in violations:
            print(f"  FAIL: {violation}")
        return 1
    mode = "syntax + resolution" if args.resolve else "syntax"
    print(f"RESULT: PASS — every capability upstream_host is valid ({mode})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

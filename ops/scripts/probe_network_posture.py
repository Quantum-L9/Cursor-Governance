#!/usr/bin/env python3
"""Assert the egress posture this deployment actually chose.

`web/network-policy.md` lists hosts under "Egress the agent must not need
(contract §16)" — `app.infisical.com` and `sonarcloud.io` among them — and calls
that a second, independent line of defence behind the capability architecture.
The audited environment reached both (`200` and `307`), because its Network
access field was set to Full. A stated control that is not in force is worse
than an absent one: it is counted on.

DECISION (see docs/NETWORK_POSTURE.md): tighten the field to least privilege.
Neither host is reachable by any legitimate operation on a model-controlled
surface — the broker reaches them, the agent never does — so blocking them costs
this surface nothing and makes the documented control real.

This probe reports by default and asserts under --assert, so it is useful before
the field is pasted (naming what is still open) and after (guarding it).

Usage:
  python3 ops/scripts/probe_network_posture.py
  python3 ops/scripts/probe_network_posture.py --assert
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

_OPS_LIB = Path(__file__).resolve().parent.parent / "lib"
if str(_OPS_LIB) not in sys.path:
    sys.path.insert(0, str(_OPS_LIB))

from safe_https import https_exchange  # noqa: E402

#: Reachability here is a policy violation, not a capability.
MUST_NOT_REACH = ("app.infisical.com", "sonarcloud.io")

#: Reachability here is required; a failure disables the named capability.
MUST_REACH = ("github.com", "api.github.com", "pypi.org")

TIMEOUT = 10


def reachable(host: str, timeout: int = TIMEOUT) -> bool:
    """True when an HTTPS connection completes, however the server answers.

    An HTTP error code still proves reachability, so it counts as reachable;
    only a transport failure counts as blocked.
    """
    try:
        request = urllib.request.Request(f"https://{host}/", method="GET")
        https_exchange(
            request,
            timeout=timeout,
            allowed_hosts=frozenset(MUST_NOT_REACH + MUST_REACH),
            label="posture probe URL",
        )
    except urllib.error.HTTPError:
        return True
    except (TimeoutError, urllib.error.URLError, OSError, ValueError):
        return False
    return True


def run(timeout: int = TIMEOUT) -> dict:
    open_violations = [h for h in MUST_NOT_REACH if reachable(h, timeout)]
    unreachable_required = [h for h in MUST_REACH if not reachable(h, timeout)]
    return {
        "posture": "least-privilege",
        "violations": open_violations,
        "missing_required": unreachable_required,
        "ok": not open_violations and not unreachable_required,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--assert", dest="assert_", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--timeout", type=int, default=TIMEOUT)
    args = parser.parse_args(argv)

    result = run(args.timeout)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("=== Egress posture (target: least privilege) ===")
        for host in result["violations"]:
            print(f"  OPEN: {host} is reachable but policy says the agent must not need it")
        for host in result["missing_required"]:
            print(f"  BLOCKED: {host} is required and unreachable")
        if result["ok"]:
            print("  OK: egress matches the documented least-privilege posture")
        elif result["violations"]:
            print("\n  The Network access field is wider than the policy. Repair by pasting")
            print("  the Custom host list from web/network-policy.md (Option B).")
    if args.assert_ and not result["ok"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Detect drift between the live runtime and the account fields that shaped it.

Three things configure a Claude Code cloud environment, and an agent can write
none of them: the **Setup script**, the **Environment variables** and the
**Network access** fields on claude.ai/code. They are copy-pasted, so they drift
from `main` silently and invisibly — there is no way to read a field back from
inside the sandbox.

What IS readable is what those fields produced. This tool compares that against
what the repository expects, and prints exact paste-ready replacement text.

The audit found four deviations, all of them costly and none of them visible:

    L9_CAPABILITY_BROKER_URL               missing  -> whole capability plane unconfigured
    CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS   missing  -> native 20-subagent ceiling
    L9_AUTONOMY_MAX_PARALLEL               4        -> expected 480
    L9_AUTONOMY_MAX_MUTATION_LANES         2        -> expected 128 (120x throttle)

The last two are Cursor's constrained defaults, which the example file says
explicitly belong to Cursor and not here.

Usage:
  python3 environment/agents/adapters/claude-code/verify_account_env.py
  python3 environment/agents/adapters/claude-code/verify_account_env.py --json
  python3 environment/agents/adapters/claude-code/verify_account_env.py --emit-fields
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
ENV_EXAMPLE = HERE / "web" / "environment.env.example"
STUB = HERE / "web" / "setup.bootstrap.sh"
NETWORK_POLICY = HERE / "web" / "network-policy.md"
ACCOUNT_FIELDS = HERE.parents[3] / "docs" / "ACCOUNT_FIELDS.md"
SESSION_ENV = Path(os.environ.get("HOME", "~")) / ".l9" / "cloud-session.env"

#: Keys the example file documents as deliberately ABSENT. Their presence is the
#: drift, not their absence — so they are never reported as missing.
DELIBERATELY_ABSENT = frozenset(
    {
        "GH_TOKEN",
        "L9_GOVERNANCE_DIR",
        "GRAPHITI_MCP_TOKEN",
        "GRAPHITI_GROUP_ID",
        "SONAR_TOKEN",
        "SONAR_PROJECT_KEY",
        "SONAR_ORG_KEY",
        "SEMGREP_APP_TOKEN",
        "INFISICAL_CLIENT_SECRET",
        "INFISICAL_TOKEN",
    }
)

#: The platform's marker for a credential it proxies rather than hands over.
#: `setup.bootstrap.sh` leaves these in place deliberately — unsetting the
#: sentinel would break the very proxying it announces — so a prohibited-key
#: check must not read one as a pasted credential.
PLATFORM_PROXY_SENTINEL = "proxy-injected"

#: Variables the RUNTIME owns after the account field sets them. The harness
#: decrements CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH per nesting level — observed
#: going 3 -> 1 within one session as subagents nested — so comparing it to a
#: static expectation reports permanent drift that no paste can fix. Reported
#: for information, never as a deviation.
RUNTIME_MANAGED = frozenset({"CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"})

#: Names whose VALUE must never be printed, whatever the example file says.
#: The expected set is derived from environment.env.example, which by contract
#: assigns no credential — but that contract is enforced elsewhere, and a tool
#: that echoes live environment values should not depend on another file staying
#: correct to remain safe (INV-6, defence in depth).
#: `_KEY$` alone missed real inventory names: GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY_ID
#: ends in `_KEY_ID`, and a bare `KEY` matches neither anchor. A redaction filter
#: that is defence in depth (INV-6) must not depend on the anchor being the last
#: character of the name.
_SECRETISH = re.compile(
    r"(TOKEN|SECRET|PASSWORD|PASSWD|PASSPHRASE|CREDENTIAL|PRIVATE"
    r"|_KEY(_ID)?$|^KEY$|APIKEY|API_KEY|BEARER|SESSION_ID)",
    re.IGNORECASE,
)

REDACTED = "<redacted>"


def safe_value(key: str, value: str) -> str:
    """Return a value safe to print for this key."""
    return REDACTED if _SECRETISH.search(key) else value


_ASSIGNMENT = re.compile(r"^([A-Z][A-Z0-9_]*)=(.*)$")


def parse_env_example(path: Path | None = None) -> dict[str, str]:
    """Read the .env-format example. Comments define intent; assignments define value."""
    expected: dict[str, str] = {}
    for raw in (path or ENV_EXAMPLE).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = _ASSIGNMENT.match(line)
        if match:
            expected[match.group(1)] = match.group(2).strip()
    return {k: v for k, v in expected.items() if k not in DELIBERATELY_ABSENT}


def stub_revision_expected(path: Path | None = None) -> str:
    body = (path or STUB).read_text(encoding="utf-8")
    match = re.search(r'^L9_STUB_REVISION="([^"]+)"', body, re.MULTILINE)
    return match.group(1) if match else ""


def stub_revision_actual(env: dict[str, str] | None = None, session_env: Path | None = None) -> str:
    source = os.environ if env is None else env
    if source.get("L9_STUB_REVISION"):
        return source["L9_STUB_REVISION"]
    path = session_env or SESSION_ENV
    if not path.is_file():
        return ""
    match = re.search(
        r"^export L9_STUB_REVISION=[\"']?([^\"'\n]+)",
        path.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    return match.group(1) if match else ""


def compare(expected: dict[str, str], env: dict[str, str] | None = None) -> list[dict[str, str]]:
    """One row per deviation. Empty means the account field matches HEAD."""
    live = os.environ if env is None else env
    deviations: list[dict[str, str]] = []
    for key, want in sorted(expected.items()):
        if key in RUNTIME_MANAGED:
            continue
        if key not in live:
            deviations.append(
                {"key": key, "expected": want, "actual": "<missing>", "kind": "missing"}
            )
        elif live[key] != want:
            deviations.append(
                {"key": key, "expected": want, "actual": live[key], "kind": "mismatch"}
            )
    return deviations


def prohibited_present(env: dict[str, str] | None = None) -> list[dict[str, str]]:
    """One row per prohibited key that is actually SET in the live environment.

    :data:`DELIBERATELY_ABSENT` states the contract in two halves — "their
    presence is the drift, not their absence". Only the second half was
    enforced: the keys were filtered out of the expected set so they could
    never be reported missing, and nothing ever looked for them being present.

    That left the more serious half unimplemented. Pasting
    ``INFISICAL_CLIENT_SECRET`` or ``GRAPHITI_MCP_TOKEN`` into the account
    field is a master key sitting in a model-controlled environment (contract
    S1/S2/S3) — and this tool would have answered "all N expected variables
    match", because a value nobody compares is a value nobody sees.

    Values are never returned. The key name and its classification are the
    whole finding; printing the value would leak the credential this check
    exists to find.
    """
    live = os.environ if env is None else env
    rows: list[dict[str, str]] = []
    for key in sorted(DELIBERATELY_ABSENT):
        if key not in live:
            continue
        if live[key] == PLATFORM_PROXY_SENTINEL:
            rows.append(
                {
                    "key": key,
                    "kind": "proxy_sentinel",
                    "actual": PLATFORM_PROXY_SENTINEL,
                    "detail": "platform proxy marker, not a credential — left in place",
                }
            )
            continue
        rows.append(
            {
                "key": key,
                "kind": "prohibited",
                "actual": REDACTED,
                "detail": "PROHIBITED on a model-controlled surface; remove it from the field",
            }
        )
    return rows


def parse_network_hosts(path: Path | None = None) -> list[str]:
    """Return the Option B custom host list — the block a human actually pastes.

    Section 3 used to say only "see network-policy.md". Two of the three account
    fields were paste-ready and the third was a pointer, so the one field that
    closes the egress gap was the one nobody could paste without a second hop.
    """
    text = (path or NETWORK_POLICY).read_text(encoding="utf-8")
    match = re.search(r"^## Option B.*?\n```\n(.*?)\n```", text, re.DOTALL | re.MULTILINE)
    if not match:
        return []
    return [
        line.strip()
        for line in match.group(1).splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def account_fields_markdown(expected: dict[str, str], revision: str) -> str:
    body = "\n".join(f"{key}={value}" for key, value in sorted(expected.items()))
    checksum = hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]
    stub_body = STUB.read_text(encoding="utf-8")
    stub_checksum = hashlib.sha256(stub_body.encode("utf-8")).hexdigest()[:16]
    hosts = parse_network_hosts()
    host_body = "\n".join(hosts)
    host_checksum = hashlib.sha256(host_body.encode("utf-8")).hexdigest()[:16]
    return f"""# Account fields — paste-ready

Generated by `verify_account_env.py --emit-fields`. An agent cannot write these
three fields; a human pastes them at claude.ai/code -> environment.

Changes apply to NEW sessions only. Anthropic caches the environment after the
first successful build, so a stale paste survives until the environment is
rebuilt — which is the failure this file exists to make detectable.

## 1. Environment variables

Checksum `{checksum}` — `verify_account_env.py` confirms a paste by comparing
the live runtime against this set.

```dotenv
{body}
```

## 2. Setup script

Paste `environment/agents/adapters/claude-code/web/setup.bootstrap.sh` verbatim.

- Revision: `{revision}`
- Checksum: `{stub_checksum}`

The stub records its own revision into `~/.l9/cloud-session.env`, so a later
session can tell whether the pasted copy is current without reading the field.

## 3. Network access

Select **Custom**, keep the default package-manager list, and add the {len(hosts)}
hosts below. Checksum `{host_checksum}`.

Every entry is owned by a capability the adapter actually invokes; the
host -> capability table in `web/network-policy.md` records which. Dropping a
host disables exactly the capability named beside it.

```
{host_body}
```

`app.infisical.com` and `sonarcloud.io` are deliberately absent: the agent holds
no credential for either, and blocking egress makes that structural rather than
conventional. Their reachability is a finding, not a feature.

Full rationale, including what the broker reaches on the agent's behalf, is in
`environment/agents/adapters/claude-code/web/network-policy.md`.
"""


def run(env: dict[str, str] | None = None) -> dict[str, Any]:
    expected = parse_env_example()
    deviations = compare(expected, env)
    want_rev = stub_revision_expected()
    have_rev = stub_revision_actual(env)
    present = prohibited_present(env)
    #: A proxy sentinel is reported for transparency but is not a violation.
    violations = [row for row in present if row["kind"] == "prohibited"]
    return {
        "expected_keys": len(expected),
        "deviations": deviations,
        "prohibited_present": present,
        "prohibited_count": len(violations),
        "stub_revision_expected": want_rev,
        "stub_revision_actual": have_rev,
        "stub_drift": bool(want_rev) and have_rev != want_rev,
        "ok": (not deviations and not violations and not (bool(want_rev) and have_rev != want_rev)),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--emit-fields",
        action="store_true",
        help="write docs/ACCOUNT_FIELDS.md with paste-ready text and checksums",
    )
    parser.add_argument(
        "--check-fields",
        action="store_true",
        help="verify docs/ACCOUNT_FIELDS.md matches its three sources; exit 1 on drift",
    )
    args = parser.parse_args(argv)

    if args.check_fields:
        want = account_fields_markdown(parse_env_example(), stub_revision_expected())
        if not ACCOUNT_FIELDS.is_file():
            print(f"MISSING: {ACCOUNT_FIELDS} — run --emit-fields")
            return 1
        if ACCOUNT_FIELDS.read_text(encoding="utf-8") != want:
            print(f"STALE: {ACCOUNT_FIELDS} no longer matches its sources")
            print("       sources: web/environment.env.example, web/setup.bootstrap.sh,")
            print("                web/network-policy.md")
            print("       repair:  verify_account_env.py --emit-fields")
            return 1
        print(f"OK: {ACCOUNT_FIELDS.relative_to(REPO)} matches its three sources")
        return 0

    if args.emit_fields:
        target = REPO / "docs" / "ACCOUNT_FIELDS.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            account_fields_markdown(parse_env_example(), stub_revision_expected()),
            encoding="utf-8",
        )
        print(f"wrote {target}")
        return 0

    result = run()
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["ok"] else 1

    print("=== Account environment drift ===")
    for key in sorted(RUNTIME_MANAGED):
        if key in os.environ:
            print(
                f"  INFO: {key}={safe_value(key, os.environ[key])} (runtime-managed; not compared)"
            )
    for row in result["prohibited_present"]:
        if row["kind"] == "prohibited":
            print(f"  PROHIBITED: {row['key']} is SET — {row['detail']}")
        else:
            print(f"  INFO: {row['key']}={row['actual']} ({row['detail']})")
    if result["prohibited_count"]:
        print(
            f"         {result['prohibited_count']} prohibited variable(s) in the account"
            " field. Remove them; do not rely on a script to unset them at runtime."
        )

    if result["stub_drift"]:
        print(
            f"  DRIFT: Setup script is revision "
            f"{result['stub_revision_actual'] or '<unrecorded>'}, "
            f"HEAD is {result['stub_revision_expected']}"
        )
        print("         re-paste web/setup.bootstrap.sh into the Setup script field")
    elif result["stub_revision_actual"]:
        print(f"  OK: Setup script revision {result['stub_revision_actual']}")

    if not result["deviations"]:
        print(f"  OK: all {result['expected_keys']} expected variables match")
        return 0 if result["ok"] else 1

    print(f"  DRIFT: {len(result['deviations'])} of {result['expected_keys']} variables")
    for row in result["deviations"]:
        key = row["key"]
        print(
            f"    {key}: expected {safe_value(key, row['expected'])!r}, "
            f"got {safe_value(key, row['actual'])!r}"
        )
    print(
        "\n  Repair: python3 environment/agents/adapters/claude-code/verify_account_env.py"
        " --emit-fields"
    )
    print("          then paste docs/ACCOUNT_FIELDS.md section 1 into Environment variables")
    return 1


if __name__ == "__main__":
    sys.exit(main())

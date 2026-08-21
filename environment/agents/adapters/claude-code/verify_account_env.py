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
_SECRETISH = re.compile(
    r"(TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|_KEY$|APIKEY|API_KEY|BEARER|SESSION_ID)",
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


def account_fields_markdown(expected: dict[str, str], revision: str) -> str:
    body = "\n".join(f"{key}={value}" for key, value in sorted(expected.items()))
    checksum = hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]
    stub_body = STUB.read_text(encoding="utf-8")
    stub_checksum = hashlib.sha256(stub_body.encode("utf-8")).hexdigest()[:16]
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

See `environment/agents/adapters/claude-code/web/network-policy.md`. That file
records which posture this deployment chose and why.
"""


def run(env: dict[str, str] | None = None) -> dict[str, Any]:
    expected = parse_env_example()
    deviations = compare(expected, env)
    want_rev = stub_revision_expected()
    have_rev = stub_revision_actual(env)
    return {
        "expected_keys": len(expected),
        "deviations": deviations,
        "stub_revision_expected": want_rev,
        "stub_revision_actual": have_rev,
        "stub_drift": bool(want_rev) and have_rev != want_rev,
        "ok": not deviations and not (bool(want_rev) and have_rev != want_rev),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--emit-fields",
        action="store_true",
        help="write docs/ACCOUNT_FIELDS.md with paste-ready text and checksums",
    )
    args = parser.parse_args(argv)

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

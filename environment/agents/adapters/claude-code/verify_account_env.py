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

    CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS   missing  -> native 20-subagent ceiling
    L9_AUTONOMY_MAX_PARALLEL               4        -> expected 480
    L9_AUTONOMY_MAX_MUTATION_LANES         2        -> expected 128 (120x throttle)

`L9_CAPABILITY_BROKER_URL` is retired (never shipped) and is not an account field.

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
        # Per-invocation opt-out, spelled at the call site. See PINNED_OPT_OUTS.
        "PR_REMEDIATE",
    }
)

#: Keys whose drift widens authority rather than just changing a display default.
AUTHORITY_WIDENING = frozenset(
    {
        "L9_AUTONOMY_ENABLED",
        "L9_AUTONOMY_AUTHORITY",
        "L9_AUTONOMY_MATURITY",
        "L9_L4_LOCAL_AUTONOMY",
        "L9_AUTONOMY_MAX_PARALLEL",
        "L9_AUTONOMY_MAX_MUTATION_LANES",
        "L9_GOVERNANCE_SURFACE",
        "L9_PUBLISH_PATH_OVERRIDE",
        "L9_MERGE_AUTHORIZED",
        "L9_WORKTREE_ISOLATION",
        "L9_AUTONOMY_STATE_DIR",
    }
)

ENV_EXAMPLE_REL = "environment/agents/adapters/claude-code/web/environment.env.example"

#: Variables the RUNTIME owns after the account field sets them. The harness
#: decrements CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH per nesting level — observed
#: going 3 -> 1 within one session as subagents nested — so comparing it to a
#: static expectation reports permanent drift that no paste can fix. Reported
#: for information, never as a deviation.
RUNTIME_MANAGED = frozenset({"CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"})

#: Credentials the example file prohibits outright. Nothing on this surface
#: legitimately sets them: the capability broker holds them on its own side, and
#: setup.bootstrap.sh strips any that arrive. So finding one in the live runtime
#: means it was pasted into the Environment variables field, or survived a stub
#: that never ran — a persistent, reusable secret in a model-readable
#: environment, which is the one thing the contract exists to prevent.
#:
#: DELIBERATELY_ABSENT is deliberately NOT reused here. It also holds names that
#: are legitimately present at runtime — L9_GOVERNANCE_DIR is exported by the
#: stub itself, GH_TOKEN is issued by the platform and required by `gh`, and
#: GRAPHITI_GROUP_ID is a valid per-shell override — so reporting that set would
#: be noise, and noise is how a real finding gets scrolled past.
PROHIBITED_PRESENT = frozenset(
    {
        "GRAPHITI_MCP_TOKEN",
        "INFISICAL_CLIENT_SECRET",
        "INFISICAL_TOKEN",
        "INFISICAL_PASSWORD",
        "SONAR_TOKEN",
        "SONARCLOUD_TOKEN",
        "SEMGREP_APP_TOKEN",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_ACCESS_KEY_ID",
        "AWS_SESSION_TOKEN",
    }
)

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


_REVISION = re.compile(r"^(\d{4})-(\d{2})-(\d{2})\.(\d+)$")


def revision_key(revision: str) -> tuple[int, int, int, int] | None:
    """Sortable key for a `YYYY-MM-DD.N` stub revision, or None if unparseable."""
    match = _REVISION.match(revision.strip())
    if not match:
        return None
    year, month, day, seq = match.groups()
    return (int(year), int(month), int(day), int(seq))


def revision_direction(actual: str, expected: str) -> str:
    """Which side is newer: `behind`, `ahead`, `same`, or `unknown`.

    Direction decides the remediation, and the two are opposites. `behind` means
    the pasted field is stale and re-pasting HEAD fixes it. `ahead` means the
    field carries a stub revision that is in NO commit — re-pasting HEAD would
    DOWNGRADE production and destroy the only copy of that code, because a field
    cannot be read back from inside the sandbox. Treating both as "drift" and
    printing one instruction is how the destructive case gets automated.
    """
    want, have = revision_key(expected), revision_key(actual)
    if want is None or have is None:
        return "unknown"
    if have == want:
        return "same"
    return "ahead" if have > want else "behind"


#: The platform's marker for a credential it proxies rather than hands over.
#: `AWS_ACCESS_KEY_ID=proxy-injected` is an announcement, not a key, and
#: setup.bootstrap.sh already skips it for the same reason. Reporting it as a
#: leak would cry wolf on every hosted session and teach the reader to ignore
#: the one line that matters.
PROXY_SENTINEL = "proxy-injected"


#: Per-invocation opt-outs that must never be pinned in the account field.
#:
#: These are not credentials and not authority — they are flags a COMMAND passes
#: for one run. Set once in the ambient environment they apply to every
#: invocation forever, and the documented default becomes unreachable: nothing a
#: caller does can restore it, because the caller's own default is what the
#: ambient value overrides.
#:
#: PR_REMEDIATE is the observed case. rules/48 states remediates defaults to 1
#: after the PR opens and that `PR_REMEDIATE=0` is opt-out ONLY, but it was
#: pinned to 0 account-wide, so the poll-to-green worker could never run on this
#: surface and no `make pr` could re-enable it. Every documented invocation
#: spells the opt-out at the call site (`PR_REMEDIATE=0 make pr`), which is
#: exactly why the field must not spell it too.
PINNED_OPT_OUTS = frozenset({"PR_REMEDIATE"})


def pinned_opt_outs_present(env: dict[str, str] | None = None) -> list[str]:
    """Per-invocation opt-outs found pinned in the ambient environment."""
    live = os.environ if env is None else env
    return sorted(key for key in PINNED_OPT_OUTS if key in live)


def prohibited_present(env: dict[str, str] | None = None) -> list[str]:
    """Prohibited credential names carrying real material in the live runtime."""
    live = os.environ if env is None else env
    return sorted(
        key
        for key in PROHIBITED_PRESENT
        if (live.get(key) or "").strip() and (live.get(key) or "").strip() != PROXY_SENTINEL
    )


def compare(expected: dict[str, str], env: dict[str, str] | None = None) -> list[dict[str, str]]:
    """One row per deviation. Empty means the account field matches HEAD."""
    live = os.environ if env is None else env
    deviations: list[dict[str, str]] = []
    for key, want in sorted(expected.items()):
        if key in RUNTIME_MANAGED:
            continue
        klass = "authority_widening" if key in AUTHORITY_WIDENING else "cosmetic"
        row = {
            "key": key,
            "expected": want,
            "source": ENV_EXAMPLE_REL,
            "class": klass,
        }
        if key not in live:
            deviations.append({**row, "actual": "<missing>", "kind": "missing"})
        elif live[key] != want:
            deviations.append({**row, "actual": live[key], "kind": "mismatch"})
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


def variables_field_markdown(expected: dict[str, str]) -> str:
    """Standalone paste-ready document for the Environment variables field."""
    body = "\n".join(f"{key}={value}" for key, value in sorted(expected.items()))
    checksum = hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]
    return f"""# Environment variables — paste-ready

**Field:** claude.ai/code → environment → **Environment variables**
**Format:** literal `.env` text. Nothing here is shell-expanded: `FOO=$HOME/x`
is stored as the characters `$HOME/x`.
**Applies to:** NEW sessions only. Anthropic caches the environment after the
first successful build, so a stale paste survives until a rebuild.
**Checksum:** `{checksum}` ({len(expected)} variables)

Generated from `environment/agents/adapters/claude-code/web/environment.env.example`
by `verify_account_env.py --emit-fields`. Do not hand-edit this file; edit the
example and regenerate, or the two disagree and the drift check trusts the example.

## Carries no credentials, by contract

No PAT, no Graphiti bearer, no Sonar or Semgrep token, no Infisical client
secret, no AWS key. Everything in this field is readable by anything the model
can run. A capability reporting DEGRADED is a broker-delivery problem; pasting a
secret here to turn it green is a permanent compromise (contract S1/S2/S3).

`verify_account_env.py` now reports a prohibited credential it finds in the live
runtime, so a paste of one does not pass silently.

## Paste this

```dotenv
{body}
```

## Verify the paste took

```bash
python3 environment/agents/adapters/claude-code/verify_account_env.py
```

`OK: all {len(expected)} expected variables match` means the field matches HEAD.
Any `DRIFT:` line names the variable, what is set, and what was expected.
"""


def setup_script_markdown(revision: str) -> str:
    """Standalone paste-ready document for the Setup script field."""
    stub_body = STUB.read_text(encoding="utf-8")
    checksum = hashlib.sha256(stub_body.encode("utf-8")).hexdigest()[:16]
    return f"""# Setup script — paste-ready

**Field:** claude.ai/code → environment → **Setup script**
**Revision:** `{revision}` · **Checksum:** `{checksum}`
**Applies to:** NEW sessions only.

Source of truth: `environment/agents/adapters/claude-code/web/setup.bootstrap.sh`.
Paste the stub, never `web/setup.sh`. The field is a copy, not a live link, so a
full script pasted into it drifts from `main` on every edit; the stub is stable
and hands off to `web/setup.sh` from the governance clone, which means setup.sh
changes reach every new session with no re-paste.

## Before you paste — copy the current field out first

A field cannot be read back from inside the sandbox, so whatever is in it now is
the only copy. If `verify_account_env.py` reports the field is **ahead** of HEAD,
it is running bootstrap code that exists in no commit: copy it out, diff it
against the stub below, and commit anything it added. Pasting over an ahead field
destroys that code silently.

```bash
python3 environment/agents/adapters/claude-code/verify_account_env.py   # names the direction
```

## Paste this

Copy **only** the script itself: the first line of the block below is
`#!/usr/bin/env bash`, immediately followed by an `L9-PASTE-BEGIN` marker, and
the last is an `L9-PASTE-END` marker just after `exit 0`. Do **not** include
the triple-backtick fence lines that open and close the block, this heading, or
the prose that follows the block.

Selecting a rendered page accurately is fiddly, so prefer copying the raw file —
it is byte-identical to the block below and carries no fence to catch:

```bash
cat environment/agents/adapters/claude-code/web/setup.bootstrap.sh
```

> **Why the fence lines matter.** A markdown fence is three backticks. Bash reads
> that as an empty command substitution plus one leftover backtick, which opens a
> substitution that swallows the entire stub. Measured on 2026-08-22, pasting the
> fence executed the stub's English comments as shell commands, ran `git clone`
> with an empty target directory, and ended in `exit 127` with the environment
> half-built and no line naming the cause. The stub is now backtick-free and
> detects the contaminated paste itself, refusing with a `FATAL` line that names
> the fence — but the environment still will not build until you re-paste
> without the fence lines.

```bash
{stub_body.rstrip()}
```

## Verify the paste took

Start a NEW session, then:

```bash
grep L9_STUB_REVISION ~/.l9/cloud-session.env      # expect {revision}
make claude-env                                    # structural + RUNTIME verdicts
```

If `~/.l9/cloud-session.env` does not exist at all, the stub did not run to
completion. Read the environment's setup log and look for a line beginning
`L9 bootstrap FATAL:` — the paste-integrity guard names the fence contamination
explicitly rather than leaving you to read a wall of "command not found".

The stub records its own revision into `~/.l9/cloud-session.env` on every run, so
a later session can answer "is the pasted stub current?" without reading the field.
"""


def run(
    env: dict[str, str] | None = None,
    session_env: Path | None = None,
) -> dict[str, Any]:
    """Audit an environment. `session_env` overrides the session-env fallback.

    `stub_revision_actual` falls back to reading the machine's session env when
    the supplied environment carries no revision. Without a way to point that
    fallback somewhere explicit, a caller auditing a synthetic environment
    silently reads this machine's real revision instead.
    """
    expected = parse_env_example()
    deviations = compare(expected, env)
    want_rev = stub_revision_expected()
    have_rev = stub_revision_actual(env, session_env)
    drift = bool(want_rev) and have_rev != want_rev
    leaked = prohibited_present(env)
    pinned = pinned_opt_outs_present(env)
    return {
        "expected_keys": len(expected),
        "deviations": deviations,
        "stub_revision_expected": want_rev,
        "stub_revision_actual": have_rev,
        "stub_drift": drift,
        "stub_drift_direction": revision_direction(have_rev, want_rev) if drift else "same",
        "prohibited_present": leaked,
        "pinned_opt_outs": pinned,
        "ok": not deviations and not drift and not leaked and not pinned,
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
        expected = parse_env_example()
        revision = stub_revision_expected()
        index = REPO / "docs" / "ACCOUNT_FIELDS.md"
        index.parent.mkdir(parents=True, exist_ok=True)
        index.write_text(account_fields_markdown(expected, revision), encoding="utf-8")
        print(f"wrote {index}")
        # One field per file as well as the combined index: these get handed to
        # whoever pastes them, and that person needs the field they are pasting,
        # not a document about three fields.
        pane = REPO / "docs" / "account-fields"
        pane.mkdir(parents=True, exist_ok=True)
        for name, text in (
            ("ENVIRONMENT_VARIABLES.md", variables_field_markdown(expected)),
            ("SETUP_SCRIPT.md", setup_script_markdown(revision)),
        ):
            (pane / name).write_text(text, encoding="utf-8")
            print(f"wrote {pane / name}")
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
    for key in result["pinned_opt_outs"]:
        print(f"  PINNED: {key} is set in this environment")
        print("          It is a per-invocation opt-out, not an account setting. Pinned")
        print("          here it applies to every run and the documented default becomes")
        print("          unreachable. Delete it from the Environment variables field and")
        print("          pass it at the call site instead.")
    for key in result["prohibited_present"]:
        print(f"  PROHIBITED: {key} is set in this environment (value not shown)")
        print("              delete it from the Environment variables field; a pasted")
        print("              credential is never a workaround (contract S1/S2/S3)")
    if result["stub_drift"]:
        actual = result["stub_revision_actual"] or "<unrecorded>"
        print(
            f"  DRIFT: Setup script is revision {actual}, "
            f"HEAD is {result['stub_revision_expected']}"
        )
        if result["stub_drift_direction"] == "ahead":
            print("         The FIELD is ahead of HEAD: it carries a stub revision that is")
            print("         in no commit. Do NOT re-paste — that downgrades production and")
            print("         destroys the only copy. Copy the field out, diff it against")
            print("         web/setup.bootstrap.sh, and commit what it added.")
        else:
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
            f"got {safe_value(key, row['actual'])!r} "
            f"(source {row.get('source', ENV_EXAMPLE_REL)}; class {row.get('class', 'cosmetic')})"
        )
    print(
        "\n  Repair: python3 environment/agents/adapters/claude-code/verify_account_env.py"
        " --emit-fields"
    )
    print("          then paste docs/ACCOUNT_FIELDS.md section 1 into Environment variables")
    return 1


if __name__ == "__main__":
    sys.exit(main())

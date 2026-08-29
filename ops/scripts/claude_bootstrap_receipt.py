#!/usr/bin/env python3
"""Read the Claude adapter bootstrap receipt and classify it at read time.

Companion to governance_refresh_receipt.py, and it borrows that module's
timestamp and TTL handling rather than re-deriving it — one expiry rule for
every L9 receipt (INV-2).

The distinction this module exists to preserve:

    never_ran   no receipt on disk. The installer did not reach its own
                bookkeeping, so nothing about the environment is established.
                This is what the audited runtime actually looked like (B-04).
    failed      the installer ran and recorded the stage it died at.
    blocked     a required component could not be wired.
    degraded    an optional component is unavailable.
    ready       the required contract is satisfied.
    unknown     a receipt exists but no longer describes an observed state,
                either because it outlived its TTL or because the governance
                revision it was produced against is no longer checked out.

`never_ran` and `ready` are the two that get confused when a reader treats a
missing file as benign, which is why they are separated here rather than in each
caller.

Usage:
  python3 ops/scripts/claude_bootstrap_receipt.py --read
  python3 ops/scripts/claude_bootstrap_receipt.py --read --json
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from governance_refresh_receipt import _parse_timestamp  # noqa: PLC2701

SCHEMA = "l9.claude-bootstrap.v1"

NEVER_RAN = "never_ran"
UNKNOWN = "unknown"
FAILED = "failed"
BLOCKED = "blocked"
DEGRADED = "degraded"
READY = "ready"

DEFAULT_TTL_SECONDS = 86400

#: Component keys the receipt carries, in the order a reader should show them.
COMPONENTS = (
    "shared_bootstrap",
    "settings",
    "skills",
    "rules",
    "capabilities",
    "memory",
    "mcp",
    "plugins",
)


def _git_dir(base: Path) -> Path | None:
    """Resolve the git directory for a clone or a worktree checkout.

    A worktree stores `.git` as a `gitdir:` pointer file. Reading
    `base/.git/HEAD` then raises OSError and would hide a live revision.
    """
    git = base / ".git"
    try:
        if git.is_file():
            first = git.read_text(encoding="utf-8").splitlines()[0].strip()
            prefix, _, rest = first.partition(":")
            if prefix.lower() != "gitdir" or not rest.strip():
                return None
            pointer = Path(rest.strip())
            if not pointer.is_absolute():
                pointer = (base / pointer).resolve()
            return pointer if pointer.is_dir() else None
        if git.is_dir():
            return git
    except OSError:
        return None
    return None


def live_governance_revision(root: Path | None = None) -> str:
    """The governance revision this session is actually running.

    Returns "" when it cannot be determined, and an undeterminable revision
    never invalidates a receipt — a missing probe must not manufacture UNKNOWN
    out of a receipt that may be perfectly current.
    """
    base = root or Path(os.environ.get("L9_GOV_ROOT") or (Path.home() / ".cursor-governance"))
    git_dir = _git_dir(base)
    if git_dir is None:
        return ""
    head = git_dir / "HEAD"
    try:
        raw = head.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    if raw.startswith("ref:"):
        ref = raw.split(" ", 1)[1].strip()
        try:
            return (git_dir / ref).read_text(encoding="utf-8").strip()
        except OSError:
            packed = git_dir / "packed-refs"
            try:
                for line in packed.read_text(encoding="utf-8").splitlines():
                    if line.endswith(f" {ref}"):
                        return line.split(" ", 1)[0].strip()
            except OSError:
                return ""
            return ""
    return raw


def receipt_path(env: dict[str, str] | None = None) -> Path:
    source = os.environ if env is None else env
    override = (source.get("L9_CLAUDE_BOOTSTRAP_RECEIPT") or "").strip()
    if override:
        return Path(override)
    return Path(source.get("HOME", str(Path.home()))) / ".l9" / "claude" / "bootstrap-state.json"


def evaluate(
    receipt: dict[str, Any] | None,
    *,
    now: datetime | None = None,
    governance_revision: str | None = None,
) -> dict[str, Any]:
    moment = now or datetime.now(UTC)

    if receipt is None:
        return {
            "state": NEVER_RAN,
            "reason": "no bootstrap receipt on disk — the adapter installer never completed",
            "remediation": "bash environment/agents/adapters/claude-code/install.sh",
            "components": {},
        }

    components = {key: receipt.get(key, "UNKNOWN") for key in COMPONENTS}
    carried = {
        "components": components,
        "stage": receipt.get("stage"),
        "workspace": receipt.get("workspace"),
        "governance_revision": receipt.get("governance_revision"),
        "generated_at": receipt.get("generated_at"),
        "remediation": receipt.get("remediation", ""),
    }

    written = _parse_timestamp(str(receipt.get("generated_at", "")))
    if written is None:
        return {"state": UNKNOWN, "reason": "receipt carries no parseable UTC timestamp", **carried}

    age = int((moment - written).total_seconds())
    ttl = receipt.get("ttl_seconds")
    ttl = DEFAULT_TTL_SECONDS if not isinstance(ttl, int) or ttl <= 0 else ttl
    carried["age_seconds"] = age
    if age > ttl:
        return {"state": UNKNOWN, "reason": f"receipt expired ({age}s old, ttl {ttl}s)", **carried}

    # A receipt describes artifacts PROJECTED FROM a governance revision:
    # skills, rules, settings, plugins. When that revision moves, the receipt
    # describes a projection that no longer exists — regardless of its age.
    # Time alone was the only expiry rule here, and its TTL is 24x the
    # governance refresh TTL, so a DEGRADED verdict produced against a
    # superseded revision was reported as current for a whole day, its
    # remediation printed and never run. Revision is the stronger binding, so
    # it is checked even while the clock still says fresh.
    recorded_revision = str(receipt.get("governance_revision") or "").strip()
    live = (governance_revision or "").strip()
    if live and recorded_revision and recorded_revision != live:
        return {
            "state": UNKNOWN,
            "reason": (
                "governance revision superseded "
                f"(receipt {recorded_revision[:8]}, live {live[:8]}) — "
                "the projected artifacts this receipt describes were rebuilt"
            ),
            **carried,
        }

    recorded = str(receipt.get("state") or receipt.get("overall") or "").upper()
    if recorded == "FAILED":
        return {
            "state": FAILED,
            "reason": f"installer failed at stage '{receipt.get('stage', 'unknown')}'",
            **carried,
        }
    if recorded == "BLOCKED" or "BLOCKED" in components.values():
        return {"state": BLOCKED, "reason": _first_non_ready(components, "BLOCKED"), **carried}
    if recorded == "DEGRADED" or "DEGRADED" in components.values():
        return {"state": DEGRADED, "reason": _first_non_ready(components, "DEGRADED"), **carried}
    if recorded == "READY":
        return {"state": READY, "reason": f"all components READY ({age}s ago)", **carried}
    return {"state": UNKNOWN, "reason": f"unrecognised recorded state {recorded!r}", **carried}


def _first_non_ready(components: dict[str, Any], level: str) -> str:
    named = [key for key, value in components.items() if value == level]
    return f"{level.lower()}: {', '.join(named)}" if named else level.lower()


def read(
    path: Path | None = None,
    *,
    now: datetime | None = None,
    governance_revision: str | None = None,
) -> dict[str, Any]:
    target = path or receipt_path()
    revision = live_governance_revision() if governance_revision is None else governance_revision
    if not target.is_file():
        return evaluate(None, now=now, governance_revision=revision)
    try:
        parsed = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {
            "state": UNKNOWN,
            "reason": f"receipt at {target} is unreadable or malformed",
            "components": {},
        }
    if not isinstance(parsed, dict):
        return {"state": UNKNOWN, "reason": "receipt is not a JSON object", "components": {}}
    return evaluate(parsed, now=now, governance_revision=revision)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    # Read is the only action these CLIs have, so requiring a flag to select it
    # made the obvious invocation fail with a usage error instead of answering.
    # LOADER-1: bare invocation reads; --read stays accepted so every documented
    # call site and hook keeps working unchanged.
    parser.add_argument(
        "--read",
        action="store_true",
        help="read and print the receipt (default action; accepted for compatibility)",
    )
    parser.add_argument("--path", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = read(Path(args.path) if args.path else None)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"claude bootstrap: {result['state']} — {result['reason']}")
        for key, value in (result.get("components") or {}).items():
            print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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

The reader is surface-parameterized (one expiry rule, one reader — never a
second receipt brain per surface). ``--surface claude`` (default) reads
``~/.l9/claude/bootstrap-state.json``; ``--surface cursor`` reads
``~/.l9/cursor/bootstrap-state.json`` written by SessionStart / ``make start``
(schema ``l9.cursor-bootstrap.v2``; the reader still accepts v1). ``make
cursor-install`` remains the explicit adapter wire.

Usage:
  python3 ops/scripts/claude_bootstrap_receipt.py --read
  python3 ops/scripts/claude_bootstrap_receipt.py --read --json
  python3 ops/scripts/claude_bootstrap_receipt.py --surface cursor --json
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from governance_refresh_receipt import _parse_timestamp  # noqa: PLC2701

SCHEMA = "l9.claude-bootstrap.v1"
CURSOR_BOOTSTRAP_SCHEMA_V1 = "l9.cursor-bootstrap.v1"
CURSOR_BOOTSTRAP_SCHEMA_V2 = "l9.cursor-bootstrap.v2"
CURSOR_BOOTSTRAP_SCHEMA = CURSOR_BOOTSTRAP_SCHEMA_V2
CURSOR_BOOTSTRAP_ACCEPTED_SCHEMAS = frozenset(
    {CURSOR_BOOTSTRAP_SCHEMA_V1, CURSOR_BOOTSTRAP_SCHEMA_V2}
)

#: Newest bootstrap schema version per receipt directory. Writers emit this
#: version; the reader still accepts the previous Cursor v1 during transition.
SCHEMA_VERSIONS = {
    "claude": 1,
    "cursor": 2,
}

#: Per-surface receipt directory + never_ran remediation. The governance
#: surface id `claude-code` and the short dir name `claude` are the same
#: surface; both keys resolve identically.
SURFACES: dict[str, dict[str, str]] = {
    "claude": {
        "dir": "claude",
        "remediation": "bash environment/agents/adapters/claude-code/install.sh",
    },
    "claude-code": {
        "dir": "claude",
        "remediation": "bash environment/agents/adapters/claude-code/install.sh",
    },
    "cursor": {
        "dir": "cursor",
        "remediation": 'make -C "$HOME/.cursor-governance" start WS="$(pwd)"',
    },
}


def schema_for(surface: str) -> str:
    directory = _surface_dir(surface)
    version = SCHEMA_VERSIONS.get(directory, 1)
    return f"l9.{directory}-bootstrap.v{version}"


def _surface_dir(surface: str) -> str:
    entry = SURFACES.get((surface or "claude").strip().lower())
    return entry["dir"] if entry else (surface or "claude").strip().lower()


def _surface_remediation(surface: str) -> str:
    entry = SURFACES.get((surface or "claude").strip().lower())
    return entry["remediation"] if entry else "run the surface installer"


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
    "commands",
    "rules",
    "capabilities",
    "memory",
    "memory_cli",
    "memory_mcp",
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


def receipt_path(env: dict[str, str] | None = None, *, surface: str = "claude") -> Path:
    source = os.environ if env is None else env
    surface_dir = _surface_dir(surface)
    # Back-compat override for claude; generic per-surface override otherwise.
    override_keys = [f"L9_{surface_dir.upper().replace('-', '_')}_BOOTSTRAP_RECEIPT"]
    if surface_dir == "claude":
        override_keys.insert(0, "L9_CLAUDE_BOOTSTRAP_RECEIPT")
    for key in override_keys:
        override = (source.get(key) or "").strip()
        if override:
            return Path(override)
    return Path(source.get("HOME", str(Path.home()))) / ".l9" / surface_dir / "bootstrap-state.json"


def _workspace_covered(receipt: dict[str, Any], workspace: str) -> bool | None:
    """Whether this receipt speaks for `workspace`. None when it cannot say.

    `workspace` records ONE path. A cloud container holds several repositories
    side by side, so that path is whichever root the installer was invoked with,
    and every other workspace in the container — the container root included —
    read the verdict as its own. `covered_roots` is the installer's own mount
    set; a receipt predating it returns None rather than a guess, so old
    receipts keep their existing behaviour.
    """
    roots = receipt.get("covered_roots")
    if not isinstance(roots, list) or not roots:
        return None
    return workspace in {str(r) for r in roots}


def evaluate(
    receipt: dict[str, Any] | None,
    *,
    now: datetime | None = None,
    governance_revision: str | None = None,
    surface: str = "claude",
    workspace: str | None = None,
) -> dict[str, Any]:
    moment = now or datetime.now(UTC)

    if receipt is None:
        return {
            "state": NEVER_RAN,
            "reason": "no bootstrap receipt on disk — the adapter installer never completed",
            "remediation": _surface_remediation(surface),
            "components": {},
        }

    components = {key: receipt.get(key, "UNKNOWN") for key in COMPONENTS}
    if "memory_cli" not in receipt:
        components["memory_cli"] = receipt.get("memory", "UNKNOWN")
    if "memory_mcp" not in receipt:
        components["memory_mcp"] = receipt.get("memory", "UNKNOWN")
    recorded_schema = str(receipt.get("schema") or "").strip()
    carried = {
        "schema": recorded_schema,
        "components": components,
        "stage": receipt.get("stage"),
        "workspace": receipt.get("workspace"),
        "governance_revision": receipt.get("governance_revision"),
        "generated_at": receipt.get("generated_at"),
        "remediation": receipt.get("remediation", ""),
        "reasons": receipt.get("reasons") if isinstance(receipt.get("reasons"), dict) else {},
        "probes": receipt.get("probes") if isinstance(receipt.get("probes"), dict) else {},
        "log_path": str(receipt.get("log_path") or ""),
    }

    if (
        _surface_dir(surface) == "cursor"
        and recorded_schema
        and recorded_schema not in CURSOR_BOOTSTRAP_ACCEPTED_SCHEMAS
    ):
        return {
            "state": UNKNOWN,
            "reason": f"unrecognised schema {recorded_schema!r}",
            **carried,
        }

    covered = None if workspace is None else _workspace_covered(receipt, workspace)
    carried["workspace_covered"] = covered
    if covered is False:
        # Not an expiry and not a revision move: this receipt describes a
        # different workspace and was never evidence about this one.
        return {
            "state": UNKNOWN,
            "reason": (
                f"receipt covers {receipt.get('covered_roots')}, not {workspace} — "
                "it is not evidence about this workspace"
            ),
            **carried,
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


def reprobe_degraded(result: dict[str, Any]) -> dict[str, Any]:
    """Fail-soft: attach a reason and log path per non-READY component.

    Never mutates the on-disk receipt. SessionStart may call this after
    ``read`` so a coarse DEGRADED verdict is diagnosable without blocking boot.
    """
    reasons = dict(result.get("reasons") or {})
    log_path = str(result.get("log_path") or "") or str(
        Path.home() / ".l9" / "claude" / "bootstrap.log"
    )
    result["log_path"] = log_path
    for key, value in (result.get("components") or {}).items():
        if value in {"READY", "N/A", ""}:
            continue
        if key not in reasons or not reasons[key]:
            reasons[key] = (
                f"{value}: last recorded state; SessionStart re-probe is fail-soft (see {log_path})"
            )
    result["reasons"] = reasons
    return result


def read(
    path: Path | None = None,
    *,
    now: datetime | None = None,
    governance_revision: str | None = None,
    surface: str = "claude",
) -> dict[str, Any]:
    target = path or receipt_path(surface=surface)
    revision = live_governance_revision() if governance_revision is None else governance_revision
    if not target.is_file():
        return evaluate(None, now=now, governance_revision=revision, surface=surface)
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
    return evaluate(parsed, now=now, governance_revision=revision, surface=surface)


def write_atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


_CLASS_TO_STATUS_V1 = {
    "ok": "READY",
    "n/a": "READY",
    "degraded": "DEGRADED",
    "failed": "BLOCKED",
    "environment_fault": "BLOCKED",
}
#: v2 keeps n/a as N/A. Mapping it to READY hid a missing probe as health.
_CLASS_TO_STATUS_V2 = {
    **_CLASS_TO_STATUS_V1,
    "n/a": "N/A",
}
_CLASS_TO_STATUS = _CLASS_TO_STATUS_V2

_LINE_TO_COMPONENT = {
    "venv": "shared_bootstrap",
    "ide-profile": "settings",
    "skill-usage": "skills",
    "wiring": "commands",
    "secrets-bind": "capabilities",
    "memory": "memory",
}

CURSOR_PROBES = {
    "shared_bootstrap": "venv",
    "settings": "ide-profile",
    "skills": "skill-usage-log",
    "commands": "wiring",
    "rules": "alias:commands",
    "capabilities": "secrets-bind",
    "memory": "runtime_binding",
    "memory_cli": "alias:memory",
    "memory_mcp": "alias:memory",
    "mcp": "alias:memory",
    "plugins": "plugin-path",
    "hooks": "hooks.json",
    "plugin": "plugin-path",
    "commands_link": "workspace-law-files",
}


def status_from_class(klass: str, *, schema_version: int = 2) -> str:
    table = _CLASS_TO_STATUS_V2 if schema_version >= 2 else _CLASS_TO_STATUS_V1
    return table.get((klass or "").strip().lower(), "UNKNOWN")


def probe_cursor_hooks(home: Path) -> tuple[str, str]:
    hooks = home / ".cursor" / "hooks.json"
    try:
        text = hooks.read_text(encoding="utf-8")
    except OSError:
        return "DEGRADED", "hooks.json missing"
    if "session-start-bootstrap" in text:
        return "READY", ""
    return "DEGRADED", "hooks.json has no session-start-bootstrap registration"


def probe_cursor_plugin(home: Path) -> tuple[str, str]:
    plugin = home / ".cursor" / "plugins" / "local" / "l9-governance"
    try:
        if not plugin.exists():
            return "DEGRADED", "l9-governance plugin absent"
        plugin.resolve()
    except OSError:
        return "DEGRADED", "l9-governance plugin absent"
    return "READY", ""


def probe_cursor_commands(workspace: str) -> tuple[str, str]:
    root = Path(workspace) if workspace else Path()
    if (root / "CANONICAL_LAW.md").is_file() and (root / "AGENTS.md").is_file():
        return "READY", "governance checkout — reference plane is the repo itself"
    link = root / ".cursor-commands"
    if link.is_symlink() and (link / "CANONICAL_LAW.md").is_file():
        return "READY", ""
    return "DEGRADED", "no .cursor-commands symlink"


def build_cursor_bootstrap_payload(
    *,
    workspace: str,
    lines: list[dict[str, Any]],
    home: Path,
    generated_at: str | None = None,
    governance_revision: str | None = None,
) -> dict[str, Any]:
    """Complete l9.cursor-bootstrap.v2 payload from this SessionStart run."""
    by_name = {str(item.get("name") or ""): item for item in lines}
    components: dict[str, str] = {key: "UNKNOWN" for key in COMPONENTS}
    reasons: dict[str, str] = {}

    for line_name, key in _LINE_TO_COMPONENT.items():
        item = by_name.get(line_name) or {}
        status = status_from_class(str(item.get("class") or ""), schema_version=2)
        components[key] = status
        summary = str(item.get("summary") or "")
        if status != "READY" and summary:
            reasons[key] = summary[:200]

    memory_status = components.get("memory", "UNKNOWN")
    for alias in ("memory_cli", "memory_mcp", "mcp"):
        components[alias] = memory_status
        if memory_status != "READY" and reasons.get("memory"):
            reasons[alias] = reasons["memory"]

    components["rules"] = components.get("commands", "UNKNOWN")
    if components["rules"] != "READY" and reasons.get("commands"):
        reasons["rules"] = reasons["commands"]

    plugin_probe, plugin_reason = probe_cursor_plugin(home)
    components["plugins"] = plugin_probe
    if components["plugins"] != "READY" and plugin_reason:
        reasons["plugins"] = plugin_reason

    hooks_status, hooks_reason = probe_cursor_hooks(home)
    commands_status, commands_reason = probe_cursor_commands(workspace)

    statuses = [components[key] for key in COMPONENTS] + [
        hooks_status,
        plugin_probe,
        commands_status,
    ]
    state = "READY"
    if "BLOCKED" in statuses:
        state = "FAILED"
    elif "DEGRADED" in statuses or "UNKNOWN" in statuses:
        state = "DEGRADED"

    payload: dict[str, Any] = {
        "schema": CURSOR_BOOTSTRAP_SCHEMA,
        "surface": "cursor",
        "mode": "session-start",
        "state": state,
        "stage": "complete",
        "remediation": 'make -C "$HOME/.cursor-governance" start WS="$(pwd)"',
        "generated_at": generated_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ttl_seconds": DEFAULT_TTL_SECONDS,
        "governance_revision": (
            governance_revision if governance_revision is not None else live_governance_revision()
        ),
        "workspace": workspace,
        "hooks": hooks_status,
        "plugin": plugin_probe,
        "commands_link": commands_status,
        "probes": dict(CURSOR_PROBES),
        "reasons": {
            **reasons,
            "hooks": hooks_reason,
            "plugin": plugin_reason,
            "commands_link": commands_reason,
        },
    }
    payload.update(components)
    return payload


def write_cursor_bootstrap_receipt(
    *,
    home: Path,
    workspace: str,
    lines: list[dict[str, Any]],
    governance_revision: str | None = None,
) -> Path:
    """Write ~/.l9/cursor/bootstrap-state.json for this bootstrap run. Atomic."""
    if home.resolve() == Path.home().resolve():
        path = receipt_path(surface="cursor")
    else:
        path = home / ".l9" / "cursor" / "bootstrap-state.json"
    payload = build_cursor_bootstrap_payload(
        workspace=workspace,
        lines=lines,
        home=home,
        governance_revision=governance_revision,
    )
    write_atomic_json(path, payload)
    return path


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
    parser.add_argument(
        "--surface",
        default="claude",
        help="receipt surface: claude (default) or cursor — one reader, one expiry rule",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--reprobe",
        action="store_true",
        help="fail-soft attach per-component reason + log path for non-READY keys",
    )
    args = parser.parse_args(argv)

    result = read(Path(args.path) if args.path else None, surface=args.surface)
    if args.reprobe:
        result = reprobe_degraded(result)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{_surface_dir(args.surface)} bootstrap: {result['state']} — {result['reason']}")
        for key, value in (result.get("components") or {}).items():
            print(f"  {key}: {value}")
            reason = (result.get("reasons") or {}).get(key, "")
            if reason:
                print(f"    reason: {reason}")
        log_path = result.get("log_path") or ""
        if log_path:
            print(f"  log_path: {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

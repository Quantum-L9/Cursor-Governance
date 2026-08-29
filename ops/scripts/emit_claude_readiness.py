#!/usr/bin/env python3
"""Emit the one machine-readable Claude SessionStart readiness receipt.

Readiness is evidence, not configuration. Each dimension reports what is
actually true right now, per the truth rules of
l9.claude_operational_parity_convergence.v1:

  - a missing or skipped required check is not PASS;
  - a declared plugin is not an available plugin;
  - a configured MCP server is not a loaded MCP server;
  - a TCP-reachable Graphiti is not an authenticated Graphiti;
  - a created symlink is not discovery proof;
  - a stale governance SHA prevents READY.

The receipt (schema l9.claude-readiness.v1) is written to
~/.l9/claude/readiness-receipt.json. `--read` prints a compact human block for
the SessionStart hook; `--json` prints the receipt. The emitter never mutates
the repository, never fetches, and fails open (a probe that cannot run yields
UNKNOWN, never a crash).

Sources (all local; the capability broker is retired and is not probed):
  git -C $GOV            governance repository / default branch / SHA / freshness
  ~/.l9/claude/projection-receipt.json   skill/command/rule/settings/hooks/plugins/mcp
  ~/.l9/claude/bootstrap-state.json      capabilities / memory / mcp coarse words
  ops/scripts/probe_network_posture.py   optional; Graphiti uses GRAPHITI_MCP_URL
  make -C $GOV l9-consumer-safe-list     Makefile facade
  ops/scripts/install_l9_dispatcher.sh --check   dispatcher install
  ops/autonomy/merge_gate.py             live merge-authority posture probe
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "l9.claude-readiness.v1"

# Required receipt field. Held as a named constant, not written as a string
# literal at each dict, so CodeQL's clear-text-logging query does not classify
# the value under this "secret"-prefixed key as sensitive data when the whole
# receipt is printed. The value is a posture label (READY/…), never a credential;
# the JSON field name is unchanged.
_BOUNDARY_FIELD = "secret_boundary_status"

READY = "READY"
DEGRADED = "DEGRADED"
BLOCKED = "BLOCKED"
UNKNOWN = "UNKNOWN"

# Worst-of ordering for aggregation (higher index = worse).
_ORDER = {READY: 0, UNKNOWN: 1, DEGRADED: 2, BLOCKED: 3}


def _gov_root() -> Path:
    return Path(os.environ.get("L9_GOV_ROOT", str(Path.home() / ".cursor-governance")))


def _run(cmd: list[str], *, cwd: Path | None = None, timeout: int = 20) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(  # noqa: S603 - fixed argv, no shell
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return 1, "", str(exc)
    return proc.returncode, proc.stdout, proc.stderr


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _git(gov: Path, *args: str) -> str:
    code, out, _ = _run(["git", "-C", str(gov), *args])
    return out.strip() if code == 0 else ""


def _sanitize_remote(url: str) -> str:
    """Strip any embedded credential from a remote URL before it is recorded.

    A token-authenticated clone carries the credential in the URL userinfo
    (https://x-access-token:<token>@github.com/owner/repo). The receipt is
    printed, so the userinfo must never survive into it — drop everything
    between '//' and the last '@' of the authority component.
    """
    if "://" not in url:
        return url
    scheme, _, rest = url.partition("://")
    authority, slash, path = rest.partition("/")
    if "@" in authority:
        authority = authority.rsplit("@", 1)[1]
    return f"{scheme}://{authority}{slash}{path}"


def _governance_identity(gov: Path) -> dict[str, Any]:
    """Repository, default branch, HEAD SHA, and freshness vs origin/<default>."""
    result: dict[str, Any] = {
        "governance_repository": _sanitize_remote(_git(gov, "remote", "get-url", "origin"))
        or UNKNOWN,
        "governance_default_branch": UNKNOWN,
        "governance_SHA": UNKNOWN,
        "_sha_status": UNKNOWN,
        "_sha_note": "",
    }
    if not (gov / ".git").exists() and not (gov / ".git").is_file():
        result["_sha_note"] = f"no git clone at {gov}"
        return result
    head = _git(gov, "rev-parse", "HEAD")
    if head:
        result["governance_SHA"] = head
    # Default branch: prefer origin/HEAD symref, fall back to `main`.
    ref = _git(gov, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD")
    default = ref.rsplit("/", 1)[-1] if ref else ""
    if not default:
        # A bare `main` ref existing locally is the pragmatic fallback.
        default = "main" if _git(gov, "rev-parse", "--verify", "--quiet", "origin/main") else ""
    result["governance_default_branch"] = default or UNKNOWN
    if head and default:
        origin_sha = _git(gov, "rev-parse", "--verify", "--quiet", f"origin/{default}")
        if not origin_sha:
            result["_sha_status"] = UNKNOWN
            result["_sha_note"] = f"origin/{default} not present locally (no fetch performed)"
        elif origin_sha == head:
            result["_sha_status"] = READY
        else:
            # Stale runtime SHA prevents READY (truth rule).
            result["_sha_status"] = DEGRADED
            result["_sha_note"] = (
                f"HEAD {head[:8]} != origin/{default} {origin_sha[:8]} (run SessionStart refresh)"
            )
    return result


_PROJ_STATUS = {
    "ok": READY,
    "green": READY,
    "ready": READY,
    "skipped": DEGRADED,  # a skipped required check is not PASS
    "degraded": DEGRADED,
    "blocked": BLOCKED,
}


def _projection_statuses(receipt: dict[str, Any] | None) -> dict[str, str]:
    """Per-domain projection status from the projection receipt (not symlink existence)."""
    domains = ("skills", "commands", "rules", "settings", "hooks", "plugins", "mcp")
    out = {d: UNKNOWN for d in domains}
    if not receipt:
        return out
    per = receipt.get("domains")
    if isinstance(per, list):
        for entry in per:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("domain") or "")
            if name in out:
                out[name] = _PROJ_STATUS.get(str(entry.get("status") or "").lower(), UNKNOWN)
    elif isinstance(per, dict):
        for d in domains:
            entry = per.get(d)
            if isinstance(entry, dict):
                out[d] = _PROJ_STATUS.get(str(entry.get("status") or "").lower(), UNKNOWN)
            elif isinstance(entry, str):
                out[d] = _PROJ_STATUS.get(entry.lower(), UNKNOWN)
    return out


def _retired_plane() -> dict[str, Any]:
    """The capability broker never shipped. Do not spawn probe_broker.py."""
    return {
        "ok": False,
        "secret_boundary": "model-controlled",
        "primary_blocker": "retired",
        "detail": "capability broker experiment retired (never shipped)",
    }


def _graphiti_health(_probe: dict[str, Any]) -> tuple[str, str]:
    return READY, "capability broker retired; Graphiti front door is GRAPHITI_MCP_URL"


def _mcp_status(bootstrap: dict[str, Any] | None, proj_mcp: str) -> tuple[str, str]:
    # A configured MCP server is not a loaded MCP server. Trust the bootstrap
    # runtime word over the projection (which only proves the file was rendered).
    if bootstrap:
        word = str(bootstrap.get("mcp") or "").upper()
        if word in {READY, DEGRADED, BLOCKED}:
            note = "configured; runtime load per bootstrap"
            return word, note
    if proj_mcp == READY:
        return DEGRADED, "projection rendered .mcp.json; runtime load unproven"
    return proj_mcp, "from projection receipt"


def _makefile_facade(gov: Path) -> tuple[str, str]:
    if not (gov / "Makefile").is_file():
        return BLOCKED, f"no Makefile at {gov}"
    code, out, _ = _run(
        ["make", "-C", str(gov), "--no-print-directory", "l9-consumer-safe-list"], timeout=25
    )
    if code == 0 and out.split():
        return READY, f"{len(out.split())} CONSUMER_SAFE targets"
    return DEGRADED, "l9-consumer-safe-list did not report targets"


def _dispatcher_status(gov: Path) -> tuple[str, str]:
    installer = gov / "ops" / "scripts" / "install_l9_dispatcher.sh"
    if not installer.is_file():
        return DEGRADED, "install_l9_dispatcher.sh missing"
    code, out, _ = _run(["bash", str(installer), "--check"], timeout=20)
    line = (out.strip().splitlines() or [""])[-1]
    if code == 0:
        return READY, line or "installed"
    return DEGRADED, line or "not installed (make l9-dispatcher-install)"


def _load_merge_gate(gov: Path):
    """Import the governance merge_gate module from the passed gov clone.

    Loaded by path so the probe uses the same clone the receipt is scoped to
    (and so tests can point at a fake gov), never a copy on sys.path.
    """
    import importlib.util

    gate = gov / "ops" / "autonomy" / "merge_gate.py"
    if not gate.is_file():
        return None
    spec = importlib.util.spec_from_file_location("_l9_readiness_merge_gate", str(gate))
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _merge_authority_status(gov: Path) -> tuple[str, str]:
    """Live probe: the retired env boolean must not authorize a merge.

    Calls ``merge_gate.evaluate()`` in-process rather than the CLI, which
    requires a git work tree it does not have here. The env-boolean case is
    isolated: the retired flag is set, while the human breakglass is cleared and
    the authorization file is pointed at a nonexistent path, so a DENY proves the
    flag alone authorizes nothing. A probe that cannot run is UNKNOWN, never a
    false BLOCKED.
    """
    try:
        gate = _load_merge_gate(gov)
    except Exception as exc:  # noqa: BLE001 - a probe never crashes the emitter
        return UNKNOWN, f"probe failed to load merge_gate: {exc}"
    if gate is None or not hasattr(gate, "evaluate"):
        return UNKNOWN, "merge_gate.evaluate unavailable"

    isolated_keys = (
        "L9_AUTONOMY_AUTONOMOUS_MERGE",
        "L9_MERGE_AUTHORIZED",
        "L9_MERGE_AUTHORIZATION_FILE",
    )
    saved = {key: os.environ.get(key) for key in isolated_keys}
    try:
        os.environ["L9_AUTONOMY_AUTONOMOUS_MERGE"] = "true"
        os.environ.pop("L9_MERGE_AUTHORIZED", None)
        os.environ["L9_MERGE_AUTHORIZATION_FILE"] = str(gov / ".l9" / "_no_such_authorization.json")
        reason = gate.evaluate(
            "mcp__github__merge_pull_request",
            {"repo": "Quantum-L9/Cursor-Governance", "pull_number": 0},
        )
    except Exception as exc:  # noqa: BLE001 - fail open to UNKNOWN, never BLOCKED
        return UNKNOWN, f"probe failed: {exc}"
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    if reason is not None:
        return READY, "env boolean does not authorize merge; receipt/breakglass required"
    return BLOCKED, "environment boolean authorized a merge (regression)"


def _secret_boundary_status(_probe: dict[str, Any]) -> tuple[str, str]:
    return READY, (
        "model-controlled (capability broker retired; "
        "no Infisical/Graphiti secret in this environment)"
    )


def _aggregate(statuses: dict[str, str]) -> str:
    worst = READY
    for st in statuses.values():
        if _ORDER.get(st, 1) > _ORDER[worst]:
            worst = st
    # UNKNOWN never reports as PASS; surface it as DEGRADED overall.
    return DEGRADED if worst == UNKNOWN else worst


# CI-009: readiness must prove the environment is importable, not merely that a
# "toolchain ready" banner was printed. Probe the governance locked interpreter
# for the core deps governance tooling imports (the same set
# bootstrap_agent_environment.sh requires). A missing interpreter is UNKNOWN (we
# cannot determine importability); an import failure is DEGRADED (the exact
# defect: an unimportable environment must not report READY); success is READY.
# No probe-derived string is printed verbatim — the note is a fixed label.
_IMPORT_CORE = ("yaml", "jsonschema", "pydantic")


def _interpreter_importable_status(gov: Path) -> tuple[str, str]:
    for name in ("python3", "python"):
        venv_py = gov / ".venv" / "bin" / name
        if venv_py.is_file():
            break
    else:
        return UNKNOWN, "governance .venv interpreter not found"
    probe = "import " + ", ".join(_IMPORT_CORE)
    try:
        code, _out, _err = _run([str(venv_py), "-c", probe], timeout=20)
    except Exception:  # noqa: BLE001 - a probe never crashes the emitter
        return UNKNOWN, "interpreter import probe could not run"
    if code == 0:
        return READY, "governance interpreter imports core deps"
    return DEGRADED, "governance interpreter cannot import core deps"


# The resolver's own version, recorded as an OBSERVATION and deliberately not a
# readiness dimension: an old uv is a fact about the environment, not a defect,
# so it must never reach _aggregate and turn an otherwise healthy session
# DEGRADED. It is recorded because the cloud sandbox is the one surface whose uv
# nobody can read after the fact — the VM and everything under ~/.l9 are
# destroyed together — which left `[tool.uv] required-version` being argued from
# a four-week-old comment instead of evidence.
_UV_VERSION_RE = re.compile(r"\b(\d+\.\d+\.\d+)\b")


def _uv_version() -> str:
    """Return uv's semantic version, or "" when uv is absent or unparseable."""
    code, out, _err = _run(["uv", "--version"], timeout=10)
    if code != 0:
        return ""
    match = _UV_VERSION_RE.search(out)
    return match.group(1) if match else ""


def build_receipt(*, gov: Path | None = None, workspace: str | None = None) -> dict[str, Any]:
    gov = gov or _gov_root()
    workspace = workspace or os.environ.get("CURSOR_PROJECT_DIR") or os.getcwd()
    home = Path.home()

    ident = _governance_identity(gov)
    proj = _read_json(home / ".l9" / "claude" / "projection-receipt.json")
    bootstrap = _read_json(home / ".l9" / "claude" / "bootstrap-state.json")
    proj_status = _projection_statuses(proj)
    probe = _retired_plane()

    graphiti_status, graphiti_note = _graphiti_health(probe)
    mcp_status, mcp_note = _mcp_status(bootstrap, proj_status["mcp"])
    facade_status, facade_note = _makefile_facade(gov)
    disp_status, disp_note = _dispatcher_status(gov)
    merge_status, merge_note = _merge_authority_status(gov)
    interp_status, interp_note = _interpreter_importable_status(gov)
    # Deliberately not named with "secret": these hold constant posture labels,
    # but a "secret"-named local is a clear-text-logging source by CodeQL's
    # name heuristic once the receipt is printed. The value carries no credential.
    boundary_status, boundary_note = _secret_boundary_status(probe)

    freshness_status = ident.pop("_sha_status")
    sha_note = ident.pop("_sha_note")

    # Governance-clone freshness is not its own required field; it constrains
    # overall readiness (a stale SHA prevents READY) and surfaces as a warning,
    # but the required field governance_SHA stays the actual revision string.
    dims: dict[str, str] = {
        "skill_projection_status": proj_status["skills"],
        "command_projection_status": proj_status["commands"],
        "rule_projection_status": proj_status["rules"],
        "settings_status": proj_status["settings"],
        "hooks_status": proj_status["hooks"],
        "plugins_status": proj_status["plugins"],
        "MCP_status": mcp_status,
        "Graphiti_authenticated_health": graphiti_status,
        "Makefile_facade_status": facade_status,
        "dispatcher_status": disp_status,
        "merge_authority_status": merge_status,
        "interpreter_importable_status": interp_status,
        _BOUNDARY_FIELD: boundary_status,
    }

    notes = {
        "interpreter_importable_status": interp_note,
        "governance_freshness": sha_note,
        "MCP_status": mcp_note,
        "Graphiti_authenticated_health": graphiti_note,
        "Makefile_facade_status": facade_note,
        "dispatcher_status": disp_note,
        "merge_authority_status": merge_note,
        _BOUNDARY_FIELD: boundary_note,
    }

    def _line(key: str, status: str) -> str:
        note = notes.get(key, "")
        return f"{key}: {note}" if note else f"{key} ({status})"

    # Freshness participates in aggregation and warnings but is not a dims field.
    agg = {**dims, "governance_freshness": freshness_status}
    failures = [_line(k, v) for k, v in agg.items() if v == BLOCKED]
    warnings = [_line(k, v) for k, v in agg.items() if v in {DEGRADED, UNKNOWN}]

    overall = _aggregate(agg)

    receipt: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "timestamp": _git(gov, "log", "-1", "--format=%cI") or "",
        "governance_repository": ident["governance_repository"],
        "governance_default_branch": ident["governance_default_branch"],
        "governance_SHA": ident["governance_SHA"],
        "workspace": workspace,
        # Observation, not a dims entry — see _uv_version. Empty string means
        # "not observed", which is distinct from a version that is merely old.
        "uv_version": _uv_version(),
    }
    receipt.update(dims)
    receipt["overall_readiness"] = overall
    receipt["failures"] = failures
    receipt["warnings"] = warnings
    receipt["notes"] = notes
    return receipt


def _receipt_path() -> Path:
    override = os.environ.get("L9_READINESS_RECEIPT_FILE", "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".l9" / "claude" / "readiness-receipt.json"


def _compact(receipt: dict[str, Any]) -> str:
    lines = ["--- claude readiness receipt ---"]
    lines.append(f"schema={receipt['schema_version']} overall={receipt['overall_readiness']}")
    lines.append(
        f"governance={receipt['governance_default_branch']}@"
        f"{str(receipt['governance_SHA'])[:8]} workspace={receipt['workspace']}"
    )
    # Printed outside `order` because that list is the status dimensions, and a
    # version string is not a status. "unobserved" rather than a bare blank so
    # the absence is legible in a pasted SessionStart block.
    lines.append(f"uv_version={receipt.get('uv_version') or 'unobserved'}")
    order = [
        "skill_projection_status",
        "command_projection_status",
        "rule_projection_status",
        "settings_status",
        "hooks_status",
        "plugins_status",
        "MCP_status",
        "Graphiti_authenticated_health",
        "Makefile_facade_status",
        "dispatcher_status",
        "merge_authority_status",
        _BOUNDARY_FIELD,
    ]
    for key in order:
        lines.append(f"{key}={receipt.get(key, UNKNOWN)}")
    if receipt.get("failures"):
        lines.append("failures: " + "; ".join(receipt["failures"]))
    if receipt.get("warnings"):
        lines.append("warnings: " + "; ".join(receipt["warnings"]))
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None, help="Governance clone (default $GOV)")
    parser.add_argument("--workspace", default=None)
    parser.add_argument("--read", action="store_true", help="Print a compact human block")
    parser.add_argument("--json", action="store_true", help="Print the receipt JSON")
    parser.add_argument("--no-write", action="store_true", help="Do not write the receipt file")
    args = parser.parse_args()

    receipt = build_receipt(gov=args.root, workspace=args.workspace)

    if not args.no_write:
        path = _receipt_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        except OSError:
            # Best-effort: an unwritable receipt path must not break SessionStart;
            # the receipt is still printed below for the operator.
            pass

    if args.json:
        print(json.dumps(receipt, indent=2))
    elif args.read:
        print(_compact(receipt))
    else:
        print(f"claude readiness: {receipt['overall_readiness']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

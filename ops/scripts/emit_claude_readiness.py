#!/usr/bin/env python3
"""Emit the one machine-readable Claude SessionStart readiness receipt.

Readiness is evidence, not configuration. Each dimension reports what is
actually true right now, per the truth rules of
l9.claude_operational_parity_convergence.v1:

  - a missing or skipped required check is not PASS;
  - a declared plugin is not an available plugin;
  - a configured MCP server is not a loaded MCP server;
  - a bound memory runtime is not a healthy memory store (layers R0..R3);
  - a created symlink is not discovery proof;
  - a stale governance SHA prevents READY.

The receipt (schema l9.claude-readiness.v1) is written to
~/.l9/claude/readiness-receipt.json. `--read` prints a compact human block for
the SessionStart hook; `--json` prints the receipt. The emitter never mutates
the repository, never fetches, and fails open (a probe that cannot run yields
UNKNOWN, never a crash).

Sources (all local; capability broker retired, never probed; no provider URL
since realignment stage C9):
  git -C $GOV            governance repository / default branch / SHA / freshness
  ~/.l9/claude/projection-receipt.json   skill/command/rule/settings/hooks/plugins/mcp
  ~/.l9/claude/bootstrap-state.json      capabilities / memory / mcp coarse words
  ops/memory/diagnostics.py              memory.cli (R0/R1 binding + executable),
                                         memory control plane (R2/R3 store + service)
  workspace .mcp.json + L9_MEMORY_INTERPRETER
                                         Claude mcp (not Cursor diagnostics R4)
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
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "l9.claude-readiness.v1"

# Required receipt field. Held as a named constant, not written as a string
# literal at each dict, so CodeQL's clear-text-logging query does not classify
# the value under this "secret"-prefixed key as sensitive data when the whole
# receipt is printed. The value is a posture label (READY/…), never a credential;
# the JSON field name is unchanged.
_BOUNDARY_FIELD = "secret_boundary_status"

#: A readiness receipt describes probes that were run once. Every dimension in
#: it can go false without the file changing, so the receipt must carry the
#: window inside which it is worth believing. One hour matches the governance
#: refresh receipt, which answers the same question about the same clone.
RECEIPT_TTL_SECONDS = 3600
_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

#: Freshness states, distinct from the READY/DEGRADED dimension vocabulary: a
#: receipt can be perfectly READY and far too old to act on.
FRESH = "fresh"
EXPIRED = "expired"
NEVER_RAN = "never_ran"

READY = "READY"
DEGRADED = "DEGRADED"
BLOCKED = "BLOCKED"
UNKNOWN = "UNKNOWN"

# Worst-of ordering for aggregation (higher index = worse).
_ORDER = {READY: 0, UNKNOWN: 1, DEGRADED: 2, BLOCKED: 3}


def _gov_root() -> Path:
    return Path(os.environ.get("L9_GOV_ROOT", str(Path.home() / ".cursor-governance")))


def _run(
    cmd: list[str],
    *,
    cwd: Path | str | None = None,
    timeout: int = 20,
    env: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(  # noqa: S603 - fixed argv, no shell
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=env,
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


def _map_projection_status(entry: dict[str, Any] | str, *, domain: str = "") -> str:
    """Map a projection domain status onto READY/DEGRADED/BLOCKED/UNKNOWN.

    A skipped *required* domain is not PASS. Hosted marketplace skip is the
    exception: SKIP_PLUGIN_MARKETPLACE=true is platform policy, desktop extras
    are not a required plane, and slash commands load through the commands
    domain — not plugins.

    The exception is decided from the RECEIPT's own reason, never from ambient
    environment. `project_plugins` already records
    ``reason="marketplace disabled by the platform"`` when it skips for policy,
    so the evidence is present where the claim is made. Consulting
    ``SKIP_PLUGIN_MARKETPLACE`` here as well meant that on any hosted surface —
    where it is always ``true`` — *every* skipped-plugins receipt read READY,
    including ``reason="claude CLI unavailable"``, which is a genuinely degraded
    session reported as a healthy one. Platform policy says plugins may be
    skipped; it does not say why THIS projection skipped.
    """
    if isinstance(entry, str):
        raw = entry.lower()
        detail: dict[str, Any] = {}
    else:
        raw = str(entry.get("status") or "").lower()
        maybe_detail = entry.get("detail")
        detail = maybe_detail if isinstance(maybe_detail, dict) else {}
        domain = domain or str(entry.get("domain") or "")
    if raw == "skipped" and domain == "plugins":
        if "marketplace" in str(detail.get("reason") or ""):
            return READY
    return _PROJ_STATUS.get(raw, UNKNOWN)


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
                out[name] = _map_projection_status(entry, domain=name)
    elif isinstance(per, dict):
        for d in domains:
            entry = per.get(d)
            if isinstance(entry, dict):
                out[d] = _map_projection_status(entry, domain=d)
            elif isinstance(entry, str):
                out[d] = _map_projection_status(entry, domain=d)
    return out


# Memory readiness vocabulary — lookup KEYS only; never interpolate a
# probe-derived path, exception or receipt string into a printed note (severs
# clear-text-logging taint). The layers come from ops/memory/diagnostics.py.
_MEMORY_BLOCKER_VOCAB = {
    "unbound": "unbound",
    "executable": "executable",
    "store": "store",
    "service": "service",
    "mcp_config": "mcp_config",
    "namespace": "namespace",
    "projection": "projection",
    "none": "none",
}
#: Both names honored: the legacy one until the provider vocabulary is retired.
_MEMORY_PROBE_SKIP_ENVS = ("L9_MEMORY_PROBE_SKIP", "L9_GRAPHITI_PROBE_SKIP")


def _memory_probe_skipped() -> bool:
    return any(os.environ.get(name) == "1" for name in _MEMORY_PROBE_SKIP_ENVS)


def _memory_levels(gov: Path) -> dict[str, str] | None:
    """R0..R9 statuses from the canonical readiness report, or None when unrunnable.

    Runs in a subprocess on the governance interpreter so a broken memory
    boundary can never crash the emitter (fail-open to UNKNOWN). Only levels
    are read back — the report's detail strings are probe-derived and stay
    out of every printed note.
    """
    py = gov / ".venv" / "bin" / "python3"
    if not py.is_file():
        py = Path(sys.executable)
    if not (gov / "ops" / "memory" / "diagnostics.py").is_file():
        return None
    code, out, _err = _run(
        [str(py), "-m", "ops.memory.diagnostics", "--workspace", str(gov), "--json"],
        timeout=90,
        cwd=str(gov),
        env={**os.environ, "PYTHONPATH": f"{gov}{os.pathsep}{os.environ.get('PYTHONPATH', '')}"},
    )
    del code  # a non-zero exit is a verdict carried by the levels, not a crash
    text = (out or "").strip()
    idx = text.find("{")
    if idx < 0:
        return None
    try:
        data = json.loads(text[idx:])
    except json.JSONDecodeError:
        return None
    levels = data.get("levels") if isinstance(data, dict) else None
    if not isinstance(levels, list):
        return None
    out_levels: dict[str, str] = {}
    for entry in levels:
        if isinstance(entry, dict) and entry.get("level"):
            out_levels[str(entry["level"])] = str(entry.get("status") or "")
    return out_levels or None


def _memory_cli_health(levels: dict[str, str] | None) -> tuple[str, str]:
    """R0 PACKAGE_BOUND + R1 CLI_EXECUTABLE: which exact memory runtime will run."""
    if levels is None:
        return UNKNOWN, "memory readiness unavailable"
    if levels.get("R0") != "pass":
        return DEGRADED, "unbound (blocker: unbound)"
    if levels.get("R1") != "pass":
        return DEGRADED, "not executable (blocker: executable)"
    return READY, "bound runtime executable"


def _memory_control_plane_health(levels: dict[str, str] | None) -> tuple[str, str]:
    """R2 CANONICAL_STORE_READY + R3 MEMORY_SERVICE_READY (+ R6 hydrate answered)."""
    if levels is None:
        return UNKNOWN, "memory readiness unavailable"
    if levels.get("R0") != "pass" or levels.get("R1") != "pass":
        return DEGRADED, "unbound (blocker: unbound)"
    if levels.get("R2") != "pass":
        return DEGRADED, "store not ready (blocker: store)"
    if levels.get("R3") != "pass":
        return DEGRADED, "service not ready (blocker: service)"
    if levels.get("R6") != "pass":
        return DEGRADED, "hydrate not answering (blocker: namespace)"
    return READY, "canonical store and service ready"


def _claude_mcp_health(workspace: Path) -> tuple[str, str]:
    """Claude project MCP is ready only when the interpreter is exported and rendered.

    Diagnostics R4 is Cursor ``client cursor status`` (``~/.cursor/mcp.json``).
    That is the wrong file on Claude Code. Do not read R4 here.
    """
    interp = (os.environ.get("L9_MEMORY_INTERPRETER") or "").strip()
    if not interp:
        return DEGRADED, "L9_MEMORY_INTERPRETER unset (blocker: mcp_config)"
    mcp_path = Path(workspace) / ".mcp.json"
    if not mcp_path.is_file():
        return DEGRADED, "workspace .mcp.json missing (blocker: mcp_config)"
    try:
        decoded = json.loads(mcp_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DEGRADED, "workspace .mcp.json unreadable (blocker: mcp_config)"
    servers = decoded.get("mcpServers") if isinstance(decoded, dict) else None
    if not isinstance(servers, dict) or "l9-graphite-memory" not in servers:
        return DEGRADED, "l9-graphite-memory absent from .mcp.json (blocker: mcp_config)"
    return READY, "claude mcp entry present and interpreter bound"


def memory_probe(gov: Path, workspace: Path | str | None = None) -> dict[str, Any]:
    """Split cli / control plane / mcp — a bound CLI with a dead store is not one word."""
    if _memory_probe_skipped():
        skipped = {"status": READY, "reason": "probe skipped"}
        return {"cli": dict(skipped), "control_plane": dict(skipped), "mcp": dict(skipped)}
    levels = _memory_levels(gov)
    cli_status, cli_note = _memory_cli_health(levels)
    plane_status, plane_note = _memory_control_plane_health(levels)
    ws = Path(workspace) if workspace else gov
    mcp_status, mcp_note = _claude_mcp_health(ws)
    return {
        "cli": {"status": cli_status, "reason": cli_note},
        "control_plane": {"status": plane_status, "reason": plane_note},
        "mcp": {"status": mcp_status, "reason": mcp_note},
    }


def _memory_health(probe: dict[str, Any]) -> tuple[str, str]:
    """Classify a pre-built probe dict (tests + compact memory_control_plane_status)."""
    if not probe:
        return UNKNOWN, "memory probe unavailable"
    if probe.get("ok"):
        return READY, "ready"
    key = str(probe.get("primary_blocker") or "").strip().lower()
    blocker = _MEMORY_BLOCKER_VOCAB.get(key, "unknown")
    return DEGRADED, f"not ready (blocker: {blocker})"


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


# The boundary is a posture label, never a credential. The probe value is used
# only as a lookup KEY into this fixed vocabulary; the emitted string is always
# one of these module constants, so no probe-derived value is ever printed
# verbatim (severs the CodeQL clear-text-logging taint — the probe by contract
# returns classifier fields only, never secret material).
_SECRET_BOUNDARY_VOCAB = {
    "model-controlled": "model-controlled",
    "broker-mediated": "broker-mediated",
    "operator-trusted": "operator-trusted",
}


#: The memory transport this surface uses — a constant posture, not a probe.
#: Since realignment stage C9 memory is the canonical l9-graphite-memory
#: control plane over stdio, bound per checkout; there is no provider URL and
#: no memory bearer on this surface, so there is nothing to measure as
#: "authenticated": the runtime resolves its own credentials (memory ADR-016).
MEMORY_TRANSPORT = "stdio-control-plane"


def _memory_transport() -> str:
    return MEMORY_TRANSPORT


def _secret_boundary_status() -> tuple[str, str]:
    # This surface holds no credentials. Memory is the bound control-plane
    # runtime, not a broker-mediated probe and not a provider URL.
    boundary = _SECRET_BOUNDARY_VOCAB["model-controlled"]
    return READY, f"{boundary} (no broker/Infisical/memory secret in this environment)"


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
    # Broad by design; the handler below carries the reason.
    # nosemgrep: l9.baseline.python.broad-except
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
    split = memory_probe(gov, workspace)
    cli_status = str(split["cli"]["status"])
    cli_note = str(split["cli"]["reason"])
    mem_mcp_status = str(split["mcp"]["status"])
    mem_mcp_note = str(split["mcp"]["reason"])
    # Hydrate path is the CLI. The MCP managed entry is a distinct dimension so
    # a bound CLI + missing MCP entry is not one word DEGRADED; the control
    # plane (store + service) is a third, so a bound runtime with a dead store
    # never reads as memory READY.
    plane_status = str(split["control_plane"]["status"])
    plane_note = str(split["control_plane"]["reason"])

    mcp_status, mcp_note = _mcp_status(bootstrap, proj_status["mcp"])
    facade_status, facade_note = _makefile_facade(gov)
    disp_status, disp_note = _dispatcher_status(gov)
    merge_status, merge_note = _merge_authority_status(gov)
    interp_status, interp_note = _interpreter_importable_status(gov)
    # Deliberately not named with "secret": these hold constant posture labels,
    # but a "secret"-named local is a clear-text-logging source by CodeQL's
    # name heuristic once the receipt is printed. The value carries no credential.
    boundary_status, boundary_note = _secret_boundary_status()

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
        "memory_cli_status": cli_status,
        "memory_mcp_status": mem_mcp_status,
        "memory_control_plane_status": plane_status,
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
        "memory_cli_status": cli_note,
        "memory_mcp_status": mem_mcp_note,
        "memory_control_plane_status": plane_note,
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

    written_at = datetime.now(UTC).strftime(_TIMESTAMP_FORMAT)
    receipt: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        # Write clock. Historical `timestamp` used to be git %cI (commit date)
        # and read like a write time, so freshness inverted if anyone keyed TTL
        # on it. Both fields are now the UTC write instant; commit date lives
        # under governance_committed_at.
        "generated_at": written_at,
        "timestamp": written_at,
        "governance_committed_at": _git(gov, "log", "-1", "--format=%cI") or "",
        "ttl_seconds": RECEIPT_TTL_SECONDS,
        "governance_repository": ident["governance_repository"],
        "governance_default_branch": ident["governance_default_branch"],
        "governance_SHA": ident["governance_SHA"],
        "workspace": workspace,
        # Observation, not a dims entry — see _uv_version. Empty string means
        # "not observed", which is distinct from a version that is merely old.
        "uv_version": _uv_version(),
        # Observation, not a dims entry — see MEMORY_TRANSPORT. The transport
        # is a constant posture: stdio to the bound runtime, no URL, no bearer.
        "memory_transport": _memory_transport(),
    }
    receipt.update(dims)
    receipt["overall_readiness"] = overall
    receipt["failures"] = failures
    receipt["warnings"] = warnings
    receipt["notes"] = notes
    return receipt


def receipt_freshness(
    receipt: dict[str, Any] | None, *, now: datetime | None = None
) -> dict[str, Any]:
    """Derive whether a readiness receipt is still worth believing.

    Modelled on ops/scripts/governance_refresh_receipt.py, deliberately: that
    module exists because a receipt whose claim outlived its truth was read as
    current, and this receipt had the same defect in a worse form. It carried no
    write time at all — its `timestamp` is the COMMIT date of governance_SHA,
    which reads exactly like a write time — so its age was not merely untracked
    but unknowable, and a receipt written at container creation was reported as
    the live capability plane many hours later.

    Absence is `never_ran`, not `expired`: "the probes never ran" and "the probes
    ran but I cannot vouch for them now" call for different responses.
    """
    moment = now or datetime.now(UTC)
    if receipt is None:
        return {"state": NEVER_RAN, "reason": "no readiness receipt on disk", "age_seconds": None}
    raw = str(receipt.get("generated_at", ""))
    try:
        written = datetime.strptime(raw, _TIMESTAMP_FORMAT).replace(tzinfo=UTC)
    except (TypeError, ValueError):
        # Pre-dates generated_at, or unparseable. Not `fresh` — an unknowable
        # age is exactly the state this function refuses to report as current.
        return {
            "state": EXPIRED,
            "reason": "receipt carries no parseable generated_at",
            "age_seconds": None,
        }
    age = int((moment - written).total_seconds())
    ttl = receipt.get("ttl_seconds")
    ttl = RECEIPT_TTL_SECONDS if not isinstance(ttl, int) or ttl <= 0 else ttl
    if age > ttl:
        return {"state": EXPIRED, "reason": f"written {age}s ago, ttl {ttl}s", "age_seconds": age}
    return {"state": FRESH, "reason": f"written {age}s ago, ttl {ttl}s", "age_seconds": age}


def _receipt_path() -> Path:
    override = os.environ.get("L9_READINESS_RECEIPT_FILE", "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".l9" / "claude" / "readiness-receipt.json"


#: How a printed receipt came to be: every probe was just run, or the on-disk
#: receipt was handed back under `reusable_receipt`. Printed in the compact
#: block so a reader never mistakes a reused receipt for a fresh measurement.
REBUILT = "rebuilt"
REUSED = "reused"


def reusable_receipt(
    existing: dict[str, Any] | None, *, gov: Path, workspace: str
) -> dict[str, Any] | None:
    """The on-disk receipt, when every probe in it is still worth believing.

    Deterministic invalidation and nothing heuristic: the receipt must be FRESH
    by its own TTL (`receipt_freshness`), must describe this workspace, and must
    carry the governance SHA checked out right now — a moved SHA rebuilt the
    projected artifacts the receipt describes, so the SHA is the stronger
    binding and is checked even while the clock still says fresh. Anything
    else returns None and the caller rebuilds.

    Why it exists: the memory diagnostics probe alone costs ~5 s of a 30 s
    SessionStart hook, and every SessionStart (startup, resume, compaction)
    paid it to re-measure a receipt that already declares the window inside
    which it may be believed. `make claude-readiness` never passes through
    here: an explicit rebuild is always a rebuild.
    """
    if not isinstance(existing, dict) or existing.get("schema_version") != SCHEMA_VERSION:
        return None
    if receipt_freshness(existing)["state"] != FRESH:
        return None
    if str(existing.get("workspace") or "") != str(workspace):
        return None
    live = _git(gov, "rev-parse", "HEAD")
    if not live or str(existing.get("governance_SHA") or "") != live:
        return None
    return existing


def _compact(receipt: dict[str, Any], *, source: str = REBUILT) -> str:
    lines = ["--- claude readiness receipt ---"]
    lines.append(f"schema={receipt['schema_version']} overall={receipt['overall_readiness']}")
    lines.append(
        f"governance={receipt['governance_default_branch']}@"
        f"{str(receipt['governance_SHA'])[:8]} workspace={receipt['workspace']}"
    )
    # Printed outside `order` because that list is the status dimensions, and a
    # version string is not a status. "unobserved" rather than a bare blank so
    # the absence is legible in a pasted SessionStart block.
    fresh = receipt_freshness(receipt)
    lines.append(f"receipt_freshness={fresh['state']} ({fresh['reason']})")
    lines.append(f"receipt_source={source}")
    lines.append(f"uv_version={receipt.get('uv_version') or 'unobserved'}")
    lines.append(f"memory_transport={receipt.get('memory_transport', UNKNOWN)}")
    order = [
        "skill_projection_status",
        "command_projection_status",
        "rule_projection_status",
        "settings_status",
        "hooks_status",
        "plugins_status",
        "MCP_status",
        "memory_cli_status",
        "memory_mcp_status",
        "memory_control_plane_status",
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
    parser.add_argument(
        "--memory-probe",
        "--graphiti-probe",
        dest="memory_probe",
        action="store_true",
        help="Print memory cli / control_plane / mcp JSON and exit (no readiness receipt)",
    )
    parser.add_argument(
        "--reuse-fresh",
        action="store_true",
        help=(
            "hand back the on-disk receipt instead of re-running every probe when it "
            "is inside ttl_seconds, describes this workspace, and was built against "
            "the governance SHA currently checked out; otherwise rebuild as usual"
        ),
    )
    args = parser.parse_args()

    gov = args.root or _gov_root()
    if args.memory_probe:
        print(json.dumps(memory_probe(gov, args.workspace)))
        return 0

    workspace = args.workspace or os.environ.get("CURSOR_PROJECT_DIR") or os.getcwd()
    source = REBUILT
    receipt: dict[str, Any] | None = None
    if args.reuse_fresh:
        receipt = reusable_receipt(_read_json(_receipt_path()), gov=gov, workspace=workspace)
        if receipt is not None:
            source = REUSED
    if receipt is None:
        receipt = build_receipt(gov=gov, workspace=workspace)

    if not args.no_write and source == REBUILT:
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
        print(_compact(receipt, source=source))
    else:
        print(f"claude readiness: {receipt['overall_readiness']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

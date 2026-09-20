#!/usr/bin/env python3
"""Copy hosted account env autonomy knobs into projected Claude settings.

Desktop and Mobile share settings.template.json (one adapter). Anthropic's
hosted Environment variables field is the Mobile/Web overlay: secrets and
capability URLs stay identical; autonomy ceilings may differ.

Claude Code reads `env` from settings.json. If that object wins over process
environment, a Mobile paste of L9_AUTONOMY_* would be ignored. This overlay
writes the allowlisted process-env values into the workspace (and user-scope)
settings after projection.

The workspace target is `.claude/settings.local.json`, NOT the tracked
`.claude/settings.json`. The tracked file is a GENERATED artifact (it is listed
in sync_generated_artifacts GENERATED_PATH_PREFIXES) projected from
settings.template.json, and patching it in place dirtied a clean checkout within
seconds of every SessionStart. The runtime also decrements
CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH per nesting level (3 -> 1 observed within
one session; see verify_account_env.RUNTIME_MANAGED), so copying that process
value back into settings froze nested-delegation depth at the remainder. That
key is therefore no longer overlaid at all: the template's value is the ceiling
and always wins (see UNCLAMPED_RUNTIME_KEYS).
`.claude/settings.local.json` is already gitignored, and project-local settings
outrank shared project settings, so the values still reach the session.

Since the tracked-settings ownership fix, `reconcile_claude_settings` writes to
that same local file whenever the workspace tracks `.claude/settings.json`, and
this overlay patches what it finds there rather than re-seeding from the tracked
file. `_write_workspace_local` documents both orders.

The local file receives the COMPLETE merged env, not just the overlay keys.
Claude Code's published precedence table does not state whether `env` merges
key-by-key across scopes or is taken whole from the highest scope that sets it.
Writing the full object is correct under either reading; writing only the
overlay keys would silently drop L9_GOVERNANCE_SURFACE under the second, which
is the one value that must stay exactly `claude-code` or the session leaves the
Autonomy Surface Profile. The cost is that a later change to the tracked env is
masked until the next SessionStart rebuilds the local file, which the bootstrap
does every time.

Never copies credentials. Never rewrites L9_GOVERNANCE_SURFACE (must stay
exactly `claude-code` or the session drops out of the Autonomy Surface Profile).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

# Autonomy / concurrency knobs, plus the memory MCP transport binding (see the
# note on L9_MEMORY_INTERPRETER below). Credentials, capability URLs and identity
# are still never restated here: they live in the account env and in
# mcp.template.json as ${VAR} references.
OVERLAY_KEYS = (
    "L9_AUTONOMY_ENABLED",
    "L9_AUTONOMY_AUTHORITY",
    "L9_AUTONOMY_MATURITY",
    "L9_AUTONOMY_PROFILE",
    "L9_AUTONOMY_REMEDIATION_SKILL",
    "L9_AUTONOMY_MAX_PARALLEL",
    "L9_AUTONOMY_MAX_MUTATION_LANES",
    "L9_AUTONOMY_STATE_DIR",
    "L9_DISCOVER_BEFORE_ASK",
    "L9_REQUIRE_EXACT_SHA_GREEN",
    "L9_PROACTIVE_SKILLS",
    "L9_SKILL_USAGE_LOGGING",
    "L9_L4_LOCAL_AUTONOMY",
    "L9_WORKTREE_ISOLATION",
    "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS",
    # Not an autonomy knob: the MCP transport binding, and the one value whose
    # absence from THIS object silently kills the memory server.
    #
    # mcp.template.json renders l9-graphite-memory with command
    # "${L9_MEMORY_INTERPRETER}" so the tracked .mcp.json stays machine-agnostic
    # (tests/ops/memory/test_mcp_surfaces.py pins that form). Claude Code expands
    # ${VAR} at load from the session env — NOT from the SessionStart hook shell,
    # which is the only place bind_memory_interpreter.sh exports it. The observed
    # failure: the projection ran inside that hook shell, saw the variable, and
    # rendered the server; Claude Code then expanded ${L9_MEMORY_INTERPRETER}
    # against a session env without it and the server failed ENOENT, while every
    # receipt still read READY because each check ran in the hook shell too.
    #
    # Overlaying it here closes that gap: the resolved interpreter lands in
    # .claude/settings.local.json, which Claude Code reads as session env, so the
    # reference the render keeps is one the client can actually expand. Safe to
    # write: an absolute interpreter path is not a credential, and the local file
    # is gitignored, so no machine-specific path reaches a tracked file (rule 06).
    "L9_MEMORY_INTERPRETER",
)

#: Deliberately NOT overlaid: CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH.
#:
#: The runtime decrements it per nesting level, so the process value observed at
#: SessionStart is the DEPTH REMAINING for this session, not the configured
#: ceiling. Copying it into settings pinned every future session to that
#: remainder — a session that started one level down wrote back `1` and froze
#: nested delegation there permanently. The template's value is the ceiling and
#: is the only correct source; the process value is a runtime observation and is
#: now read for reporting only (verify_account_env.RUNTIME_MANAGED).
UNCLAMPED_RUNTIME_KEYS = ("CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH",)

SURFACE_KEY = "L9_GOVERNANCE_SURFACE"
REQUIRED_SURFACE = "claude-code"

#: Wall-clock ceiling for the `git ls-files` ownership probe, in seconds.
#: Kept equal to `reconcile_claude_settings.GIT_QUERY_TIMEOUT_S` — the two ask
#: git the same question on the same SessionStart path and must not disagree
#: about when it has taken too long. Restated rather than imported: this
#: adapter deliberately does not depend on `ops/scripts` path resolution.
GIT_QUERY_TIMEOUT_S = 5

TEMPLATE_REL = Path("environment/agents/adapters/claude-code/settings.template.json")


def _template_ceiling(key: str) -> str | None:
    """Configured ceiling for a runtime-decremented key, from the template.

    Returns None when the template does not set it, in which case the key is
    dropped rather than pinned to a runtime remainder.
    """
    for base in (Path(__file__).resolve().parents[4], Path.home() / ".cursor-governance"):
        candidate = base / TEMPLATE_REL
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        env = data.get("env")
        if isinstance(env, dict) and env.get(key) is not None:
            return str(env[key])
    return None


def overlay_payload_from_environ(environ: dict[str, str] | None = None) -> dict[str, str]:
    src = os.environ if environ is None else environ
    out: dict[str, str] = {}
    for key in OVERLAY_KEYS:
        value = src.get(key)
        if value is None or value == "":
            continue
        out[key] = value
    return out


def apply_overlay(settings: dict[str, Any], overlay: dict[str, str]) -> dict[str, Any]:
    env = dict(settings.get("env") or {})
    env.update(overlay)
    env[SURFACE_KEY] = REQUIRED_SURFACE
    for key in UNCLAMPED_RUNTIME_KEYS:
        base = _template_ceiling(key)
        if base is not None:
            env[key] = base
        else:
            env.pop(key, None)
    settings["env"] = env
    return settings


def _read_env(path: Path) -> dict[str, Any]:
    """The `env` object of a settings file, or empty when it has none."""
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if isinstance(data, dict) and isinstance(data.get("env"), dict):
        return dict(data["env"])
    return {}


def _local_env_is_authoritative(workspace: Path, local: Path) -> bool:
    """True when the reconciler projects the template's env into `local`.

    That is exactly the case where the workspace TRACKS `.claude/settings.json`
    — see `reconcile_claude_settings.WHY_LOCAL_FOR_TRACKED`. Ownership is asked
    of git, the same signal the reconciler branches on, so the two cannot drift
    apart. A workspace that is not a git repository, or a machine with no git,
    answers "not tracked" and takes the settings.json path, which is the
    historical behaviour.

    The probe is bounded (`GIT_QUERY_TIMEOUT_S`): it runs on the SessionStart
    path, and every external call needs an explicit timeout
    (`.github/copilot-instructions.md`, "Explicit failure semantics").

    A timeout answers `True`, deliberately, and NOT the "fall back to
    settings.json seeding" a first reading suggests. The two probes must agree:
    `reconcile_claude_settings._path_is_git_tracked` resolves the same unknown
    to `True` so it never overwrites repo-owned bytes, which means it has just
    written the current projection into the local file. Seeding from
    `settings.json` here would then overwrite that fresh projection with the
    tracked file's unrelated env — reintroducing, in the timeout case, exactly
    the staleness this function exists to prevent. Preferring the local file
    costs nothing when the workspace is genuinely untracked: the overlay owns
    that file too, so its env is still the right base.
    """
    if not local.is_file():
        return False
    try:
        proc = subprocess.run(
            [
                "git",
                "-C",
                str(workspace),
                "ls-files",
                "--error-unmatch",
                "--",
                ".claude/settings.json",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=GIT_QUERY_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return True
    except OSError:
        return False
    return proc.returncode == 0


def _patch_file(path: Path, overlay: dict[str, str]) -> bool:
    if not path.is_file() or not overlay:
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(data, dict):
        return False
    apply_overlay(data, overlay)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return True


def _write_workspace_local(workspace: Path, overlay: dict[str, str]) -> bool:
    """Write the merged env into the gitignored project-local settings file.

    The base is a COMPLETE env, not a fragment, so the file is correct whether
    Claude Code merges `env` key-by-key across scopes or takes it whole from the
    highest scope that sets it. Where that base comes from depends on who owns
    the workspace's settings.json:

    * **Repo-owned (git-tracked) settings.json.** `reconcile_claude_settings`
      does not write that file at all; it projects the template's managed keys,
      `env` included, into this same local file moments earlier
      (WHY_LOCAL_FOR_TRACKED). The local file's own env is then the current
      projection and the tracked file's is unrelated repository content —
      possibly from another revision entirely. So patch what is here, exactly
      as `_patch_file` does for `~/.claude/settings.json`. Re-seeding from the
      tracked file instead would overwrite a fresh projection with a stale one,
      which is the regression this whole path exists to end.
    * **Governance-injected (untracked) settings.json.** The reconciler wrote
      the projection THERE, so that file holds the authoritative env and the
      local file is this overlay's alone. Seed from it.

    Either way the base is refreshed from a file the reconciler rewrites every
    SessionStart, so a change to the template still reaches the session on the
    next start rather than being masked indefinitely.

    Any other keys already in settings.local.json (personal permissions, for
    example) are preserved.
    """
    if not overlay:
        return False
    claude_dir = workspace / ".claude"
    if not claude_dir.is_dir():
        return False

    local = claude_dir / "settings.local.json"
    base_env: dict[str, Any] = {}
    if _local_env_is_authoritative(workspace, local):
        base_env = _read_env(local)
    else:
        base_env = _read_env(claude_dir / "settings.json")

    data: dict[str, Any] = {}
    if local.is_file():
        try:
            existing = json.loads(local.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = None
        if isinstance(existing, dict):
            data = existing

    data["env"] = base_env
    apply_overlay(data, overlay)
    try:
        local.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    except OSError:
        return False
    return True


def overlay_hosted_settings(
    *,
    workspace: Path,
    home: Path | None = None,
    environ: dict[str, str] | None = None,
) -> list[str]:
    overlay = overlay_payload_from_environ(environ)
    written: list[str] = []
    if _write_workspace_local(workspace, overlay):
        written.append("workspace-local")
    home = home or Path.home()
    if _patch_file(home / ".claude" / "settings.json", overlay):
        written.append("user")
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    written = overlay_hosted_settings(workspace=args.workspace)
    if written:
        print("hosted-settings-env overlay: " + ",".join(written))
    else:
        print("hosted-settings-env overlay: none")
    return 0


if __name__ == "__main__":
    sys.exit(main())

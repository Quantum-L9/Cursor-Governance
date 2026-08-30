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
import sys
from pathlib import Path
from typing import Any

# Autonomy / concurrency only. Capability URLs and identity live in the
# account env and in mcp.template.json — they are not restated here.
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

    Base is the tracked settings.json env when it is readable, so the local file
    is a complete picture rather than a fragment. Any other keys already in
    settings.local.json (personal permissions, for example) are preserved.
    """
    if not overlay:
        return False
    claude_dir = workspace / ".claude"
    if not claude_dir.is_dir():
        return False

    base_env: dict[str, Any] = {}
    tracked = claude_dir / "settings.json"
    if tracked.is_file():
        try:
            tracked_data = json.loads(tracked.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            tracked_data = None
        if isinstance(tracked_data, dict) and isinstance(tracked_data.get("env"), dict):
            base_env = dict(tracked_data["env"])

    local = claude_dir / "settings.local.json"
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

#!/usr/bin/env python3
"""Copy hosted account env autonomy knobs into projected Claude settings.

Desktop and Mobile share settings.template.json (one adapter). Anthropic's
hosted Environment variables field is the Mobile/Web overlay: secrets and
capability URLs stay identical; autonomy ceilings may differ.

Claude Code reads `env` from settings.json. If that object wins over process
environment, a Mobile paste of L9_AUTONOMY_* would be ignored. This overlay
writes the allowlisted process-env values into workspace (and user-scope)
settings.json `env` after projection.

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
    "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH",
)

SURFACE_KEY = "L9_GOVERNANCE_SURFACE"
REQUIRED_SURFACE = "claude-code"


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


def overlay_hosted_settings(
    *,
    workspace: Path,
    home: Path | None = None,
    environ: dict[str, str] | None = None,
) -> list[str]:
    overlay = overlay_payload_from_environ(environ)
    written: list[str] = []
    if _patch_file(workspace / ".claude" / "settings.json", overlay):
        written.append("workspace")
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

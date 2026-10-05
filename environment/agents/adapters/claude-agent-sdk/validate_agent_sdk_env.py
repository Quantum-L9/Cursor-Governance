#!/usr/bin/env python3
"""Validate the Claude Agent SDK adapter against L9 invariants.

Checks:
  G_SETTING_SOURCES  setting_sources includes "project" (otherwise CLAUDE.md is dropped by the SDK)
  G_DENY_INVARIANT   every disallowed_tools entry names an invariant
  G_PROTECTED_SSOT   core SSOT files are in protected_files
  G_LAUNCHER_PATH    hook_launcher is a relative path under environment/agents/adapters/claude-code/hooks/
  G_SDK_IMPORT       (advisory) claude_agent_sdk importable
Exit 0 on pass, 1 on any G_* failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REQUIRED_SSOT = {"CANONICAL_LAW.md", "INVARIANTS.md", "ORG_INVARIANTS.yaml", "CODEOWNERS"}


def validate(cfg: dict) -> list[str]:
    errors: list[str] = []
    if "project" not in (cfg.get("setting_sources") or []):
        errors.append("G_SETTING_SOURCES: setting_sources must include \"project\"")
    for d in cfg.get("disallowed_tools") or []:
        if not isinstance(d, dict) or not d.get("rule") or not d.get("invariant"):
            errors.append(f"G_DENY_INVARIANT: {d!r} missing rule/invariant")
    missing = REQUIRED_SSOT - set(cfg.get("protected_files") or [])
    if missing:
        errors.append(f"G_PROTECTED_SSOT: missing {sorted(missing)}")
    launcher = str(cfg.get("hook_launcher", ""))
    if launcher.startswith("/") or not launcher.startswith("environment/agents/adapters/claude-code/hooks/"):
        errors.append(f"G_LAUNCHER_PATH: {launcher!r} must be relative under claude-code/hooks/")
    return errors


def main() -> int:
    cfg = yaml.safe_load((HERE / "config.yaml").read_text())
    errors = validate(cfg)
    for e in errors:
        print(e, file=sys.stderr)
    try:
        import claude_agent_sdk  # noqa: F401
        print("G_SDK_IMPORT: ok")
    except ImportError:
        print("G_SDK_IMPORT: advisory - claude-agent-sdk not installed (uv add claude-agent-sdk)")
    print("validate_agent_sdk_env:", "PASS" if not errors else f"FAIL ({len(errors)})")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

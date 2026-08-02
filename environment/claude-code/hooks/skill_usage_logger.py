#!/usr/bin/env python3
"""Record metadata-only Claude skill invocations without storing prompt text."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


def skill_from_payload(payload: dict[str, Any]) -> tuple[str, str]:
    event = str(payload.get("hook_event_name", ""))
    if event == "UserPromptExpansion":
        return str(payload.get("command_name", "")), "user"
    tool_name = str(payload.get("tool_name", ""))
    if event == "PreToolUse" and tool_name == "Skill":
        tool_input = payload.get("tool_input", {})
        if isinstance(tool_input, dict):
            for key in ("skill", "name", "command"):
                if tool_input.get(key):
                    return str(tool_input[key]), "model"
        return "unknown", "model"
    return "", "unknown"


def main() -> int:
    if os.environ.get("L9_SKILL_USAGE_LOGGING", "true").lower() != "true":
        return 0
    try:
        payload = json.load(sys.stdin)
        skill, source = skill_from_payload(payload)
        if not skill:
            return 0
        log_dir = Path.home() / ".claude" / "l9"
        log_dir.mkdir(parents=True, exist_ok=True)
        event = {
            "event": "skill_invocation",
            "session_id": payload.get("session_id", ""),
            "workspace": payload.get("cwd", ""),
            "skill_name": skill,
            "invocation_source": source,
        }
        with (log_dir / "skill-usage.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

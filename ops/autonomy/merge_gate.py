#!/usr/bin/env python3
"""Deny merge / force / admin-destructive git operations (Autonomy Surface Profile).

Claude Code PreToolUse adapter: environment/claude-code/hooks/merge_gate_wrap.py
calls this module. Brain lives under ops/ per CANONICAL_LAW §2.1.

Escape hatch (human authorization only):
  L9_MERGE_AUTHORIZED=<nonempty reason string>
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any

DENY_TOOL_NAMES = {
    "mcp__github__merge_pull_request",
    "MergePullRequest",
}

DENY_BASH_PATTERNS = (
    re.compile(r"\bgh\s+pr\s+merge\b", re.I),
    re.compile(r"\bgit\s+push\s+.*(--force|-f)\b", re.I),
    re.compile(r"\bgit\s+reset\s+--hard\b", re.I),
    re.compile(r"\bgit\s+clean\s+-fd\b", re.I),
)


def _deny(reason: str) -> int:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    return 0


def evaluate(tool_name: str, tool_input: dict[str, Any]) -> str | None:
    """Return deny reason or None if allowed to proceed (no decision)."""
    if os.environ.get("L9_MERGE_AUTHORIZED", "").strip():
        return None

    if tool_name in DENY_TOOL_NAMES:
        return (
            "Autonomy Surface Profile forbids merge_pull_request. "
            "Human merge only. Set L9_MERGE_AUTHORIZED=<reason> to override."
        )

    if tool_name in {"Bash", "bash"}:
        command = str(tool_input.get("command") or tool_input.get("cmd") or "")
        for pattern in DENY_BASH_PATTERNS:
            if pattern.search(command):
                return (
                    "Autonomy Surface Profile forbids merge/force/hard-reset via shell. "
                    "Human authorization required (L9_MERGE_AUTHORIZED)."
                )
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    tool_name = str(event.get("tool_name", ""))
    tool_input = event.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        tool_input = {}
    reason = evaluate(tool_name, tool_input)
    if reason:
        return _deny(reason)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

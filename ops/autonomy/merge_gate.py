#!/usr/bin/env python3
"""Deny merge / force / admin-destructive git operations (Autonomy Surface Profile).

Claude Code PreToolUse adapter: environment/agents/adapters/claude-code/hooks/merge_gate_wrap.py
calls this module. Brain lives under ops/ per CANONICAL_LAW §2.1.

Escape hatches:
  L9_MERGE_AUTHORIZED=<nonempty reason string>  # human only
  An L4 release receipt does NOT authorize merge (campaign_execution /
  post_push.merge_requires=never).
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from l4_local import workspace_from_event  # noqa: E402

DENY_TOOL_NAMES = {
    "mcp__github__merge_pull_request",
    "MergePullRequest",
}

MERGE_BASH = re.compile(r"\bgh\s+pr\s+merge\b", re.I)

DENY_BASH_PATTERNS = (
    MERGE_BASH,
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


def evaluate(
    tool_name: str,
    tool_input: dict[str, Any],
    *,
    root: Path | None = None,
) -> str | None:
    """Return deny reason or None if allowed to proceed (no decision)."""
    if os.environ.get("L9_MERGE_AUTHORIZED", "").strip():
        return None

    del root  # signature kept for hook callers

    if tool_name in DENY_TOOL_NAMES:
        return (
            "Autonomy Surface Profile forbids merge_pull_request. "
            "Do not remediate or merge. Human only: L9_MERGE_AUTHORIZED=<reason>."
        )

    if tool_name in {"Bash", "bash", "Shell", "shell"}:
        command = str(tool_input.get("command") or tool_input.get("cmd") or "")
        for pattern in DENY_BASH_PATTERNS:
            if pattern.search(command):
                return (
                    "Autonomy Surface Profile forbids merge/force/hard-reset via "
                    "shell. Agents must use PR_REMEDIATE=0 make pr and must not "
                    "merge. Human only: L9_MERGE_AUTHORIZED=<reason>."
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
    root = workspace_from_event(event)
    reason = evaluate(tool_name, tool_input, root=root)
    if reason:
        return _deny(reason)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

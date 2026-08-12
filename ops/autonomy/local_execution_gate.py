#!/usr/bin/env python3
"""Deny mid-execution git push / PR create until L4 release is authorized.

Claude Code PreToolUse adapter:
  environment/claude-code/hooks/local_execution_gate_wrap.py

Cursor beforeShellExecution adapter:
  ops/hooks/l4-local-execution-gate-shell.sh

Brain lives under ops/ per CANONICAL_LAW §2.1.

Escape hatches (human / ops only):
  L9_LOCAL_PUSH_AUTHORIZED=<reason>
  L9_L4_LOCAL_AUTONOMY=0
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from l4_local import release_allows_remote, workspace_root  # noqa: E402

REMOTE_BASH_PATTERNS = (
    re.compile(r"\bgit\s+push\b", re.I),
    re.compile(r"\bgh\s+pr\s+create\b", re.I),
    re.compile(r"\bgh\s+pr\s+edit\b", re.I),
    re.compile(r"\bmake\s+pr\b", re.I),
    re.compile(r"\bmake\s+push\b", re.I),
)

DENY_MCP_TOOLS = {
    "mcp__github__create_pull_request",
    "mcp__github__push_files",
    "create_pull_request",
    "push_files",
}


def _workspace_from_event(event: dict[str, Any]) -> Path:
    tool_input = event.get("tool_input") or {}
    if isinstance(tool_input, dict):
        for key in ("cwd", "working_directory", "workspace"):
            val = tool_input.get(key)
            if val:
                return Path(str(val)).expanduser().resolve()
    for key in ("cwd", "working_directory", "workspace"):
        val = event.get(key)
        if val:
            return Path(str(val)).expanduser().resolve()
    return workspace_root()


def command_is_remote_mutation(command: str) -> bool:
    return any(p.search(command) for p in REMOTE_BASH_PATTERNS)


def evaluate(tool_name: str, tool_input: dict[str, Any], *, root: Path) -> str | None:
    """Return deny reason or None if allowed."""
    if tool_name in DENY_MCP_TOOLS or tool_name.endswith("create_pull_request"):
        allowed, reason = release_allows_remote(root)
        return None if allowed else reason

    if tool_name in {"Bash", "bash", "Shell", "shell"}:
        command = str(tool_input.get("command") or tool_input.get("cmd") or "")
        if not command_is_remote_mutation(command):
            return None
        allowed, reason = release_allows_remote(root)
        return None if allowed else reason
    return None


def _deny_claude(reason: str) -> int:
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


def _emit_cursor(permission: str, message: str | None = None) -> int:
    payload: dict[str, Any] = {"permission": permission}
    if message:
        payload["user_message"] = message
    print(json.dumps(payload))
    return 0


def main_claude() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if not isinstance(event, dict):
        return 0
    tool_name = str(event.get("tool_name", ""))
    tool_input = event.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        tool_input = {}
    reason = evaluate(tool_name, tool_input, root=_workspace_from_event(event))
    if reason:
        return _deny_claude(reason)
    return 0


def main_cursor_shell() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return _emit_cursor("allow")
    if not isinstance(event, dict):
        return _emit_cursor("allow")
    command = str(event.get("command") or event.get("full_command") or "")
    if not command_is_remote_mutation(command):
        return _emit_cursor("allow")
    root = _workspace_from_event(event)
    allowed, reason = release_allows_remote(root)
    if allowed:
        return _emit_cursor("allow")
    return _emit_cursor("deny", reason)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "claude"
    if mode in {"cursor-shell", "shell"}:
        raise SystemExit(main_cursor_shell())
    raise SystemExit(main_claude())

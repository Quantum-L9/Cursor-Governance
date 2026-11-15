#!/usr/bin/env python3
"""PreToolUse gate: a registered /lcto swarm child never reaches across sessions.

The CTO operating protocol (governance/cto-mode/MODE.yaml ``invariants``) says swarm
agents never call cross-session messaging tools: they report by ``CTO-STATUS:`` /
``CTO-QUESTION:`` / ``CTO-BLOCKER:`` lines in their own transcript, which the CTO reads,
and a cross-session call from a child would need an operator approval the protocol rules
out. Until this gate only the launch prompt said so.

A session registered as a child (``ops/autonomy/session_role.py``) is denied every tool
that sends to, creates, schedules into or steers another session. Read-only session
tools (``get_session``, ``list_*``) stay allowed. Every other session is unaffected: the
role only narrows authority (L9-MONOTONIC-001).

Contract: stdin is the Claude PreToolUse payload; a deny prints the standard
``permissionDecision: deny`` document and exits 0; no decision exits 0 silently.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import session_role  # noqa: E402

REMOTE_PREFIX = "mcp__claude-code-remote__"
#: Tools that send to, create, schedule into or steer another session.
CROSS_SESSION_TOOLS = frozenset(
    {
        "send_message",
        "create_session",
        "send_later",
        "create_trigger",
        "update_trigger",
        "delete_trigger",
        "fire_trigger",
        "interrupt_session",
        "archive_session",
        "unarchive_session",
        "set_session_tags",
        "set_session_title",
    }
)
REASON = (
    "denied: this session is a registered /lcto swarm child "
    "(ops/autonomy/session_role.py). Swarm agents never call cross-session tools "
    "(governance/cto-mode/MODE.yaml invariants.swarm_never_pings_operator); report to "
    "the CTO with CTO-STATUS:, CTO-QUESTION: or CTO-BLOCKER: lines in your own reply."
)


def is_cross_session_tool(tool_name: str) -> bool:
    return tool_name.startswith(REMOTE_PREFIX) and (
        tool_name[len(REMOTE_PREFIX) :] in CROSS_SESSION_TOOLS
    )


def evaluate(tool_name: str, event: dict[str, Any] | None = None) -> str | None:
    if not is_cross_session_tool(tool_name):
        return None
    session_id = str((event or {}).get("session_id") or "") or None
    return REASON if session_role.is_child(session_id) else None


def main() -> int:
    raw = sys.stdin.read()
    try:
        event = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, ValueError):
        return 0
    if not isinstance(event, dict):
        return 0
    reason = evaluate(str(event.get("tool_name") or ""), event)
    if reason:
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


if __name__ == "__main__":
    raise SystemExit(main())

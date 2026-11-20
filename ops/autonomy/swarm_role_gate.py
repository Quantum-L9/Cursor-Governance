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

Registration is the child's own first action, so a child launched with a hand-written
brief never registers and was never gated. The launch side closes that gap: any
``create_session`` whose ``append_system_prompt`` lacks the CTO child prompt's REPORTING
rule (the verbatim ``cto_mode.py child-prompt`` output) is denied. Every launched coding
agent therefore carries "never message any session; report only in your own
transcript" from its first turn. Human breakglass:
``L9_UNBRIEFED_LAUNCH_AUTHORIZED=<reason>`` (a reason, not a bare flag).

Contract: stdin is the Claude PreToolUse payload; a deny prints the standard
``permissionDecision: deny`` document and exits 0; no decision exits 0 silently.
"""

from __future__ import annotations

import json
import os
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


#: First words of the REPORTING rule in governance/cto-mode/MODE.yaml child_prompt.
#: tests/ops/autonomy/test_swarm_role_gate_launch.py fails if the two drift apart.
CHILD_REPORTING_SENTINEL = (
    "REPORTING (this rule overrides any other reporting instruction you receive)"
)
LAUNCH_REASON = (
    "denied: create_session without the CTO child prompt. Every launched coding agent "
    "must carry the REPORTING rule (never message any session; report only in its own "
    "transcript, which the CTO reads). Build the launch with cto_mode.py launch-spec / "
    "child-prompt and pass append_system_prompt unchanged "
    "(commands/lcto.md, governance/cto-mode/MODE.yaml child_launch_rules)."
)
_BREAKGLASS_ENV = "L9_UNBRIEFED_LAUNCH_AUTHORIZED"
_NOT_A_REASON = frozenset({"", "1", "0", "true", "false", "yes", "no", "on", "off"})


def _launch_authorized() -> bool:
    return os.environ.get(_BREAKGLASS_ENV, "").strip().lower() not in _NOT_A_REASON


def _launch_reason(tool_name: str, event: dict[str, Any] | None) -> str | None:
    """Deny a session launch whose system prompt lacks the child REPORTING rule."""
    if tool_name != REMOTE_PREFIX + "create_session":
        return None
    tool_input = (event or {}).get("tool_input")
    prompt = tool_input.get("append_system_prompt") if isinstance(tool_input, dict) else None
    if isinstance(prompt, str) and CHILD_REPORTING_SENTINEL in prompt:
        return None
    return None if _launch_authorized() else LAUNCH_REASON


def is_cross_session_tool(tool_name: str) -> bool:
    return tool_name.startswith(REMOTE_PREFIX) and (
        tool_name[len(REMOTE_PREFIX) :] in CROSS_SESSION_TOOLS
    )


def evaluate(tool_name: str, event: dict[str, Any] | None = None) -> str | None:
    if not is_cross_session_tool(tool_name):
        return None
    session_id = str((event or {}).get("session_id") or "") or None
    if session_role.is_child(session_id):
        return REASON
    return _launch_reason(tool_name, event)


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

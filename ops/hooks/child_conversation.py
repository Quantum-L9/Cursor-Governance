#!/usr/bin/env python3
"""Derive the child conversation identity from a native Cursor subagent payload.

Both `lifecycle-subagent-start.sh` and `lifecycle-subagent-stop.sh` read this,
and they must agree: prefetch writes a receipt under the child id, and the
governed close has to find that same receipt. A start that keys on one id and a
stop that keys on another leaves the receipt unclosed and hands the parent's
conversation to a child's write gate.

The native `subagentStart` payload carries `subagent_id` / `tool_call_id` /
`parent_conversation_id`; `subagentStop` carries `subagent_id` / `status` /
`output` and no conversation id at all. `subagent_id` is therefore the only key
present on both sides, which is why it ranks above `tool_call_id` and why
`parent_conversation_id` is never a candidate — inheriting it is the failure
this ordering exists to prevent.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

# Ordered by preference. Every key here identifies the *child*; a parent id is
# not a fallback, because a child that inherits it writes as its parent.
CHILD_ID_KEYS: tuple[str, ...] = (
    "subagent_conversation_id",
    "conversation_id",
    "CURSOR_CONVERSATION_ID",
    "subagent_id",
    "tool_call_id",
    "session_id",
)

PROJECT_DIR_KEYS: tuple[str, ...] = (
    "cwd",
    "workspace_root",
    "project_dir",
    "CURSOR_PROJECT_DIR",
)


def child_conversation_id(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    for key in CHILD_ID_KEYS:
        value = str(payload.get(key) or "").strip()
        if value:
            return value
    return ""


def project_dir(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    for key in PROJECT_DIR_KEYS:
        value = str(payload.get(key) or "").strip()
        if value:
            return value
    roots = payload.get("workspace_roots") or payload.get("workspaceRoots") or []
    if isinstance(roots, list):
        for root in roots:
            value = str(root or "").strip()
            if value:
                return value
    return ""


def main() -> int:
    raw = os.environ.get("INPUT")
    if raw is None:
        raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    print(
        json.dumps(
            {
                "conversation_id": child_conversation_id(payload),
                "project_dir": project_dir(payload),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

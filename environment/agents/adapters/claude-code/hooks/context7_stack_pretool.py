#!/usr/bin/env python3
"""Deny first Edit/Write of stack files unless Context7 ran or a PASS receipt exists."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

STACK_NAME_RE = re.compile(
    r"(CAMPAIGN_SOURCE\.yaml|\.activate\.yaml|docker-compose|Dockerfile|"
    r"package\.json|requirements\.txt|pyproject\.toml)",
    re.I,
)
STACK_BODY_RE = re.compile(
    r"\b(api[_-]?key|mcp__|docker compose|pip install|npm install|language_name)\b",
    re.I,
)
CONTEXT7_TOOL_RE = re.compile(r"mcp__.*context7", re.I)


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


def _payload_paths(payload: dict[str, Any]) -> str:
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return ""
    parts = [
        str(tool_input.get("file_path") or ""),
        str(tool_input.get("path") or ""),
        str(tool_input.get("target_file") or ""),
        str(tool_input.get("new_string") or "")[:500],
        str(tool_input.get("contents") or "")[:500],
    ]
    return "\n".join(parts)


def _session_called_context7(session_id: str) -> bool:
    log = Path.home() / ".claude" / "l9" / "skill-usage.jsonl"
    if not session_id or not log.is_file():
        return False
    try:
        for line in log.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            if str(event.get("session_id") or "") != session_id:
                continue
            name = str(event.get("skill_name") or event.get("tool_name") or "")
            if CONTEXT7_TOOL_RE.search(name) or name == "l9-context7-docs":
                return True
    except (OSError, json.JSONDecodeError):
        return False
    return False


def _pass_receipt_exists() -> bool:
    primed = Path(os.environ.get("L9_ROOT", Path.home() / ".l9")) / "primed"
    if not primed.is_dir():
        return False
    for path in primed.glob("*/stack-proof.json"):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if str(raw.get("status") or "") == "pass":
            return True
    return False


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    tool = str(payload.get("tool_name") or "")
    if tool not in {"Edit", "Write", "NotebookEdit"}:
        return 0
    blob = _payload_paths(payload)
    if not (STACK_NAME_RE.search(blob) or STACK_BODY_RE.search(blob)):
        return 0
    session_id = str(payload.get("session_id") or "")
    if _session_called_context7(session_id) or _pass_receipt_exists():
        return 0
    return _deny(
        "Context7 stack proof required before editing API/MCP/install/Docker or "
        "campaign seed files. Call Context7 MCP (resolve-library-id → query-docs) "
        "or wait for $HOME/.l9/primed/<id>/stack-proof.json status=pass."
    )


if __name__ == "__main__":
    raise SystemExit(main())

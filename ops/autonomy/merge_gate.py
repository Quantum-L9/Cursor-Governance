#!/usr/bin/env python3
"""Deny merge / force / admin-destructive git operations (Autonomy Surface Profile).

Claude Code PreToolUse adapter: environment/claude-code/hooks/merge_gate_wrap.py
calls this module. Brain lives under ops/ per CANONICAL_LAW §2.1.

Escape hatches:
  L9_MERGE_AUTHORIZED=<nonempty reason string>
  L4 program/plan Build: valid ``.l9/autonomy/l4-release-receipt.json`` allows
  ordinary ``gh pr merge`` / merge MCP only (not force-push, hard-reset, admin).
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

from l4_local import release_allows_remote, workspace_from_event, workspace_root  # noqa: E402

DENY_TOOL_NAMES = {
    "mcp__github__merge_pull_request",
    "MergePullRequest",
}

MERGE_BASH = re.compile(r"\bgh\s+pr\s+merge\b", re.I)
ADMIN_MERGE = re.compile(r"--admin\b", re.I)

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


def _l4_program_merge_authorized(root: Path) -> bool:
    """Program/plan Build launch implies merge once L4 release is authorized."""
    try:
        allowed, _ = release_allows_remote(root)
        return allowed
    except (OSError, RuntimeError, ValueError):
        return False


def _merge_only_command(command: str) -> bool:
    return bool(MERGE_BASH.search(command)) and not ADMIN_MERGE.search(command)


def evaluate(
    tool_name: str,
    tool_input: dict[str, Any],
    *,
    root: Path | None = None,
) -> str | None:
    """Return deny reason or None if allowed to proceed (no decision)."""
    if os.environ.get("L9_MERGE_AUTHORIZED", "").strip():
        return None

    ws = root if root is not None else workspace_root()
    program_merge_ok = _l4_program_merge_authorized(ws)

    if tool_name in DENY_TOOL_NAMES:
        if program_merge_ok:
            return None
        return (
            "Autonomy Surface Profile forbids merge_pull_request outside an "
            "authorized L4 program/plan Build stack. Launching a program or "
            "Build authorizes merge for that stack (release receipt); else set "
            "L9_MERGE_AUTHORIZED=<reason>."
        )

    if tool_name in {"Bash", "bash", "Shell", "shell"}:
        command = str(tool_input.get("command") or tool_input.get("cmd") or "")
        for pattern in DENY_BASH_PATTERNS:
            if not pattern.search(command):
                continue
            if _merge_only_command(command) and program_merge_ok:
                return None
            return (
                "Autonomy Surface Profile forbids merge/force/hard-reset via shell. "
                "Program/plan Build + L4 release receipt authorizes ordinary "
                "gh pr merge only; force/admin/hard-reset need "
                "L9_MERGE_AUTHORIZED."
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

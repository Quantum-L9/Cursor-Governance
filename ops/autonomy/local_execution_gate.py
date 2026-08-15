#!/usr/bin/env python3
"""Deny mid-execution git push / PR create until L4 release is authorized.

Also enforces shared-worktree isolation (scoop/revert/switch/reset of foreign
dirty files) via ``worktree_isolation_gate``.

Claude Code PreToolUse adapter:
  environment/agents/adapters/claude-code/hooks/local_execution_gate_wrap.py

Cursor beforeShellExecution adapter:
  ops/hooks/l4-local-execution-gate-shell.sh

Brain lives under ops/ per CANONICAL_LAW §2.1.

Escape hatches (human / ops only):
  L9_LOCAL_PUSH_AUTHORIZED=<reason>
  L9_L4_LOCAL_AUTONOMY=0
  L9_GIT_REVERT_AUTHORIZED=<reason>
  L9_GIT_BROAD_ADD_AUTHORIZED=<reason>
  L9_GIT_SWITCH_AUTHORIZED=<reason>
  L9_GIT_RESET_AUTHORIZED=<reason>
  L9_WORKTREE_ISOLATION=0
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from command_parse import (  # noqa: E402
    extract_named_roots,
    segment_head,
    split_segments,
    strip_heredoc_bodies,
    wrapper_subcommands,
)
from l4_local import release_allows_remote, workspace_from_event  # noqa: E402
from worktree_isolation_gate import command_violates_worktree_isolation  # noqa: E402

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


def command_is_remote_mutation(command: str) -> bool:
    """Detect remote mutation in command text only (heredoc data is excluded).

    Matching is command-position scoped: a segment only counts when its head
    is the tool the pattern names (git/gh/make). Quoted spans are preserved,
    so ``bash -c 'git push …'`` still matches via the wrapper descent.
    ``echo 'git push'`` and other data segments never match. Residual accepted:
    ``ssh host 'git push'`` / ``sudo git push`` heads are not pattern targets.
    """
    segments: list[str] = []
    for segment in split_segments(strip_heredoc_bodies(command)):
        segments.append(segment)
        segments.extend(wrapper_subcommands(segment))
    for segment in segments:
        head = segment_head(segment)
        if head not in {"git", "gh", "make"}:
            continue
        if any(pattern.search(segment) for pattern in REMOTE_BASH_PATTERNS):
            return True
    return False


def _repo_root_from_path(path: str) -> Path | None:
    """Resolve a named path to its git repo root (symlinks resolved).

    Fails closed: only an existing directory inside a git work tree qualifies.
    """
    try:
        candidate = Path(path).resolve()
    except OSError:
        return None
    if not candidate.is_dir():
        return None
    try:
        proc = subprocess.run(
            ["git", "-C", str(candidate), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    top = Path(proc.stdout.strip())
    return top if top.is_dir() else None


def evaluate(tool_name: str, tool_input: dict[str, Any], *, root: Path) -> str | None:
    """Return deny reason or None if allowed.

    Workspace resolution: when the command explicitly names repo paths
    (``git -C <path>`` / ``cd <path>``), EVERY named root must hold a valid L4
    release receipt — otherwise the session-root check applies unchanged.
    Dynamic path tokens never widen the gate (extract_named_roots ignores
    them), so unknown targets stay fail-closed.
    """
    if tool_name in DENY_MCP_TOOLS or tool_name.endswith("create_pull_request"):
        allowed, reason = release_allows_remote(root)
        return None if allowed else reason

    if tool_name in {"Bash", "bash", "Shell", "shell"}:
        command = str(tool_input.get("command") or tool_input.get("cmd") or "")
        iso = command_violates_worktree_isolation(command, root=root)
        if iso:
            return iso
        if not command_is_remote_mutation(command):
            return None
        named_roots = extract_named_roots(command)
        if named_roots:
            resolved = [_repo_root_from_path(path) for path in named_roots]
            if any(item is None for item in resolved):
                return (
                    "L4 named root could not be resolved to a git repository; "
                    "fail-closed on unresolved remote-mutation targets"
                )
            if all(release_allows_remote(item)[0] for item in resolved):  # type: ignore[union-attr]
                return None
            denied = next(
                item for item in resolved if item is not None and not release_allows_remote(item)[0]
            )
            _, reason = release_allows_remote(denied)
            return reason
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
    reason = evaluate(tool_name, tool_input, root=workspace_from_event(event))
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
    root = workspace_from_event(event)
    iso = command_violates_worktree_isolation(command, root=root)
    if iso:
        return _emit_cursor("deny", iso)
    if not command_is_remote_mutation(command):
        return _emit_cursor("allow")
    allowed, reason = release_allows_remote(root)
    if allowed:
        return _emit_cursor("allow")
    return _emit_cursor("deny", reason)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "claude"
    if mode in {"cursor-shell", "shell"}:
        raise SystemExit(main_cursor_shell())
    raise SystemExit(main_claude())

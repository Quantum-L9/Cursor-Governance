#!/usr/bin/env python3
"""Deny merge / force / admin-destructive git operations (Autonomy Surface Profile).

Claude Code PreToolUse adapter: environment/agents/adapters/claude-code/hooks/merge_gate_wrap.py
calls this module. Brain lives under ops/ per CANONICAL_LAW §2.1.

Ordinary `gh pr merge` is allowed only when:

  L9_MERGE_AUTHORIZED=<nonempty reason string>          # session env
  ~/.l9/autonomy/merge-authorization.json               # receipt file
    {"authorizations": [{"repo": "org/repo", "pr": "*" | 53,
                          "source": "l9-pr-remediation",
                          "expires_at": <unix-seconds>, "reason": "..."}]}
    Overridable for tests via L9_MERGE_AUTHORIZATION_FILE. An entry matches
    when repo matches and pr is "*" (all open PRs in that repo) or the
    exact PR number, and expires_at is in the future.

Invoking /l9-pr-remediation writes that receipt via
ops/autonomy/authorize_merge.py. Campaigns and make pr do not merge.
An L4 release receipt does NOT authorize merge.

Never waived: force-push, hard-reset, git clean -fd, admin-merge.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
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
ADMIN_MERGE_BASH = re.compile(r"\bgh\s+pr\s+merge\b.*--admin\b", re.I)
FORCE_PUSH_BASH = re.compile(r"\bgit\s+push\s+.*(--force|-f)\b", re.I)
HARD_RESET_BASH = re.compile(r"\bgit\s+reset\s+--hard\b", re.I)
CLEAN_FD_BASH = re.compile(r"\bgit\s+clean\s+-fd\b", re.I)
REPO_SCOPE = {"*", "all", "ALL"}

NEVER_WAIVE_REASON = (
    "Autonomy Surface Profile never waives force-push, hard-reset, "
    "destructive clean, or admin-merge."
)

MERGE_DENY_REASON = (
    "Autonomy Surface Profile forbids merge until /l9-pr-remediation is "
    "invoked (or L9_MERGE_AUTHORIZED=<reason>). Campaigns and make pr end "
    "at green + merge-ready. Write the receipt with "
    "python3 ops/autonomy/authorize_merge.py --repo <owner/name> --all-open "
    "--reason 'l9-pr-remediation invoked', then gh pr merge --squash "
    "(no --admin) for each green mergeable PR, oldest first."
)


def _auth_file_path() -> Path:
    override = os.environ.get("L9_MERGE_AUTHORIZATION_FILE", "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".l9" / "autonomy" / "merge-authorization.json"


def _target_from_input(tool_name: str, tool_input: dict[str, Any]) -> tuple[str, str]:
    """Return (repo, pr) parsed conservatively from the tool input; ('', '') when unknown."""
    repo = str(tool_input.get("repo") or tool_input.get("repository") or "")
    pr = str(
        tool_input.get("pull_number") or tool_input.get("pr") or tool_input.get("number") or ""
    )
    if not (repo and pr) and tool_name in {"Bash", "bash", "Shell", "shell"}:
        command = str(tool_input.get("command") or tool_input.get("cmd") or "")
        match = re.search(r"\bgh\s+pr\s+merge\s+(\d+)", command, re.I)
        if match:
            pr = match.group(1)
            repo_match = re.search(r"--repo\s+([\w.-]+/[\w.-]+)", command, re.I)
            repo = repo_match.group(1) if repo_match else ""
    return repo, pr


def _file_authorizes(repo: str, pr: str) -> bool:
    """True when a fresh matching repo-scoped or PR-scoped authorization exists."""
    path = _auth_file_path()
    if not path.is_file():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        entries = payload.get("authorizations", []) if isinstance(payload, dict) else []
    except (json.JSONDecodeError, OSError):
        return False
    now = time.time()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        expires = entry.get("expires_at") or 0
        if isinstance(expires, (int, float)) and 0 < expires < now:
            continue
        entry_repo = str(entry.get("repo") or "")
        entry_pr = str(entry.get("pr") or entry.get("number") or "")
        if not entry_repo:
            continue
        if repo and entry_repo != repo:
            continue
        if not repo:
            continue
        if entry_pr in REPO_SCOPE:
            return True
        if pr and entry_pr == pr:
            return True
    return False


def _merge_authorized(tool_name: str, tool_input: dict[str, Any]) -> bool:
    if os.environ.get("L9_MERGE_AUTHORIZED", "").strip():
        return True
    repo, pr = _target_from_input(tool_name, tool_input)
    return _file_authorizes(repo, pr)


def _never_waive_command(command: str) -> bool:
    return bool(
        FORCE_PUSH_BASH.search(command)
        or HARD_RESET_BASH.search(command)
        or CLEAN_FD_BASH.search(command)
        or ADMIN_MERGE_BASH.search(command)
    )


def _never_waive_tool(tool_name: str, tool_input: dict[str, Any]) -> bool:
    if tool_name in DENY_TOOL_NAMES and bool(tool_input.get("admin") or tool_input.get("admin_override")):
        return True
    return False


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
    del root  # signature kept for hook callers

    if _never_waive_tool(tool_name, tool_input):
        return NEVER_WAIVE_REASON

    if tool_name in {"Bash", "bash", "Shell", "shell"}:
        command = str(tool_input.get("command") or tool_input.get("cmd") or "")
        if _never_waive_command(command):
            return NEVER_WAIVE_REASON
        if MERGE_BASH.search(command):
            if _merge_authorized(tool_name, tool_input):
                return None
            return MERGE_DENY_REASON
        return None

    if tool_name in DENY_TOOL_NAMES:
        if _merge_authorized(tool_name, tool_input):
            return None
        return MERGE_DENY_REASON
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

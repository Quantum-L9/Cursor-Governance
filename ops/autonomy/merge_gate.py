#!/usr/bin/env python3
"""Deny merge / force / admin-destructive git operations (Autonomy Surface Profile).

Claude Code PreToolUse adapter: environment/agents/adapters/claude-code/hooks/merge_gate_wrap.py
calls this module. Brain lives under ops/ per CANONICAL_LAW §2.1.

Escape hatches (human only):
  L9_MERGE_AUTHORIZED=<nonempty reason string>          # session env
  ~/.l9/autonomy/merge-authorization.json               # one-shot file channel
    {"authorizations": [{"repo": "org/repo", "pr": 53,
                          "expires_at": <unix-seconds>, "reason": "..."}]}
    Overridable for tests via L9_MERGE_AUTHORIZATION_FILE. An entry matches
    when repo and pr match the target and expires_at is in the future; a
    blank entry or expired entry authorizes nothing (fail closed).
  An L4 release receipt does NOT authorize merge (campaign_execution /
  post_push.merge_requires=never).
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

DENY_BASH_PATTERNS = (
    MERGE_BASH,
    re.compile(r"\bgit\s+push\s+.*(--force|-f)\b", re.I),
    re.compile(r"\bgit\s+reset\s+--hard\b", re.I),
    re.compile(r"\bgit\s+clean\s+-fd\b", re.I),
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
    """True when a fresh, matching one-shot authorization entry exists."""
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
        if not entry_repo and not entry_pr:
            continue
        if entry_repo and repo and entry_repo != repo:
            continue
        if entry_pr and pr and entry_pr != pr:
            continue
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
    if os.environ.get("L9_MERGE_AUTHORIZED", "").strip():
        return None
    repo, pr = _target_from_input(tool_name, tool_input)
    if _file_authorizes(repo, pr):
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
                    "merge. Human only: L9_MERGE_AUTHORIZED=<reason>, or a "
                    "one-shot entry in ~/.l9/autonomy/merge-authorization.json "
                    "matching this repo and PR with a future expires_at."
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

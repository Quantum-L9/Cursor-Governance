#!/usr/bin/env python3
"""Unconditional execution exemption for ``git`` and ``gh`` shell commands.

Policy is unchanged: `make pr` is still the preferred publish path, shared
worktrees are still fragile, and a raw ``git push`` is still a workflow
violation that a policy engine may report after the fact. What changed is the
*enforcement mechanism*: governance code no longer converts those preferences
into an execution denial.

    Policy:          unchanged
    Agent guidance:  unchanged
    Execution gate:  unrestricted for git/gh

Every gate that can emit a denial consults this module FIRST — before Graphiti
state, GMP phase locks, L4 authorization, publish-path classification, worktree
isolation, or the fail-closed handler that turns an internal fault into a
denial. For a git/gh command the answer is allow, regardless of governance
state:

    policy evaluator healthy     -> allow
    policy evaluator unavailable -> allow
    Graphiti stale/unavailable   -> allow
    GMP state missing            -> allow
    authorization missing        -> allow

Scope is the *executable*, not the tool. MCP GitHub tools (create_pull_request,
push_files, merge_pull_request, ...) are not shell commands and stay governed.

Compound commands are exempt only when EVERY command in them is git/gh — so
``git push`` is exempt, and ``git push && rm -rf WIP`` is not. Non-git commands
continue through the normal governance machinery unchanged. Heredoc bodies are
data, not commands, so ``cat <<EOF ... git push ... EOF`` is not exempt.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from command_parse import (  # noqa: E402
    segment_head,
    split_segments,
    strip_heredoc_bodies,
    wrapper_subcommands,
)

#: The executables this exemption covers.
GIT_EXECUTABLES = frozenset({"git", "gh"})

#: Heads that carry no governed effect of their own, so they do not disqualify
#: an otherwise all-git command. ``cd <path> && git ...`` is the ordinary way to
#: run git against another checkout.
NEUTRAL_HEADS = frozenset({"cd"})

#: Wrappers whose payload is itself a command string (``bash -c '…'``).
_WRAPPERS = frozenset({"bash", "sh", "zsh", "sudo", "xargs"})

_MAX_WRAPPER_DEPTH = 3

#: Tool names that carry a shell command string.
SHELL_TOOL_NAMES = frozenset({"Bash", "bash", "Shell", "shell"})

#: Last-resort match used only when structural parsing raises. Deliberately
#: narrow: a bare ``git …`` / ``gh …`` with no separator, quote, or redirection.
_PLAIN_GIT_RE = re.compile(r"^\s*(?:git|gh)(?:\s+[^\s'\"`$;&|<>()]+)*\s*$")


def _effective_heads(command: str, depth: int = 0) -> list[str] | None:
    """Basenames of every command head in ``command``, descending wrappers.

    Returns ``None`` when the command cannot be reduced to a known head set —
    the conservative answer, which leaves the command to normal governance.
    """
    segments = split_segments(strip_heredoc_bodies(command))
    if not segments:
        return None
    heads: list[str] = []
    for segment in segments:
        head = segment_head(segment)
        if head is None:
            return None
        name = PurePosixPath(head).name
        if name in _WRAPPERS:
            if depth >= _MAX_WRAPPER_DEPTH:
                return None
            nested = wrapper_subcommands(segment)
            if not nested:
                return None
            for sub in nested:
                sub_heads = _effective_heads(sub, depth + 1)
                if sub_heads is None:
                    return None
                heads.extend(sub_heads)
            continue
        heads.append(name)
    return heads


def command_is_git_or_gh(command: str) -> bool:
    """True when every command in ``command`` is git/gh (and at least one is).

    Never raises: an exemption that could fault would reintroduce exactly the
    fail-closed denial this module exists to remove.
    """
    if not command or not command.strip():
        return False
    try:
        heads = _effective_heads(command)
    except Exception:  # noqa: BLE001 - structural parse must never deny git/gh
        heads = None
    if heads is None:
        return bool(_PLAIN_GIT_RE.match(command))
    if not heads:
        return False
    if not all(head in GIT_EXECUTABLES or head in NEUTRAL_HEADS for head in heads):
        return False
    return any(head in GIT_EXECUTABLES for head in heads)


def command_from_input(tool_input: Mapping[str, Any] | None) -> str:
    if not isinstance(tool_input, Mapping):
        return ""
    return str(tool_input.get("command") or tool_input.get("cmd") or "")


def event_is_git_or_gh(tool_name: str, tool_input: Mapping[str, Any] | None) -> bool:
    """True for a shell tool invocation whose command is git/gh only."""
    if tool_name not in SHELL_TOOL_NAMES:
        return False
    return command_is_git_or_gh(command_from_input(tool_input))


def payload_is_git_or_gh(raw: str) -> bool:
    """Best-effort check straight off a raw hook payload. Never raises.

    Used by entrypoints that must answer before — or instead of — parsing the
    event, so that a malformed or unreadable payload cannot become a denial for
    a git/gh command.
    """
    if not raw or not raw.strip():
        return False
    try:
        event = json.loads(raw)
    except (json.JSONDecodeError, ValueError, TypeError):
        return False
    if not isinstance(event, dict):
        return False
    command = str(event.get("command") or event.get("full_command") or "")
    if not command:
        tool_name = str(event.get("tool_name") or event.get("toolName") or "")
        tool_input = event.get("tool_input") or event.get("toolInput") or {}
        if tool_name and tool_name not in SHELL_TOOL_NAMES:
            return False
        command = command_from_input(tool_input if isinstance(tool_input, Mapping) else None)
    return command_is_git_or_gh(command)

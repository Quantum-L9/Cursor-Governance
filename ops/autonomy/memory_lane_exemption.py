#!/usr/bin/env python3
"""Agent-lane exemption for memory invocations (ADR-0033 B8, INV-03b).

Agents are first-class real-time memory writers. A shell invocation of the
memory package's public CLI (``l9-memory …``), of the operator form
(``python -m ops.memory.cli …``), or of the SessionStart prefetch that repairs
a missed hydrate is a *memory* action, not a *repository* write, so no
repository-write precondition may deny it. In particular the Claude
``memory_gate`` — a hydration precondition on ``Edit|Write|Bash`` — must not
refuse the very command that writes or repairs memory: that was the
interposition on the agent lane this module removes.

    Policy:            unchanged — repository edits still gate on hydration
    Memory invocation: exempt from the hydration gate, unconditionally
    Destructive risk:  unchanged — ``git_guardrails`` still runs first

Same shape as ``git_execution_exemption``: scope is the *executable*, compound
commands are exempt only when EVERY segment is a memory invocation (or a
neutral ``cd``), heredoc bodies are data, and a structural-parse fault falls
back to a deliberately narrow plain match rather than to a denial.

MCP memory tools (``mcp__l9-graphite-memory__*``) are not shell commands and
never appear in any hook matcher or deny list in the first place;
``tests/ops/memory/test_no_agent_lane_interposition.py`` pins that.
"""

from __future__ import annotations

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
    segment_words,
    split_segments,
    strip_heredoc_bodies,
    wrapper_subcommands,
)

#: The memory package's public console script.
MEMORY_EXECUTABLES = frozenset({"l9-memory"})

#: Interpreters that may carry ``-m ops.memory.cli`` or the prefetch script.
_PYTHON_HEADS = re.compile(r"^python(?:3(?:\.\d+)?)?$")

#: The operator / deterministic-adapter form of the same control plane.
OPERATOR_MODULE = "ops.memory.cli"

#: The Claude SessionStart hydrate, run by hand to repair a missed prefetch.
#: The hydration gate's own remediation text names it; denying it while
#: unhydrated would make the repair impossible.
PREFETCH_SCRIPT = "memory_prefetch.py"

NEUTRAL_HEADS = frozenset({"cd"})

_WRAPPERS = frozenset({"bash", "sh", "zsh", "sudo", "xargs"})
_MAX_WRAPPER_DEPTH = 3

SHELL_TOOL_NAMES = frozenset({"Bash", "bash", "Shell", "shell"})

#: Last resort when structural parsing raises. Covers the three allowed
#: entrypoints and refuses shell metacharacters so a parse fault cannot
#: exempt a redirect or substitution.
_SAFE_TAIL = r"(?:\s+[^\s'\"`$;&|<>()]+)*\s*$"
_PLAIN_MEMORY_RE = re.compile(
    r"^\s*(?:"
    r"(?:\S*/)?l9-memory"
    r"|(?:(?:\S*/)?python(?:3(?:\.\d+)?)?)\s+-m\s+ops\.memory\.cli"
    r"|(?:\S*/)?memory_prefetch\.py"
    r")" + _SAFE_TAIL
)
_SIDE_EFFECT_RE = re.compile(r"[<>]|\$\(|`")


def _segment_is_memory(segment: str) -> bool | None:
    """True / False for one simple segment; ``None`` when it cannot be judged."""

    head = segment_head(segment)
    if head is None:
        return None
    name = PurePosixPath(head).name
    if name in NEUTRAL_HEADS:
        return False  # neutral: neither qualifies nor disqualifies
    if name in MEMORY_EXECUTABLES:
        return None if _SIDE_EFFECT_RE.search(segment) else True
    if _PYTHON_HEADS.match(name):
        words = segment_words(segment)
        try:
            start = words.index(head)
        except ValueError:
            return None
        rest = words[start + 1 :]
        if len(rest) >= 2 and rest[0] == "-m" and rest[1] == OPERATOR_MODULE:
            return None if _SIDE_EFFECT_RE.search(segment) else True
        if rest and PurePosixPath(rest[0]).name == PREFETCH_SCRIPT:
            return None if _SIDE_EFFECT_RE.search(segment) else True
        return None
    if name == PREFETCH_SCRIPT:
        return None if _SIDE_EFFECT_RE.search(segment) else True
    return None


def _classify(command: str, depth: int = 0) -> tuple[int, int] | None:
    """(memory_segments, disqualifying_segments) or ``None`` when unparseable."""

    segments = split_segments(strip_heredoc_bodies(command))
    if not segments:
        return None
    memory = 0
    other = 0
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
                inner = _classify(sub, depth + 1)
                if inner is None:
                    return None
                memory += inner[0]
                other += inner[1]
            continue
        verdict = _segment_is_memory(segment)
        if verdict is None:
            other += 1
        elif verdict:
            memory += 1
    return memory, other


def command_is_memory_lane(command: str) -> bool:
    """True when every command in ``command`` is a memory invocation (≥ 1).

    Never raises: an exemption that could fault would reintroduce the denial
    it exists to remove.
    """

    if not command or not command.strip():
        return False
    # nosemgrep: l9.baseline.python.broad-except
    try:
        verdict = _classify(command)
    except Exception:  # noqa: BLE001 - structural parse must never deny memory
        verdict = None
    if verdict is None:
        return bool(_PLAIN_MEMORY_RE.match(command))
    memory, other = verdict
    return memory > 0 and other == 0


def command_from_input(tool_input: Mapping[str, Any] | None) -> str:
    if not isinstance(tool_input, Mapping):
        return ""
    return str(tool_input.get("command") or tool_input.get("cmd") or "")


def event_is_memory_lane(tool_name: str, tool_input: Mapping[str, Any] | None) -> bool:
    """True for a shell tool invocation whose command is memory-only."""

    if tool_name not in SHELL_TOOL_NAMES:
        return False
    return command_is_memory_lane(command_from_input(tool_input))


__all__ = [
    "MEMORY_EXECUTABLES",
    "OPERATOR_MODULE",
    "PREFETCH_SCRIPT",
    "SHELL_TOOL_NAMES",
    "command_is_memory_lane",
    "event_is_memory_lane",
]

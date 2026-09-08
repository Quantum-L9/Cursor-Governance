#!/usr/bin/env python3
"""Memory write gate logic for Cursor hooks — canonical evidence (stage C8).

The gate reads the local, non-authoritative session state the canonical
hydration wrote (``ops/memory/session_state.py``,
``~/.cursor/l9-memory-session-state/<session>.json``). It never reads the
retired provider state file, never calls memory, and never consults a lock.

``git``/``gh`` shell commands never reach the state checks below: memory
prefetch freshness is an input to *policy*, not to whether git may execute. See
``ops/autonomy/git_execution_exemption``.

The gate checks hydration only. A memory phase-lock is never a repository
mutex (rules/96-multi-agent-main-bound-execution.mdc, E7). A subagent inherits
its parent's evidence read-only and never writes state of its own (authority
narrowing, stage C8).
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_AUTONOMY = _REPO_ROOT / "ops" / "autonomy"
for _extra in (_REPO_ROOT, _AUTONOMY):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

from git_execution_exemption import payload_is_git_or_gh  # noqa: E402

from ops.memory.session_state import (  # noqa: E402
    hydration_is_fresh,
    memory_satisfied,
    read_session_state,
)

ALLOW = {"permission": "allow"}

ENV_GATES = "L9_MEMORY_WRITE_GATES"
#: Legacy switch name, honored until the provider env plane is removed (C9).
LEGACY_ENV_GATES = "GRAPHITI_WRITE_GATES"


def load_state(conv_id: str) -> dict:
    """Canonical session state for this conversation, or ``{}``."""
    return read_session_state(conv_id or "default") or {}


def gates_enabled() -> bool:
    for name in (ENV_GATES, LEGACY_ENV_GATES):
        if name in os.environ:
            return os.environ.get(name, "0") == "1"
    # Machine-local env file (legacy location; removed with the provider env
    # plane at stage C9). Read for the switch only — never for a credential.
    env_path = Path.home() / ".cursor" / "graphiti.env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            for name in (ENV_GATES, LEGACY_ENV_GATES):
                if stripped.startswith(f"{name}="):
                    return stripped.split("=", 1)[1].strip() == "1"
    return False


def prefetch_fresh(state: dict, ttl_minutes: int = 30) -> bool:
    return hydration_is_fresh(state, ttl_minutes=ttl_minutes)


def memory_ok(state: dict, task_sig: str | None = None) -> bool:
    return memory_satisfied(state, task_signature=task_sig)


READ_ONLY_TOOLS = frozenset(
    {
        "Read",
        "Grep",
        "Glob",
        "SemanticSearch",
        "ListDir",
        "TaskExplore",
        "Shell",
        "mcp",
    }
)

DENY_HINT = (
    "Run a canonical memory search/hydrate (l9-graphite-memory) or start a fresh "
    "session so SessionStart hydrates. This is a hydration gate, not a lock."
)


def pre_tool_use(payload: str) -> dict:
    if payload_is_git_or_gh(payload):
        return dict(ALLOW)
    if not gates_enabled():
        return {"permission": "allow"}
    data = json.loads(payload) if payload.strip() else {}
    tool = data.get("tool_name") or data.get("toolName") or ""
    if tool in READ_ONLY_TOOLS or tool.startswith("mcp_"):
        return {"permission": "allow"}
    conv = data.get("conversation_id") or data.get("conversationId") or "default"
    state = load_state(str(conv))
    # A GMP prompt used to require gmp:phase_lock here. That made a memory
    # marker into repository-write permission, which the L9 Multi-Agent
    # Main-Bound Execution Contract forbids (E7): GMP freezes the authorized
    # edit *scope* (the scope contract), it does not decide which agent owns
    # the repository. Hydration is the only remaining precondition.
    if memory_ok(state):
        return {"permission": "allow"}
    return {
        "permission": "deny",
        "user_message": f"Memory gate: Write blocked until memory hydration is fresh. {DENY_HINT}",
    }


def shell_gate(payload: str) -> dict:
    if payload_is_git_or_gh(payload):
        return dict(ALLOW)
    if not gates_enabled():
        return {"permission": "allow"}
    data = json.loads(payload) if payload.strip() else {}
    command = data.get("command") or data.get("full_command") or ""
    if not re.search(r"git\s+commit|make\s+push", command):
        return {"permission": "allow"}
    conv = data.get("conversation_id") or "default"
    state = load_state(str(conv))
    if memory_ok(state):
        return {"permission": "allow"}
    return {
        "permission": "deny",
        "user_message": (
            f"Memory gate: commit/push blocked until memory hydration is fresh. {DENY_HINT}"
        ),
    }


def subagent_gate(payload: str) -> dict:
    """A subagent inherits the PARENT session's evidence, read-only.

    The parent's state is consulted; nothing is written for the subagent, so
    a subagent can never manufacture its own hydration or widen the parent's
    authority (stage C8 narrowing).
    """
    if not gates_enabled():
        return {"permission": "allow"}
    data = json.loads(payload) if payload.strip() else {}
    conv = data.get("parent_conversation_id") or data.get("conversation_id") or "default"
    state = load_state(str(conv))
    if memory_ok(state):
        return {"permission": "allow"}
    return {
        "permission": "deny",
        "user_message": (
            "Memory gate: subagent blocked — parent session memory hydration not fresh."
        ),
    }


def main() -> int:
    mode = sys.argv[1]
    payload = sys.stdin.read()
    # Ahead of dispatch, so neither a state check nor a handler fault (which the
    # runner converts into a denial when gates are enabled) can block git/gh.
    if payload_is_git_or_gh(payload):
        print(json.dumps(ALLOW))
        return 0
    handlers = {
        "pre_tool_use": pre_tool_use,
        "shell": shell_gate,
        "subagent": subagent_gate,
    }
    result = handlers[mode](payload)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

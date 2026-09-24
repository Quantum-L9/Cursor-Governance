"""Which agent is writing memory — one answer per surface, never "one Claude Code".

Every memory names the agent that wrote it (ADR-0031), and the operator must be
able to tell a Cursor fact from a Claude Code Desktop fact from a Claude Code
Mobile fact. This module is the single resolver both memory lanes use: the
hook lane (SessionStart prefetch, Stop close, handoffs) stamps it as the writer,
and ``ops/memory/run_memory_mcp.sh`` mints the signed MCP door for it.

    cursor               Cursor (CURSOR_AGENT)
    claude-code-desktop  Claude Code on the operator's machine — desktop app,
                         CLI or IDE (Claude Code markers, CLAUDE_CODE_REMOTE unset)
    claude-code-mobile   Claude Code cloud session from the mobile app
                         (CLAUDE_CODE_REMOTE=true, CLAUDE_CODE_ENTRYPOINT=remote_mobile)
    claude-code-web      any other Claude Code cloud session (web, API-started),
                         so a non-mobile cloud session is never labelled mobile

``L9_MEMORY_AGENT_ID`` set to a concrete id (``cursor``, ``manus``,
``claude-code-mobile``, …) is authoritative. The legacy value ``claude-code``
— which ``settings.template.json`` projects into every Claude surface, and
which Cursor can inherit by loading ``.claude/settings.json`` — is only the
family marker and is refined from the runtime markers above.

Pure: reads the mapping it is given, no I/O. ``python -m ops.memory.agent_identity``
prints the id for the current environment (empty and exit 1 when unknown).
"""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from typing import Final

CLAUDE_FAMILY: Final = "claude-code"
CURSOR: Final = "cursor"
CLAUDE_DESKTOP: Final = "claude-code-desktop"
CLAUDE_MOBILE: Final = "claude-code-mobile"
CLAUDE_WEB: Final = "claude-code-web"
CLAUDE_IDENTITIES: Final = frozenset({CLAUDE_DESKTOP, CLAUDE_MOBILE, CLAUDE_WEB})
#: Identities that share one hosted environment (and so one provisioned secret).
HOSTED_CLAUDE: Final = frozenset({CLAUDE_MOBILE, CLAUDE_WEB})
MOBILE_ENTRYPOINTS: Final = frozenset({"remote_mobile"})


def _flag(env: Mapping[str, str], name: str) -> str:
    return (env.get(name) or "").strip()


def _is_claude(env: Mapping[str, str]) -> bool:
    return bool(
        _flag(env, "CLAUDECODE")
        or _flag(env, "CLAUDE_CODE_ENTRYPOINT")
        or _flag(env, "CLAUDE_CODE_SESSION_ID")
    )


def claude_identity(env: Mapping[str, str]) -> str:
    """The Claude Code surface identity from runtime markers."""
    if _flag(env, "CLAUDE_CODE_REMOTE").lower() == "true":
        if _flag(env, "CLAUDE_CODE_ENTRYPOINT").lower() in MOBILE_ENTRYPOINTS:
            return CLAUDE_MOBILE
        return CLAUDE_WEB
    return CLAUDE_DESKTOP


def resolve_agent_id(env: Mapping[str, str] | None = None) -> str:
    """The writing agent's identity, or "" when nothing identifies one."""
    source = os.environ if env is None else env
    explicit = _flag(source, "L9_MEMORY_AGENT_ID")
    if explicit and explicit != CLAUDE_FAMILY:
        return explicit
    # Cursor wins over a Claude family marker it inherited from .claude/settings.json.
    if _flag(source, "CURSOR_AGENT"):
        return CURSOR
    if explicit == CLAUDE_FAMILY or _is_claude(source):
        return claude_identity(source)
    return ""


def user_id_for(agent_id: str) -> str:
    """The registry's USER_ID convention (validate_agents R3)."""
    return f"{agent_id.replace('-', '_')}_agent"


def main() -> int:
    agent_id = resolve_agent_id()
    print(agent_id)
    return 0 if agent_id else 1


if __name__ == "__main__":
    sys.exit(main())

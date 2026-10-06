"""Which agent is writing memory — DERIVED from the running process, never configured.

Every memory names the agent that wrote it (ADR-0031), and the operator must be
able to hold each surface accountable for what it wrote. The identity is
therefore derived at write time from markers the host itself sets on the
running process — never read from a hard-coded setting that can drift from
where the code is actually running:

    cursor        Cursor        CURSOR_AGENT is set
    claude-code   Claude Code   Claude Code markers. Desktop, CLI, and mobile
                                are surfaces of this one actor, not authors.

On a Cursor or Claude Code surface a static ``L9_MEMORY_AGENT_ID`` is IGNORED:
the host's own markers are the only evidence, so a pasted surface author
(``claude-code-desktop`` or ``claude-code-mobile``) can never mislabel a write.
:func:`static_drift` names such a value so SessionStart can report it.

Agents with no host markers of their own are identified by the
``L9_MEMORY_AGENT_ID`` their ADAPTER sets (never an operator's pasted value),
and only when it names a registered identity — see ADAPTER_IDENTITIES:

    manus                Manus (adapters/manus sets and enforces it)
    codex, gemini        existing adapters
    human                the operator's private entrance
    perplexity           Perplexity                 reserved — not yet wired
    perplexity-computer  Perplexity Computer        reserved — not yet wired
    l-cto                L CTO                      reserved — not yet wired
    igorbot              IgorBot                    reserved — not yet wired

Any other value is not an identity.

No guessing: a Claude Code cloud session whose entrypoint is not recognised
resolves to NO identity (""), and every memory writer refuses to write rather
than record an inaccurate author. ``claude-code-desktop`` and
``claude-code-mobile`` are retired surface authors, not registry agents.

Pure: reads the mapping it is given, no I/O. ``python -m ops.memory.agent_identity``
prints the identity for the current process (exit 1 and a reason when none).
"""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from typing import Final

CURSOR: Final = "cursor"
CLAUDE_ACTOR: Final = "claude-code"
#: Every identity this resolver derives from host markers.
DERIVED_IDENTITIES: Final = frozenset({CURSOR, CLAUDE_ACTOR})
CLAUDE_IDENTITIES: Final = frozenset({CLAUDE_ACTOR})
#: Identities set by an agent's own adapter (no host markers to derive from).
ADAPTER_IDENTITIES: Final = frozenset(
    {
        "manus",
        "codex",
        "gemini",
        "human",
        "perplexity",
        "perplexity-computer",
        "l-cto",
        "igorbot",
    }
)
#: Every memory identity there is; equal to the registry's agents.
ALL_IDENTITIES: Final = DERIVED_IDENTITIES | ADAPTER_IDENTITIES
#: Retired surface authors. They name a surface of ``claude-code``, not an agent.
RETIRED: Final = frozenset({"claude-code-desktop", "claude-code-mobile"})
#: Read-compatibility fold for receipts and tags stamped before the surface/actor split.
#: A new write still refuses these names; see ``agent_write``.
HISTORICAL_ACTOR_ALIASES: Final = {name: CLAUDE_ACTOR for name in sorted(RETIRED)}
CURSOR_SURFACE: Final = "cursor-ide"
CLAUDE_DESKTOP_SURFACE: Final = "claude-code-desktop"
CLAUDE_CLI_SURFACE: Final = "claude-code-cli"
CLAUDE_MOBILE_SURFACE: Final = "claude-code-mobile"
LOCAL_ENTRYPOINTS: Final = {"cli": CLAUDE_CLI_SURFACE}
REMOTE_SURFACE_BY_ENTRYPOINT: Final = {"remote_mobile": CLAUDE_MOBILE_SURFACE}
#: CLAUDE_CODE_ENTRYPOINT values of a cloud session this resolver admits.
REMOTE_ENTRYPOINTS: Final = frozenset(REMOTE_SURFACE_BY_ENTRYPOINT)


def _flag(env: Mapping[str, str], name: str) -> str:
    return (env.get(name) or "").strip()


def _is_cursor(env: Mapping[str, str]) -> bool:
    return bool(_flag(env, "CURSOR_AGENT"))


def _is_claude(env: Mapping[str, str]) -> bool:
    return bool(
        _flag(env, "CLAUDECODE")
        or _flag(env, "CLAUDE_CODE_ENTRYPOINT")
        or _flag(env, "CLAUDE_CODE_SESSION_ID")
    )


def _claude_identity(env: Mapping[str, str]) -> str:
    if _flag(env, "CLAUDE_CODE_REMOTE").lower() == "true":
        if _flag(env, "CLAUDE_CODE_ENTRYPOINT").lower() not in REMOTE_ENTRYPOINTS:
            return ""
    return CLAUDE_ACTOR


def canonical_actor_id(value: str | None) -> str:
    """Fold a retired surface-author tag to ``claude-code`` for receipt comparison.

    Call only on a value known to be an actor id. The same strings are surface
    names and must not be folded there.
    """
    actor = (value or "").strip()
    return HISTORICAL_ACTOR_ALIASES.get(actor, actor)


def resolve_agent_id(env: Mapping[str, str] | None = None) -> str:
    """The writing agent's identity, derived from host markers; "" when unknown."""
    source = os.environ if env is None else env
    if _is_cursor(source):
        return CURSOR
    if _is_claude(source):
        return _claude_identity(source)
    explicit = _flag(source, "L9_MEMORY_AGENT_ID")
    return explicit if explicit in ADAPTER_IDENTITIES else ""


def resolve_surface_id(env: Mapping[str, str] | None = None) -> str:
    """The surface of this process, derived from host markers; "" when unknown."""
    source = os.environ if env is None else env
    if _is_cursor(source):
        return CURSOR_SURFACE
    if not _is_claude(source):
        return ""
    entry = _flag(source, "CLAUDE_CODE_ENTRYPOINT").lower()
    if _flag(source, "CLAUDE_CODE_REMOTE").lower() == "true":
        return REMOTE_SURFACE_BY_ENTRYPOINT.get(entry, "")
    return LOCAL_ENTRYPOINTS.get(entry, CLAUDE_DESKTOP_SURFACE)


def static_drift(env: Mapping[str, str] | None = None) -> str:
    """A configured L9_MEMORY_AGENT_ID that disagrees with the derived identity, or ""."""
    source = os.environ if env is None else env
    explicit = _flag(source, "L9_MEMORY_AGENT_ID")
    if not explicit or not (_is_cursor(source) or _is_claude(source)):
        return ""
    return explicit if explicit != resolve_agent_id(source) else ""


def unresolved_reason(env: Mapping[str, str] | None = None) -> str:
    """Why no identity could be derived (for a loud refusal), or ""."""
    source = os.environ if env is None else env
    if resolve_agent_id(source):
        return ""
    if _is_claude(source):
        entry = _flag(source, "CLAUDE_CODE_ENTRYPOINT") or "unset"
        return (
            f"Claude Code cloud session with CLAUDE_CODE_ENTRYPOINT={entry} has no registered "
            f"memory identity (known: {', '.join(sorted(REMOTE_ENTRYPOINTS))})"
        )
    explicit = _flag(source, "L9_MEMORY_AGENT_ID")
    if explicit in RETIRED:
        return (
            f"L9_MEMORY_AGENT_ID={explicit} is a retired surface author; "
            f"the actor is {CLAUDE_ACTOR}"
        )
    if explicit:
        known = ", ".join(sorted(ALL_IDENTITIES))
        return f"L9_MEMORY_AGENT_ID={explicit} is not a registered memory identity (known: {known})"
    return "no host markers (CURSOR_AGENT / Claude Code) and no L9_MEMORY_AGENT_ID"


def user_id_for(agent_id: str) -> str:
    """The registry's USER_ID convention (validate_agents R3), derived from the identity."""
    return f"{agent_id.replace('-', '_')}_agent"


def main() -> int:
    agent_id = resolve_agent_id()
    if agent_id:
        print(agent_id)
        return 0
    print(f"no memory identity: {unresolved_reason()}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())

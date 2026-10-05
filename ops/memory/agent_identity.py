"""Which agent is writing memory — DERIVED from the running process, never configured.

Two identity dimensions, never mixed (upstream ``Quantum-L9/.github``
``semantics/actor_registry.yaml`` and ``semantics/surface_registry.yaml``,
pinned in ``environment/agents/agent_registry.yaml`` ``identity_authority``):

* **ActorIdentity** — who wrote the memory (the join key, ADR-0031).
* **SurfaceIdentity** — where that actor was running.

Both are derived at write time from markers the host itself sets on the
running process — never read from a hard-coded setting that can drift from
where the code is actually running:

    ActorIdentity  SurfaceIdentity       evidence
    cursor         cursor-ide            CURSOR_AGENT is set
    claude-code    claude-code-cli       Claude Code markers, CLAUDE_CODE_REMOTE unset,
                                         CLAUDE_CODE_ENTRYPOINT=cli
    claude-code    claude-code-desktop   Claude Code markers, CLAUDE_CODE_REMOTE unset,
                                         no more specific admitted entrypoint
    claude-code    claude-code-mobile    CLAUDE_CODE_REMOTE=true and
                                         CLAUDE_CODE_ENTRYPOINT=remote_mobile
    claude-code    "" (unknown)          any other Claude Code cloud entrypoint

An unknown surface never makes the actor unknown: Claude Code host markers
prove the actor even when they do not prove the surface.

On a Cursor or Claude Code surface a static ``L9_MEMORY_AGENT_ID`` is IGNORED:
the host's own markers are the only evidence, so a pasted or projected value
(a historical ``claude-code-desktop`` alias, say) can never relabel a write.
:func:`static_drift` names such a value so SessionStart can report it.

Agents with no host markers of their own are identified by the
``L9_MEMORY_AGENT_ID`` their ADAPTER sets (never an operator's pasted value),
and only when it names an ACTIVE adapter actor — see ADAPTER_IDENTITIES:

    manus                Manus (adapters/manus sets and enforces it)
    codex, gemini        existing adapters
    human                the operator's private entrance

PLANNED_IDENTITIES (perplexity, perplexity-computer, l-cto, igorbot) are
registry rows that are not yet wired; they are never a runtime writer.
``tests/ops/memory/test_agent_identity.py`` holds ALL_IDENTITIES equal to
``environment/agents/agent_registry.yaml`` (no drift).

``claude-code-desktop`` and ``claude-code-mobile`` are typed historical
ActorIdentity aliases of ``claude-code`` (:func:`canonical_actor_id`). The same
strings remain canonical SurfaceIdentity values; canonicalize only a value
known to be an ActorIdentity.

Pure: reads the mapping it is given, no I/O. ``python -m ops.memory.agent_identity``
prints the actor for the current process (exit 1 and a reason when none).
"""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from typing import Final

CURSOR_ACTOR: Final = "cursor"
CLAUDE_ACTOR: Final = "claude-code"
#: Every actor this resolver derives from host markers.
DERIVED_IDENTITIES: Final = frozenset({CURSOR_ACTOR, CLAUDE_ACTOR})
#: Active actors set by an agent's own adapter (no host markers to derive from).
ADAPTER_IDENTITIES: Final = frozenset({"manus", "codex", "gemini", "human"})
#: Registry rows with status planned: registered, never a runtime writer.
PLANNED_IDENTITIES: Final = frozenset({"perplexity", "perplexity-computer", "l-cto", "igorbot"})
#: Every registry identity there is; equal to the registry's agents.
ALL_IDENTITIES: Final = DERIVED_IDENTITIES | ADAPTER_IDENTITIES | PLANNED_IDENTITIES
#: Typed historical ActorIdentity aliases (upstream actor_registry.yaml).
HISTORICAL_ACTOR_ALIASES: Final = {
    "claude-code-desktop": CLAUDE_ACTOR,
    "claude-code-mobile": CLAUDE_ACTOR,
}

CURSOR_SURFACE: Final = "cursor-ide"
CLAUDE_DESKTOP_SURFACE: Final = "claude-code-desktop"
CLAUDE_CLI_SURFACE: Final = "claude-code-cli"
CLAUDE_IDE_SURFACE: Final = "claude-code-ide"
CLAUDE_MOBILE_SURFACE: Final = "claude-code-mobile"
#: Every Claude Code SurfaceIdentity with a local execution binding.
CLAUDE_SURFACES: Final = frozenset(
    {CLAUDE_DESKTOP_SURFACE, CLAUDE_CLI_SURFACE, CLAUDE_IDE_SURFACE, CLAUDE_MOBILE_SURFACE}
)
#: CLAUDE_CODE_ENTRYPOINT values of a local process and the surface each is.
LOCAL_ENTRYPOINTS: Final = {"cli": CLAUDE_CLI_SURFACE}
#: CLAUDE_CODE_ENTRYPOINT values of a cloud session and the surface each is.
REMOTE_ENTRYPOINTS: Final = {"remote_mobile": CLAUDE_MOBILE_SURFACE}


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


def _is_remote(env: Mapping[str, str]) -> bool:
    return _flag(env, "CLAUDE_CODE_REMOTE").lower() == "true"


def canonical_actor_id(value: str | None) -> str:
    """An ActorIdentity with typed historical aliases folded to their canonical actor.

    Call only on a value known to be an ActorIdentity (an author tag, a writer
    receipt's agent_id). ``claude-code-desktop`` is also a canonical
    SurfaceIdentity and must not be canonicalized there.
    """
    actor = (value or "").strip()
    return HISTORICAL_ACTOR_ALIASES.get(actor, actor)


def resolve_agent_id(env: Mapping[str, str] | None = None) -> str:
    """The writing actor, derived from host markers; "" when unknown."""
    source = os.environ if env is None else env
    if _is_cursor(source):
        return CURSOR_ACTOR
    if _is_claude(source):
        return CLAUDE_ACTOR
    explicit = _flag(source, "L9_MEMORY_AGENT_ID")
    return explicit if explicit in ADAPTER_IDENTITIES else ""


def resolve_surface_id(env: Mapping[str, str] | None = None) -> str:
    """The SurfaceIdentity of this process, derived from host markers; "" when unknown."""
    source = os.environ if env is None else env
    if _is_cursor(source):
        return CURSOR_SURFACE
    if not _is_claude(source):
        return ""
    entry = _flag(source, "CLAUDE_CODE_ENTRYPOINT").lower()
    if _is_remote(source):
        return REMOTE_ENTRYPOINTS.get(entry, "")
    return LOCAL_ENTRYPOINTS.get(entry, CLAUDE_DESKTOP_SURFACE)


def surface_unresolved_reason(env: Mapping[str, str] | None = None) -> str:
    """Why no SurfaceIdentity could be derived, or ""."""
    source = os.environ if env is None else env
    if resolve_surface_id(source):
        return ""
    if _is_claude(source):
        entry = _flag(source, "CLAUDE_CODE_ENTRYPOINT") or "unset"
        return (
            f"Claude Code cloud session with CLAUDE_CODE_ENTRYPOINT={entry} has no admitted "
            f"surface (known: {', '.join(sorted(REMOTE_ENTRYPOINTS))})"
        )
    return "no host markers (CURSOR_AGENT / Claude Code) for a surface"


def static_drift(env: Mapping[str, str] | None = None) -> str:
    """A configured L9_MEMORY_AGENT_ID that disagrees with the derived actor, or ""."""
    source = os.environ if env is None else env
    explicit = _flag(source, "L9_MEMORY_AGENT_ID")
    if not explicit or not (_is_cursor(source) or _is_claude(source)):
        return ""
    return explicit if explicit != resolve_agent_id(source) else ""


def unresolved_reason(env: Mapping[str, str] | None = None) -> str:
    """Why no actor could be derived (for a loud refusal), or ""."""
    source = os.environ if env is None else env
    if resolve_agent_id(source):
        return ""
    explicit = _flag(source, "L9_MEMORY_AGENT_ID")
    if explicit in HISTORICAL_ACTOR_ALIASES:
        return (
            f"L9_MEMORY_AGENT_ID={explicit} is a historical ActorIdentity alias of "
            f"{HISTORICAL_ACTOR_ALIASES[explicit]}; that actor is derived from Claude Code "
            "host markers, never configured"
        )
    if explicit in DERIVED_IDENTITIES:
        return f"L9_MEMORY_AGENT_ID={explicit} is derived from host markers, never configured"
    if explicit in PLANNED_IDENTITIES:
        return f"L9_MEMORY_AGENT_ID={explicit} is a planned identity, not yet a runtime writer"
    if explicit:
        known = ", ".join(sorted(ADAPTER_IDENTITIES))
        return f"L9_MEMORY_AGENT_ID={explicit} is not an active adapter identity (known: {known})"
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

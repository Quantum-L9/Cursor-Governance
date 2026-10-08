"""Surface identity SSOT for Cursor / Claude Code / peer adapters.

Canonical predicate for where an agent session is running. Adapters and gates
MUST import this (or the shell twin ``ops/scripts/lib/surface_detect.sh``)
instead of inventing private marker lists.

Return values:
  cursor | claude-code | claude-code-remote | codex | gemini | manus | unknown

Precedence:
  1. A Cursor host marker overrides a projected Claude explicit surface
     (``L9_GOVERNANCE_SURFACE=claude-code`` from ``.claude/settings.json``
     loaded inside Cursor). Markers: ``CURSOR_AGENT``,
     ``CURSOR_CONVERSATION_ID``, ``CURSOR_EXTENSION_HOST_ROLE``.
     Intentional non-Claude explicit ids still win.
  2. Explicit ``L9_GOVERNANCE_SURFACE`` when it is a known id.
  3. Runtime markers break ties toward the adapter (Claude remote, Claude
     desktop/CLI, then Cursor).
  4. ``unknown`` when nothing matches — callers that fail-toward-enforcing
     treat unknown as "do not skip the gate".
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from typing import Final

KNOWN_SURFACES: Final[frozenset[str]] = frozenset(
    {
        "cursor",
        "claude-code",
        "claude-code-remote",
        "codex",
        "gemini",
        "manus",
    }
)

CLAUDE_GATE_SURFACES: Final[frozenset[str]] = frozenset({"claude-code", "claude-code-remote"})

#: Host markers Cursor sets on an agent process. ``CURSOR_AGENT`` is the
#: primary one; the other two remain when a hook child inherits the Cursor
#: process environment but not ``CURSOR_AGENT``. Any one of them means this
#: process is Cursor, including when a projected ``.claude/settings.json``
#: has set ``L9_GOVERNANCE_SURFACE=claude-code``.
CURSOR_HOST_MARKERS: Final[tuple[str, ...]] = (
    "CURSOR_AGENT",
    "CURSOR_CONVERSATION_ID",
    "CURSOR_EXTENSION_HOST_ROLE",
)

ADAPTER_KERNEL_SURFACES: Final[frozenset[str]] = frozenset(
    {"claude-code", "claude-code-remote", "codex", "gemini", "manus"}
)


def cursor_host_present(env: Mapping[str, str] | None = None) -> bool:
    """True when ``env`` carries a Cursor host marker."""
    source = os.environ if env is None else env
    return any((source.get(key) or "").strip() for key in CURSOR_HOST_MARKERS)


def scrub_cursor_host_markers(delete: Callable[..., object]) -> None:
    """Remove every Cursor host marker via ``delete(name, raising=False)``.

    ``detect_surface`` treats any one marker as Cursor, including when a test
    has set ``L9_GOVERNANCE_SURFACE=claude-code``. Deleting only
    ``CURSOR_AGENT`` leaves ``CURSOR_CONVERSATION_ID`` and the surface stays
    Cursor inside a Cursor session.
    """
    for marker in CURSOR_HOST_MARKERS:
        delete(marker, raising=False)


def detect_surface(env: Mapping[str, str] | None = None) -> str:
    """Return the surface id for ``env`` (defaults to ``os.environ``)."""
    source = os.environ if env is None else env
    explicit = (source.get("L9_GOVERNANCE_SURFACE") or "").strip().lower()
    if cursor_host_present(source) and explicit in CLAUDE_GATE_SURFACES:
        return "cursor"
    if explicit in KNOWN_SURFACES:
        return explicit

    if (source.get("CLAUDE_CODE_REMOTE") or "").strip().lower() == "true":
        return "claude-code-remote"

    if (
        source.get("CLAUDECODE")
        or source.get("CLAUDE_CODE_ENTRYPOINT")
        or source.get("CLAUDE_CODE_SESSION_ID")
    ):
        return "claude-code"

    if cursor_host_present(source):
        return "cursor"

    return "unknown"


def detect_surface_id(env: Mapping[str, str] | None = None) -> str:
    """The fine SurfaceIdentity (``cursor-ide``, ``claude-code-cli``, …); "" when unknown.

    Not the governance-profile domain :func:`detect_surface` returns. The one
    evidence table is ``ops/memory/agent_identity.py``.
    """
    from ops.memory.agent_identity import resolve_surface_id  # noqa: PLC0415

    return resolve_surface_id(env)


def claude_runtime_present(env: Mapping[str, str] | None = None) -> bool:
    """True for a live Claude process, not a projected surface string.

    ``L9_GOVERNANCE_SURFACE=claude-code`` from ``.claude/settings.json`` is not
    a runtime. Cursor loads that file, so the string alone must not arm a
    Claude-only gate.
    """
    source = os.environ if env is None else env
    if (source.get("CLAUDE_CODE_REMOTE") or "").strip().lower() == "true":
        return True
    return bool(
        source.get("CLAUDECODE")
        or source.get("CLAUDE_CODE_ENTRYPOINT")
        or source.get("CLAUDE_CODE_SESSION_ID")
    )


def is_claude_gate_surface(env: Mapping[str, str] | None = None) -> bool:
    """True when Claude adapter gate-class hooks should evaluate."""
    return detect_surface(env) in CLAUDE_GATE_SURFACES


def main() -> int:
    print(detect_surface())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

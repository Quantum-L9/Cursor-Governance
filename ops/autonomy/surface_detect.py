"""Surface identity SSOT for Cursor / Claude Code / peer adapters.

Canonical predicate for where an agent session is running. Adapters and gates
MUST import this (or the shell twin ``ops/scripts/lib/surface_detect.sh``)
instead of inventing private marker lists.

Return values:
  cursor | claude-code | claude-code-remote | codex | gemini | manus | unknown

Precedence:
  1. Explicit ``L9_GOVERNANCE_SURFACE`` when it is a known id (wins).
  2. Runtime markers break ties toward the adapter (Claude remote, Claude
     desktop/CLI, then Cursor).
  3. ``unknown`` when nothing matches — callers that fail-toward-enforcing
     treat unknown as "do not skip the gate".
"""

from __future__ import annotations

import os
from collections.abc import Mapping
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

CLAUDE_GATE_SURFACES: Final[frozenset[str]] = frozenset(
    {"claude-code", "claude-code-remote"}
)

ADAPTER_KERNEL_SURFACES: Final[frozenset[str]] = frozenset(
    {"claude-code", "claude-code-remote", "codex", "gemini", "manus"}
)


def detect_surface(env: Mapping[str, str] | None = None) -> str:
    """Return the surface id for ``env`` (defaults to ``os.environ``)."""
    source = os.environ if env is None else env
    explicit = (source.get("L9_GOVERNANCE_SURFACE") or "").strip().lower()
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

    if source.get("CURSOR_AGENT"):
        return "cursor"

    return "unknown"


def is_claude_gate_surface(env: Mapping[str, str] | None = None) -> bool:
    """True when Claude adapter gate-class hooks should evaluate."""
    return detect_surface(env) in CLAUDE_GATE_SURFACES


def kernel_latch_surface(env: Mapping[str, str] | None = None) -> bool:
    """True when the tree-kernel latch applies (adapter / Claude runtimes)."""
    return detect_surface(env) in ADAPTER_KERNEL_SURFACES


def main() -> int:
    print(detect_surface())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

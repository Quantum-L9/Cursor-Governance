"""Surface identity SSOT for Cursor / Claude Code / peer adapters.

Canonical predicate for where an agent session is running. Adapters and gates
MUST import this (or the shell twin ``ops/scripts/lib/surface_detect.sh``)
instead of inventing private marker lists.

Return values:
  cursor | claude-code | claude-code-remote | codex | gemini | manus | unknown

Precedence:
  1. ``CURSOR_AGENT`` overrides a projected Claude explicit surface
     (``L9_GOVERNANCE_SURFACE=claude-code`` from ``.claude/settings.json``
     loaded inside Cursor). Intentional non-Claude explicit ids still win.
  2. Explicit ``L9_GOVERNANCE_SURFACE`` when it is a known id.
  3. Runtime markers break ties toward the adapter (Claude remote, Claude
     desktop/CLI, then Cursor).
  4. ``unknown`` when nothing matches — callers that fail-toward-enforcing
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

CLAUDE_GATE_SURFACES: Final[frozenset[str]] = frozenset({"claude-code", "claude-code-remote"})

ADAPTER_KERNEL_SURFACES: Final[frozenset[str]] = frozenset(
    {"claude-code", "claude-code-remote", "codex", "gemini", "manus"}
)


def detect_surface(env: Mapping[str, str] | None = None) -> str:
    """Return the surface id for ``env`` (defaults to ``os.environ``)."""
    source = os.environ if env is None else env
    explicit = (source.get("L9_GOVERNANCE_SURFACE") or "").strip().lower()
    if source.get("CURSOR_AGENT") and explicit in CLAUDE_GATE_SURFACES:
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

    if source.get("CURSOR_AGENT"):
        return "cursor"

    return "unknown"


def is_claude_gate_surface(env: Mapping[str, str] | None = None) -> bool:
    """True when Claude adapter gate-class hooks should evaluate."""
    return detect_surface(env) in CLAUDE_GATE_SURFACES


#: Values that mean "yes" in a CI environment variable. Anything else —
#: including the literal "false" and "0" that GitHub Actions itself writes
#: for a disabled condition — is not CI.
_CI_TRUTHY = frozenset({"1", "true", "yes"})


def _ci_surface(source: Mapping[str, str]) -> bool:
    """True only for an explicitly truthy CI marker.

    Both markers are parsed the same way on purpose. Accepting any non-empty
    ``GITHUB_ACTIONS`` would classify ``GITHUB_ACTIONS=false`` as CI, and
    because CI is the one thing that SKIPS the kernel latch, that is an
    accidental bypass of the gate rather than a harmless misread. Unknown or
    malformed values now fail closed: the latch applies.
    """
    return any(
        (source.get(key) or "").strip().lower() in _CI_TRUTHY for key in ("GITHUB_ACTIONS", "CI")
    )


def kernel_latch_surface(env: Mapping[str, str] | None = None) -> bool:
    """True when local publish must take the tree-kernel latch at precommit.

    Cursor, adapters, and a bare local shell all fire so RA + Validate &
    Repair record before the precommit hooks and tests. This is NOT an L4
    gate: ``authorize-release`` never consults it (CANONICAL_LAW
    ``KERNEL_PRECOMMIT_HOOK_V1``).

    A bare shell used to resolve ``unknown`` and skip, so a human publishing
    without an agent-surface marker bypassed the latch entirely. Skip only CI
    with no agent-surface marker: ``.l9/autonomy/kernel-receipt.json`` is
    gitignored and cannot exist on GitHub Actions. A CI job that sets a known
    surface (unit tests) still latches.
    """
    source = os.environ if env is None else env
    if _ci_surface(source) and detect_surface(source) == "unknown":
        return False
    return True


def main() -> int:
    print(detect_surface())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

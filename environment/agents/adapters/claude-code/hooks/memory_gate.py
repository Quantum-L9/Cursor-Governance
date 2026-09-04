#!/usr/bin/env python3
"""PreToolUse memory gate — Cursor Graphiti front door only.

Operator-only escape hatch (admin key, never agent-settable):
  L9_MEMORY_ENFORCEMENT_BREAKGLASS=<reason>

There is no ``ENFORCEMENT-off`` side door.

**Hydration only.** The single permitted gate shape is::

    fresh hydration?  yes -> continue
                      no  -> hydrate, then continue

The gate does NOT consult, acquire, or require a Graphiti phase-lock. Memory
shares knowledge; repository isolation comes from a dedicated worktree, history
isolation from a branch, and collision safety from Git plus the publication
gate. A memory conflict is *evidence*, never a repository mutex, so one agent
writing memory cannot revoke another agent's authority to edit code
(rules/96-multi-agent-main-bound-execution.mdc, invariants E7 and E10).

``git``/``gh`` shell commands are exempt: memory hydration governs *writes to
the repository*, and the `git-mutation` rule still describes the expected
workflow, but an unsatisfied precondition no longer blocks the command from
executing. See ``ops/autonomy/git_execution_exemption``. Editor writes and the
MCP GitHub tools are governed exactly as before.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

MEM = Path(__file__).resolve().parent.parent / "memory"
sys.path.insert(0, str(MEM))

# The exemption brain lives under ops/ (CANONICAL_LAW §2.1). This hook always
# runs out of the governance clone, but accept the canonical $HOME location too
# so an installed copy still resolves it.
for _autonomy in (
    Path(__file__).resolve().parents[5] / "ops" / "autonomy",
    Path.home() / ".cursor-governance" / "ops" / "autonomy",
):
    if _autonomy.is_dir() and str(_autonomy) not in sys.path:
        sys.path.insert(0, str(_autonomy))

import memory_state as st  # noqa: E402

try:
    from git_execution_exemption import event_is_git_or_gh  # noqa: E402
except ImportError:  # pragma: no cover - exemption module unreachable
    import re as _re

    _PLAIN_GIT = _re.compile(r"^\s*(?:git|gh)(?:\s+[^\s'\"`$;&|<>()]+)*\s*$")

    def event_is_git_or_gh(tool_name: str, tool_input: object) -> bool:
        """Narrow fallback: a missing module must not resurrect the denial."""
        if tool_name not in {"Bash", "bash", "Shell", "shell"}:
            return False
        if not isinstance(tool_input, dict):
            return False
        command = str(tool_input.get("command") or tool_input.get("cmd") or "")
        return bool(_PLAIN_GIT.match(command))


def _deny(reason: str) -> None:
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
    sys.exit(0)


def _governed_tool_names(contract: dict) -> set[str]:
    names: set[str] = set()
    for rule in contract.get("governed_writes", []):
        names.update(rule.get("match", {}).get("tools", []))
    return names


def main() -> int:
    # Deliberately NO ENFORCEMENT-off escape hatch.
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    tool_name = str(event.get("tool_name", ""))
    tool_input = event.get("tool_input") or {}

    # Before contract load, classification, and the fail-closed handler: for a
    # git/gh command, execution permission does not depend on memory state.
    if event_is_git_or_gh(tool_name, tool_input):
        return 0

    try:
        session_id = st.resolve_session_id(event=event)
    except ValueError:
        session_id = ""

    try:
        contract = st.load_contract()
    except (OSError, json.JSONDecodeError):
        print("memory-gate: contract unreadable; enforcement inactive", file=sys.stderr)
        return 0

    if tool_name not in _governed_tool_names(contract):
        return 0

    breakglass = os.environ.get("L9_MEMORY_ENFORCEMENT_BREAKGLASS", "").strip()

    try:
        rule = st.classify(contract, tool_name, tool_input)
        if rule is None:
            return 0
        if breakglass:
            try:
                st.record_override(contract, rule["id"], breakglass)
            except OSError as exc:
                print(
                    f"memory-gate: could not persist override event ({exc}); "
                    "continuing under breakglass",
                    file=sys.stderr,
                )
            print(
                f"memory-gate: OPERATOR BREAKGLASS on {rule['id']}: {breakglass}",
                file=sys.stderr,
            )
            return 0

        # Raises on any precondition beyond hydration (E7 fail-closed).
        requires = st.validate_requires(rule)

        if "session_prefetch" in requires and not st.usable_receipt(contract, session_id):
            # Name the session id the gate itself resolved: on Cursor the hook
            # event id is NOT the newest ~/.claude/projects jsonl, and pointing
            # at that heuristic sent agents to prefetch for the wrong session.
            sid_hint = (
                f"--session-id {session_id}"
                if session_id
                else (
                    "--session-id <session-id-from-hook-event> "
                    "(best-effort fallback only if the hook event has no "
                    "session_id: newest ~/.claude/projects/<project>/<uuid>.jsonl "
                    "— on Cursor that heuristic is often wrong)"
                )
            )
            _deny(
                f"Memory not hydrated this session. Governed write '{rule['id']}' requires the "
                "SessionStart Graphiti prefetch (front door). Start a fresh session, or run "
                "environment/agents/adapters/claude-code/hooks/memory_prefetch.py "
                f"{sid_hint}, then retry. "
                "This is a hydration gate, not a lock: no phase-lock is required or accepted."
            )
        return 0
    except Exception as exc:
        _deny(
            f"memory-gate could not verify preconditions for '{tool_name}' ({exc}). "
            "Failing closed. Operator override: L9_MEMORY_ENFORCEMENT_BREAKGLASS=<reason>."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

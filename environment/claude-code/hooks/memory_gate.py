#!/usr/bin/env python3
"""PreToolUse memory gate — Cursor Graphiti front door only.

Operator-only escape hatch (admin key, never agent-settable):
  L9_MEMORY_ENFORCEMENT_BREAKGLASS=<reason>

There is no ``ENFORCEMENT-off`` side door.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

MEM = Path(__file__).resolve().parent.parent / "memory"
sys.path.insert(0, str(MEM))

import graphiti_bridge as gb  # noqa: E402
import memory_state as st  # noqa: E402


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
    session_id = str(event.get("session_id", ""))

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

        requires = rule.get("requires", [])
        namespaces = st.resolve_namespaces(contract) or ["cursor-governance"]

        if "session_prefetch" in requires and not st.fresh_receipt(contract, session_id):
            _deny(
                f"Memory not prefetched this session. Governed write '{rule['id']}' requires the "
                "SessionStart Graphiti prefetch (front door). Start a fresh session, or run "
                "environment/claude-code/hooks/memory_prefetch.py, then retry."
            )

        if "phase_lock" in requires:
            if not _has_verified_lock(contract, namespaces, session_id):
                _deny(
                    f"No conflict-checked phase-lock held. Governed write '{rule['id']}' "
                    f"requires a verified Graphiti lock on one of {namespaces}. Acquire: "
                    "python3 environment/claude-code/hooks/memory_lock.py acquire "
                    f'--namespace {namespaces[0]} --task "<what you are changing>".'
                )
        return 0
    except Exception as exc:
        _deny(
            f"memory-gate could not verify preconditions for '{tool_name}' ({exc}). "
            "Failing closed. Operator override: L9_MEMORY_ENFORCEMENT_BREAKGLASS=<reason>."
        )
    return 0


def _has_verified_lock(contract: dict, namespaces: list[str], session_id: str) -> bool:
    """Verify local lock artifact + Cursor Graphiti phase-lock state. No HTTP."""
    graphiti_ok = gb.phase_lock_satisfied(session_id)
    for namespace in namespaces:
        lock = st.read_lock(contract, namespace)
        if not lock or lock.get("session_id") != session_id:
            continue
        if not lock.get("task_signature"):
            continue
        # Front-door acquire stamps transport + granted after Graphiti phase-lock.
        if lock.get("transport") == "cursor-graphiti-phase-lock" and lock.get("granted"):
            return True
        if graphiti_ok:
            return True
    return False


if __name__ == "__main__":
    raise SystemExit(main())

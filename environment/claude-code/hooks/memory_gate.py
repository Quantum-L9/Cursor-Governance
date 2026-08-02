#!/usr/bin/env python3
"""PreToolUse memory-enforcement gate for the Claude Code surface.

Reads the tool call on stdin, classifies it against
`environment/claude-code/memory/memory-enforcement.contract.json`, and emits a
`deny` permission decision when a governed write's preconditions are unmet.
It only ever ADDS denials — it never emits `allow`, so normal permission
prompts are preserved for everything it does not block.

Fail-closed for governed writes: a missing prefetch receipt or an
unverifiable phase-lock blocks the write. Non-governed tools are never blocked,
even if this gate errors. Operator-only escape hatches:
  L9_MEMORY_ENFORCEMENT=off            disable entirely (surfaces w/o memory)
  L9_MEMORY_ENFORCEMENT_BREAKGLASS=... allow + record an override event
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "memory"))

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
    if os.environ.get("L9_MEMORY_ENFORCEMENT", "on").strip().lower() == "off":
        return 0
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
        # Cannot load the contract: fail open rather than brick every tool.
        print("memory-gate: contract unreadable; enforcement inactive", file=sys.stderr)
        return 0

    # A crash after this point only fails closed for governed tool names.
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
                # Non-fatal: the override still applies, but note the audit gap.
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
                "SessionStart memory prefetch to have run. Start a fresh session, or run "
                "environment/claude-code/hooks/memory_prefetch.py, then retry."
            )

        if "phase_lock" in requires:
            if not _has_verified_lock(contract, namespaces, session_id):
                _deny(
                    f"No conflict-checked phase-lock held. Governed write '{rule['id']}' "
                    f"requires a verified lock on one of {namespaces}. Acquire one: python3 "
                    "environment/claude-code/hooks/memory_lock.py acquire "
                    f'--namespace {namespaces[0]} --task "<what you are changing>".'
                )
        return 0
    except Exception as exc:  # governed tool + unexpected failure -> fail closed
        _deny(
            f"memory-gate could not verify preconditions for '{tool_name}' ({exc}). "
            "Failing closed. Set L9_MEMORY_ENFORCEMENT_BREAKGLASS with a reason to override."
        )
    return 0


def _has_verified_lock(contract: dict, namespaces: list[str], session_id: str) -> bool:
    import memory_client as mc  # local import; only lock-gated writes pay this cost

    for namespace in namespaces:
        lock = st.read_lock(contract, namespace)
        if not lock or lock.get("session_id") != session_id:
            continue
        signature = str(lock.get("task_signature", ""))
        try:
            verdict = mc.verify_phase_lock(namespace, signature)
        except mc.MemoryError:
            continue  # cannot confirm this lock; try the next namespace
        status = str(verdict.get("status", verdict.get("state", ""))).lower()
        if verdict.get("valid") is True or status in {
            "granted",
            "current",
            "valid",
            "active",
            "ok",
        }:
            return True
    return False


if __name__ == "__main__":
    raise SystemExit(main())

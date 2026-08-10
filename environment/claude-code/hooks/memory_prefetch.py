#!/usr/bin/env python3
"""SessionStart prefetch — thin wrap of Cursor Graphiti inject (front door only)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

MEM = Path(__file__).resolve().parent.parent / "memory"
sys.path.insert(0, str(MEM))

import graphiti_bridge as gb  # noqa: E402
import memory_state as st  # noqa: E402


def _emit(context: str) -> None:
    print(
        json.dumps(
            {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}}
        )
    )


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        event = {}
    session_id = str(event.get("session_id", "")) or "unknown-session"

    try:
        contract = st.load_contract()
    except (OSError, json.JSONDecodeError):
        return 0

    namespaces = st.resolve_namespaces(contract) or ["cursor-governance"]
    workspace = st.workspace_root()
    task = f"Claude Code session in {workspace.name}"

    try:
        result = gb.inject(task, workspace=workspace, session_id=session_id)
        group_id = str(result.get("group_id") or "")
        st.write_receipt(
            contract,
            session_id,
            {
                "namespaces": namespaces,
                "transport": "cursor-graphiti-inject",
                "group_id": group_id,
                "prefetch_chars": result.get("prefetch_chars"),
                "status": "prefetched",
            },
        )
        lines = [
            "L9 memory: ENFORCED via Cursor Graphiti front door "
            f"(group_id={group_id or 'unknown'}; namespaces {', '.join(namespaces)}). "
            "Rule 03-graphiti-memory; skill l9-graphiti-memory; CANONICAL_LAW §8.",
        ]
        if result.get("prefetch_chars"):
            lines.append(f"graphiti: prefetch ok ({result.get('prefetch_chars')} chars).")
        lines.append(
            "Governed writes require a conflict-checked phase-lock via the same front door: "
            "python3 environment/claude-code/hooks/memory_lock.py acquire "
            f'--namespace {namespaces[0]} --task "<change>".'
        )
        _emit("\n".join(lines))
    except Exception as exc:  # fail-open
        _emit(
            "L9 memory: prefetch DEGRADED ("
            f"{exc}). No receipt written; governed writes remain fail-closed until Cursor "
            "Graphiti is reachable. Operator-only override: L9_MEMORY_ENFORCEMENT_BREAKGLASS."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

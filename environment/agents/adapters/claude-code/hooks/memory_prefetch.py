#!/usr/bin/env python3
"""SessionStart prefetch — thin wrap of Cursor hydration compiler (front door).

Mid-session repair: when the automatic SessionStart stamp is stale or missing,
run with an explicit session id instead of guessing:

    python3 memory_prefetch.py --session-id <uuid>

Find your session id as the newest
``~/.claude/projects/<project>/<uuid>.jsonl`` for this conversation.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

MEM = Path(__file__).resolve().parent.parent / "memory"
sys.path.insert(0, str(MEM))

import graphiti_bridge as gb  # noqa: E402
import memory_state as st  # noqa: E402


def _gov_root() -> Path:
    return gb.find_governance_root()


def _emit(context: str) -> None:
    print(
        json.dumps(
            {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}}
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(prog="memory_prefetch")
    parser.add_argument(
        "--session-id",
        default=None,
        help=(
            "stamp the receipt for this session id instead of reading stdin "
            "(newest ~/.claude/projects/<project>/<uuid>.jsonl for this conversation)"
        ),
    )
    args = parser.parse_args()
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        event = {}
    session_id = args.session_id or str(event.get("session_id", "")) or "unknown-session"

    try:
        contract = st.load_contract()
    except (OSError, json.JSONDecodeError):
        return 0

    namespaces = st.resolve_namespaces(contract) or ["cursor-governance"]
    workspace = st.workspace_root()
    os.environ.setdefault("L9_MEMORY_AGENT_ID", "claude-code")
    os.environ.setdefault("USER_ID", "claude_code_agent")

    root = _gov_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    try:
        from ops.graphiti.hydration.compile_session_packet import compile_and_format

        compiled = compile_and_format(
            project_dir=workspace,
            conversation_id=session_id,
            agent_id="claude-code",
        )
        packet = compiled.get("packet") or {}
        group_id = str(packet.get("group_id") or "")
        # Gate receipt via inject (hash / memory_satisfied_for)
        try:
            result = gb.inject(
                f"Claude Code session in {workspace.name}",
                workspace=workspace,
                session_id=session_id,
            )
            group_id = group_id or str(result.get("group_id") or "")
        except Exception:  # noqa: BLE001 — hydrate facts still useful
            pass
        st.write_receipt(
            contract,
            session_id,
            {
                "namespaces": namespaces,
                "transport": "cursor-graphiti-hydrate",
                "group_id": group_id,
                "packet_id": packet.get("packet_id"),
                "status": "prefetched",
                "degraded": bool(packet.get("degraded")),
            },
        )
        lines = [
            "L9 memory: ENFORCED via Cursor Graphiti hydrate "
            f"(group_id={group_id or 'unknown'}; namespaces {', '.join(namespaces)}). "
            "Rule 03-graphiti-memory; skill l9-graphiti-memory; CANONICAL_LAW §8.",
            compiled.get("additional_context") or "",
            "Governed writes require a conflict-checked phase-lock via the same front door: "
            "python3 environment/agents/adapters/claude-code/hooks/memory_lock.py acquire "
            f'--namespace {namespaces[0]} --task "<change>".',
        ]
        _emit("\n".join(lines))
    except Exception as exc:  # fail-open
        _emit(
            "L9 memory: prefetch DEGRADED ("
            f"{exc}). No receipt written; governed writes remain fail-closed until Cursor "
            "Graphiti is reachable. Operator-only override: L9_MEMORY_ENFORCEMENT_BREAKGLASS. "
            "next="
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

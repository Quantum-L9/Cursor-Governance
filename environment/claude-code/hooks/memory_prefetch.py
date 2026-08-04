#!/usr/bin/env python3
"""SessionStart memory prefetch for the Claude Code surface.

Hydrates the governed namespace(s) from the l9-shared-memory server and writes a
session receipt. The receipt is the object the PreToolUse gate checks: no
receipt -> governed writes are denied. Fail-open by contract: a prefetch failure
never blocks the session, but it also does not write a receipt, which keeps the
write boundary fail-closed until memory is reachable again.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "memory"))

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
        return 0  # no contract -> nothing to enforce; stay silent and open

    namespaces = st.resolve_namespaces(contract) or ["cursor-governance"]
    task = f"Claude Code session in {st.workspace_root().name}"

    try:
        import memory_client as mc

        bundle = mc.hydrate(task, namespaces, limit=8)
        # memory.hydrate returns context under `sections` (HydrationResult); it has
        # no `records`/`hits` key. Read via the one-contract accessor so this hook
        # cannot drift from the server schema. See ADR-0003/ADR-0004.
        sections = mc.hydrated_sections(bundle)
        st.write_receipt(
            contract,
            session_id,
            {"namespaces": namespaces, "hydrated_records": len(sections), "status": "prefetched"},
        )
        lines = [
            "L9 memory: ENFORCED. Prefetch complete for namespaces "
            f"{', '.join(namespaces)} ({len(sections)} section(s) hydrated).",
        ]
        # Bound injected context by the server-provided token budget (~4 chars/
        # token) so a large hydration cannot overrun the SessionStart budget.
        token_budget = int(bundle.get("token_budget") or 1200)
        context = mc.render_sections(bundle, max_chars=max(500, token_budget * 4))
        if context:
            # Actually surface the retrieved memory to the session — a successful
            # prefetch that injects nothing is indistinguishable from no memory.
            lines.append("--- prefetched memory (l9-shared-memory) ---")
            lines.append(context)
        for warning in bundle.get("warnings") or []:
            lines.append(f"memory warning: {warning}")
        lines.append(
            "Governed writes (authority-file edits, git commit/push/merge, PR "
            "create/merge) require a conflict-checked phase-lock: python3 "
            "environment/claude-code/hooks/memory_lock.py acquire --namespace "
            f'{namespaces[0]} --task "<change>". The PreToolUse gate denies them otherwise.'
        )
        _emit("\n".join(lines))
    except Exception as exc:  # fail-open: never block session start
        _emit(
            "L9 memory: prefetch DEGRADED ("
            f"{exc}). No receipt written; governed writes remain fail-closed until memory is "
            "reachable. Operator override: L9_MEMORY_ENFORCEMENT_BREAKGLASS or "
            "L9_MEMORY_ENFORCEMENT=off."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from collections.abc import Mapping


def render_context(status: Mapping[str, object]) -> str:
    raw_programs = status.get("programs")
    programs = raw_programs if isinstance(raw_programs, list) else []
    lines = [f"programs: {status.get('active_programs', 0)} active"]
    emitted = 0
    for item in programs:
        if emitted >= 5:
            break
        if not isinstance(item, dict):
            continue
        program_id = item.get("program_id", "unknown")
        state = item.get("state", "UNKNOWN")
        lines.append(f"- {program_id}: {state}")
        emitted += 1
    return "\n".join(lines)

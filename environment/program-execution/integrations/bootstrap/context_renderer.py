from __future__ import annotations

from collections.abc import Mapping


def render_context(status: Mapping[str, object]) -> str:
    programs = list(status.get("programs") or [])
    lines = [f"programs: {status.get('active_programs', 0)} active"]
    for item in programs[:5]:
        if isinstance(item, dict):
            lines.append(f"- {item.get('program_id', 'unknown')}: {item.get('state', 'UNKNOWN')}")
    return "\n".join(lines)
